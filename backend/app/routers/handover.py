import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.access import operator_machine_ids, require_machine_access
from app.core.deps import get_current_user, require_roles
from app.core.utils import get_or_404
from app.database import get_db
from app.models import HandoverNote, Machine, User, UserRole
from app.schemas.handover import HandoverNoteCreate, HandoverNotePublic

router = APIRouter(prefix="/handover-notes", tags=["handover_notes"])

_write_roles = require_roles(UserRole.operator, UserRole.supervisor, UserRole.admin)


@router.get("", response_model=list[HandoverNotePublic])
def list_handover_notes(
    machine_id: uuid.UUID | None = Query(default=None, alias="machineId"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[HandoverNote]:
    query = db.query(HandoverNote)
    scoped_ids = operator_machine_ids(db, current_user)
    if scoped_ids is not None:
        if not scoped_ids:
            return []
        query = query.filter(HandoverNote.machine_id.in_(scoped_ids))
    elif machine_id is not None:
        query = query.filter(HandoverNote.machine_id == machine_id)
    return query.order_by(HandoverNote.created_at.desc()).limit(50).all()


@router.post("", response_model=HandoverNotePublic, status_code=201)
def create_handover_note(
    payload: HandoverNoteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(_write_roles),
) -> HandoverNote:
    require_machine_access(db, current_user, payload.machine_id)
    get_or_404(db, Machine, payload.machine_id, "Machine not found")
    note = HandoverNote(machine_id=payload.machine_id, note=payload.note, created_by=current_user.id)
    db.add(note)
    db.commit()
    db.refresh(note)
    return note
