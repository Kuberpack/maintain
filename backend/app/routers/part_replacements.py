import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.access import work_machine_ids, require_machine_access
from app.core.deps import get_current_user, require_roles
from app.core.utils import commit_or_409, get_or_404
from app.database import get_db
from app.models import Machine, PartReplacement, User, UserRole
from app.schemas.part_replacements import (
    PartReplacementCreate,
    PartReplacementPublic,
    PartReplacementUpdate,
)
from app.services.notifications import notify_part_replacement

router = APIRouter(prefix="/part-replacements", tags=["part_replacements"])

# Logging a replacement is operator+supervisor+admin (floor-level);
# editing/deleting a record is supervisor+admin; management is read-only.
_report_roles = require_roles(UserRole.operator, UserRole.supervisor, UserRole.admin)
_write_roles = require_roles(UserRole.supervisor, UserRole.admin)


@router.get("", response_model=list[PartReplacementPublic])
def list_part_replacements(
    machine_id: uuid.UUID | None = Query(default=None, alias="machineId"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[PartReplacement]:
    query = db.query(PartReplacement)
    scoped_ids = work_machine_ids(db, current_user)
    if machine_id is not None:
        require_machine_access(db, current_user, machine_id)
        query = query.filter(PartReplacement.machine_id == machine_id)
    elif scoped_ids is not None:
        if not scoped_ids:
            return []
        query = query.filter(PartReplacement.machine_id.in_(scoped_ids))
    return query.order_by(PartReplacement.replaced_at.desc()).all()


@router.get("/{part_replacement_id}", response_model=PartReplacementPublic)
def get_part_replacement(
    part_replacement_id: uuid.UUID, db: Session = Depends(get_db), _user=Depends(get_current_user)
) -> PartReplacement:
    return get_or_404(db, PartReplacement, part_replacement_id, "Part replacement not found")


@router.post("", response_model=PartReplacementPublic, status_code=201)
def create_part_replacement(
    payload: PartReplacementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(_report_roles),
) -> PartReplacement:
    require_machine_access(db, current_user, payload.machine_id)
    machine = get_or_404(db, Machine, payload.machine_id, "Machine not found")
    part_replacement = PartReplacement(**payload.model_dump(), replaced_by=current_user.id)
    db.add(part_replacement)
    db.commit()
    db.refresh(part_replacement)
    notify_part_replacement(
        db,
        machine.name,
        part_replacement.part_name,
        current_user.name,
        part_replacement.notes,
        machine,
    )
    return part_replacement


@router.patch("/{part_replacement_id}", response_model=PartReplacementPublic)
def update_part_replacement(
    part_replacement_id: uuid.UUID,
    payload: PartReplacementUpdate,
    db: Session = Depends(get_db),
    _user=Depends(_write_roles),
) -> PartReplacement:
    part_replacement = get_or_404(db, PartReplacement, part_replacement_id, "Part replacement not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(part_replacement, field, value)
    db.commit()
    db.refresh(part_replacement)
    return part_replacement


@router.delete("/{part_replacement_id}", status_code=204)
def delete_part_replacement(
    part_replacement_id: uuid.UUID, db: Session = Depends(get_db), _user=Depends(_write_roles)
) -> None:
    part_replacement = get_or_404(db, PartReplacement, part_replacement_id, "Part replacement not found")
    db.delete(part_replacement)
    commit_or_409(db, "Cannot delete this part replacement")
