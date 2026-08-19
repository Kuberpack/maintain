import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_roles
from app.core.utils import commit_or_409, get_or_404
from app.database import get_db
from app.models import Machine, UserRole
from app.schemas.machines import MachineCreate, MachinePublic, MachineUpdate

router = APIRouter(prefix="/machines", tags=["machines"])

# Management is explicitly read-only (architecture.md); only supervisor writes.
_write_roles = require_roles(UserRole.supervisor)


@router.get("", response_model=list[MachinePublic])
def list_machines(db: Session = Depends(get_db), _user=Depends(get_current_user)) -> list[Machine]:
    return db.query(Machine).order_by(Machine.name).all()


@router.get("/{machine_id}", response_model=MachinePublic)
def get_machine(
    machine_id: uuid.UUID, db: Session = Depends(get_db), _user=Depends(get_current_user)
) -> Machine:
    return get_or_404(db, Machine, machine_id, "Machine not found")


@router.post("", response_model=MachinePublic, status_code=201)
def create_machine(
    payload: MachineCreate, db: Session = Depends(get_db), _user=Depends(_write_roles)
) -> Machine:
    machine = Machine(**payload.model_dump())
    db.add(machine)
    db.commit()
    db.refresh(machine)
    return machine


@router.patch("/{machine_id}", response_model=MachinePublic)
def update_machine(
    machine_id: uuid.UUID,
    payload: MachineUpdate,
    db: Session = Depends(get_db),
    _user=Depends(_write_roles),
) -> Machine:
    machine = get_or_404(db, Machine, machine_id, "Machine not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(machine, field, value)
    db.commit()
    db.refresh(machine)
    return machine


@router.delete("/{machine_id}", status_code=204)
def delete_machine(
    machine_id: uuid.UUID, db: Session = Depends(get_db), _user=Depends(_write_roles)
) -> None:
    machine = get_or_404(db, Machine, machine_id, "Machine not found")
    db.delete(machine)
    commit_or_409(db, "Cannot delete this machine")
