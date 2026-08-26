import io
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.orm import Session, joinedload

from app.core.access import require_machine_access, validate_operator_id, validate_supervisor_id
from app.core.deps import get_current_user, require_roles
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

_write_roles = require_roles(UserRole.supervisor, UserRole.admin)

_MACHINE_LOAD = (joinedload(Machine.operator), joinedload(Machine.supervisor))


def _machines_by_ids(db: Session, machine_ids: list[uuid.UUID]) -> list[Machine]:
    return (
        db.query(Machine)
        .options(*_MACHINE_LOAD)
        .filter(Machine.id.in_(machine_ids))
        .order_by(Machine.name)
        .all()
    )


@router.get("", response_model=list[MachinePublic])
def list_machines(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> list[Machine]:
    query = db.query(Machine).options(*_MACHINE_LOAD).order_by(Machine.group_name.nulls_last(), Machine.name)
    if current_user.role == UserRole.operator:
        query = query.filter(Machine.operator_id == current_user.id)
    return query.all()


@router.put("/operator-assignments", response_model=list[MachinePublic])
def set_operator_assignments(
    payload: MachineOperatorAssignmentsUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(_write_roles),
) -> list[Machine]:
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
    return _machines_by_ids(db, machine_ids)


@router.put("/supervisor-assignments", response_model=list[MachinePublic])
def set_supervisor_assignments(
    payload: MachineSupervisorAssignmentsUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(_write_roles),
) -> list[Machine]:
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
    return _machines_by_ids(db, machine_ids)


@router.get("/{machine_id}", response_model=MachinePublic)
def get_machine(
    machine_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> Machine:
    machine = require_machine_access(db, current_user, machine_id)
    return db.query(Machine).options(*_MACHINE_LOAD).filter(Machine.id == machine.id).one()


@router.post("", response_model=MachinePublic, status_code=201)
def create_machine(
    payload: MachineCreate, db: Session = Depends(get_db), _user: User = Depends(_write_roles)
) -> Machine:
    validate_operator_id(db, payload.operator_id)
    validate_supervisor_id(db, payload.supervisor_id)
    data = payload.model_dump()
    data["kind"] = payload.kind.value
    machine = Machine(**data)
    db.add(machine)
    commit_or_409(db, "Could not create machine")
    db.refresh(machine)
    return db.query(Machine).options(*_MACHINE_LOAD).filter(Machine.id == machine.id).one()


@router.patch("/{machine_id}", response_model=MachinePublic)
def update_machine(
    machine_id: uuid.UUID,
    payload: MachineUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(_write_roles),
) -> Machine:
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
    return db.query(Machine).options(*_MACHINE_LOAD).filter(Machine.id == machine.id).one()


@router.delete("/{machine_id}", status_code=204)
def delete_machine(
    machine_id: uuid.UUID, db: Session = Depends(get_db), _user: User = Depends(_write_roles)
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
