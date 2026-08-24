import io
import uuid

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session, joinedload

from app.core.access import require_machine_access, validate_operator_id
from app.core.deps import get_current_user, require_roles
from app.core.utils import commit_or_409, get_or_404
from app.database import get_db
from app.models import Machine, User, UserRole
from app.schemas.machines import MachineCreate, MachinePublic, MachineUpdate

router = APIRouter(prefix="/machines", tags=["machines"])

_write_roles = require_roles(UserRole.supervisor, UserRole.admin)


@router.get("", response_model=list[MachinePublic])
def list_machines(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> list[Machine]:
    query = db.query(Machine).options(joinedload(Machine.operator)).order_by(Machine.name)
    if current_user.role == UserRole.operator:
        query = query.filter(Machine.operator_id == current_user.id)
    return query.all()


@router.get("/{machine_id}", response_model=MachinePublic)
def get_machine(
    machine_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> Machine:
    machine = require_machine_access(db, current_user, machine_id)
    db.refresh(machine)
    return db.query(Machine).options(joinedload(Machine.operator)).filter(Machine.id == machine.id).one()


@router.post("", response_model=MachinePublic, status_code=201)
def create_machine(
    payload: MachineCreate, db: Session = Depends(get_db), _user: User = Depends(_write_roles)
) -> Machine:
    validate_operator_id(db, payload.operator_id)
    machine = Machine(**payload.model_dump())
    db.add(machine)
    commit_or_409(db, "This operator is already assigned to another machine")
    db.refresh(machine)
    return db.query(Machine).options(joinedload(Machine.operator)).filter(Machine.id == machine.id).one()


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
    for field, value in data.items():
        setattr(machine, field, value)
    commit_or_409(db, "This operator is already assigned to another machine")
    db.refresh(machine)
    return db.query(Machine).options(joinedload(Machine.operator)).filter(Machine.id == machine.id).one()


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
