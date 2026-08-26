import io
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.orm import Session, joinedload

from app.core.access import (
    can_see_supervisor_assignment,
    catalog_machine_ids,
    require_machine_access,
    validate_operator_id,
    validate_supervisor_id,
)
from app.core.deps import get_current_user, require_assign_operators, require_assign_supervisors, require_roles
from app.core.utils import commit_or_409, get_or_404
from app.database import get_db
from app.models import Machine, User, UserRole
from app.schemas.machines import (
    MachineCreate,
    MachineOperatorAssignmentsUpdate,
    MachinePublic,
    MachineSupervisorAssignmentsUpdate,
    MachineUpdate,
)

router = APIRouter(prefix="/machines", tags=["machines"])

_admin_write = require_roles(UserRole.admin)

_MACHINE_LOAD = (joinedload(Machine.operator), joinedload(Machine.supervisor))


def _public_machine(machine: Machine, viewer: User) -> MachinePublic:
    payload = MachinePublic.model_validate(machine)
    if can_see_supervisor_assignment(viewer):
        return payload
    return payload.model_copy(update={"supervisor_id": None, "supervisor": None})


def _machines_by_ids(db: Session, machine_ids: list[uuid.UUID], viewer: User) -> list[MachinePublic]:
    rows = (
        db.query(Machine)
        .options(*_MACHINE_LOAD)
        .filter(Machine.id.in_(machine_ids))
        .order_by(Machine.name)
        .all()
    )
    return [_public_machine(row, viewer) for row in rows]


@router.get("", response_model=list[MachinePublic])
def list_machines(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> list[MachinePublic]:
    query = db.query(Machine).options(*_MACHINE_LOAD).order_by(Machine.group_name.nulls_last(), Machine.name)
    scoped_ids = catalog_machine_ids(db, current_user)
    if scoped_ids is not None:
        if not scoped_ids:
            return []
        query = query.filter(Machine.id.in_(scoped_ids))
    return [_public_machine(row, current_user) for row in query.all()]


@router.put("/operator-assignments", response_model=list[MachinePublic])
def set_operator_assignments(
    payload: MachineOperatorAssignmentsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_assign_operators),
) -> list[MachinePublic]:
    """Save who sits on which unit in one request.

    The same operator may cover several units at once (Suresh on four FAC
    heads). Each machine still appears at most once.
    """
    assignments = payload.assignments
    machine_ids = [row.machine_id for row in assignments]
    if len(set(machine_ids)) != len(machine_ids):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Each machine can only appear once")

    machines = db.query(Machine).filter(Machine.id.in_(machine_ids)).all()
    by_id = {m.id: m for m in machines}
    missing = [mid for mid in machine_ids if mid not in by_id]
    if missing:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "One or more machines were not found")

    for row in assignments:
        validate_operator_id(db, row.operator_id)

    for machine in machines:
        machine.operator_id = None
    db.flush()
    for row in assignments:
        by_id[row.machine_id].operator_id = row.operator_id

    commit_or_409(db, "Could not save operator assignments")
    return _machines_by_ids(db, machine_ids, current_user)


@router.put("/supervisor-assignments", response_model=list[MachinePublic])
def set_supervisor_assignments(
    payload: MachineSupervisorAssignmentsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_assign_supervisors),
) -> list[MachinePublic]:
    """Dedicated supervisor per machine. Null is valid (plant equipment)."""
    assignments = payload.assignments
    machine_ids = [row.machine_id for row in assignments]
    if len(set(machine_ids)) != len(machine_ids):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Each machine can only appear once")

    machines = db.query(Machine).filter(Machine.id.in_(machine_ids)).all()
    by_id = {m.id: m for m in machines}
    missing = [mid for mid in machine_ids if mid not in by_id]
    if missing:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "One or more machines were not found")

    for row in assignments:
        validate_supervisor_id(db, row.supervisor_id)

    for machine in machines:
        machine.supervisor_id = None
    db.flush()
    for row in assignments:
        by_id[row.machine_id].supervisor_id = row.supervisor_id

    commit_or_409(db, "Could not save supervisor assignments")
    return _machines_by_ids(db, machine_ids, current_user)


@router.get("/{machine_id}", response_model=MachinePublic)
def get_machine(
    machine_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> MachinePublic:
    machine = require_machine_access(db, current_user, machine_id)
    loaded = db.query(Machine).options(*_MACHINE_LOAD).filter(Machine.id == machine.id).one()
    return _public_machine(loaded, current_user)


@router.post("", response_model=MachinePublic, status_code=201)
def create_machine(
    payload: MachineCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(_admin_write),
) -> MachinePublic:
    validate_operator_id(db, payload.operator_id)
    validate_supervisor_id(db, payload.supervisor_id)
    data = payload.model_dump()
    data["kind"] = payload.kind.value
    machine = Machine(**data)
    db.add(machine)
    commit_or_409(db, "Could not create machine")
    db.refresh(machine)
    loaded = db.query(Machine).options(*_MACHINE_LOAD).filter(Machine.id == machine.id).one()
    return _public_machine(loaded, current_user)


@router.patch("/{machine_id}", response_model=MachinePublic)
def update_machine(
    machine_id: uuid.UUID,
    payload: MachineUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(_admin_write),
) -> MachinePublic:
    machine = get_or_404(db, Machine, machine_id, "Machine not found")
    data = payload.model_dump(exclude_unset=True)
    if "operator_id" in data:
        validate_operator_id(db, data["operator_id"])
    if "supervisor_id" in data:
        validate_supervisor_id(db, data["supervisor_id"])
    if "kind" in data and data["kind"] is not None:
        data["kind"] = data["kind"].value if hasattr(data["kind"], "value") else data["kind"]
    for field, value in data.items():
        setattr(machine, field, value)
    commit_or_409(db, "Could not update machine")
    db.refresh(machine)
    loaded = db.query(Machine).options(*_MACHINE_LOAD).filter(Machine.id == machine.id).one()
    return _public_machine(loaded, current_user)


@router.delete("/{machine_id}", status_code=204)
def delete_machine(
    machine_id: uuid.UUID, db: Session = Depends(get_db), _user: User = Depends(_admin_write)
) -> None:
    machine = get_or_404(db, Machine, machine_id, "Machine not found")
    db.delete(machine)
    commit_or_409(db, "Cannot delete this machine")


@router.get("/{machine_id}/qr")
def machine_qr(
    machine_id: uuid.UUID,
    origin: str = Query(min_length=8),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    require_machine_access(db, current_user, machine_id)
    import qrcode

    target = f"{origin.rstrip('/')}/today"
    qr = qrcode.QRCode(box_size=8, border=2)
    qr.add_data(target)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return Response(content=buf.getvalue(), media_type="image/png")
