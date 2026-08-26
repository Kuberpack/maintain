import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.access import work_machine_ids, require_machine_access
from app.core.deps import get_current_user, require_roles
from app.core.time import today_local
from app.core.utils import commit_or_409, get_or_404
from app.database import get_db
from app.models import Machine, ShiftLog, User, UserRole
from app.schemas.shift_logs import ShiftLogPublic, ShiftLogUpsert

router = APIRouter(prefix="/shift-logs", tags=["shift_logs"])

_write_roles = require_roles(UserRole.operator, UserRole.supervisor, UserRole.admin)
_correct_roles = require_roles(UserRole.supervisor, UserRole.admin)


def _require_edit_window(current_user: User, log_date: date) -> None:
    """Operators own today's row only. Correcting an earlier day is a
    supervisor job so yesterday's production numbers can't quietly move after
    they've been read."""
    if current_user.role == UserRole.operator and log_date != today_local():
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Only today's shift log can be edited. Ask a supervisor to correct an earlier day.",
        )


@router.get("", response_model=list[ShiftLogPublic])
def list_shift_logs(
    machine_id: uuid.UUID | None = Query(default=None, alias="machineId"),
    date_from: date | None = Query(default=None, alias="dateFrom"),
    date_to: date | None = Query(default=None, alias="dateTo"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ShiftLog]:
    query = db.query(ShiftLog)
    scoped_ids = work_machine_ids(db, current_user)
    if machine_id is not None:
        require_machine_access(db, current_user, machine_id)
        query = query.filter(ShiftLog.machine_id == machine_id)
    elif scoped_ids is not None:
        if not scoped_ids:
            return []
        query = query.filter(ShiftLog.machine_id.in_(scoped_ids))
    if date_from is not None:
        query = query.filter(ShiftLog.log_date >= date_from)
    if date_to is not None:
        query = query.filter(ShiftLog.log_date <= date_to)
    return query.order_by(ShiftLog.log_date.desc()).all()


@router.put("", response_model=ShiftLogPublic)
def upsert_shift_log(
    payload: ShiftLogUpsert,
    db: Session = Depends(get_db),
    current_user: User = Depends(_write_roles),
) -> ShiftLog:
    """Create or update the one row for this machine and date.

    An upsert rather than POST+PATCH because the sheet itself is one row per
    machine per day: the operator saves it repeatedly through the shift, and
    a second save is a correction, not a new record.

    The whole row is replaced on every save, so callers must send every field
    they want kept -- an omitted field is read as "cleared", not "unchanged".
    That matches the form, which always submits the full sheet.
    """
    require_machine_access(db, current_user, payload.machine_id)
    get_or_404(db, Machine, payload.machine_id, "Machine not found")
    _require_edit_window(current_user, payload.log_date)

    log = (
        db.query(ShiftLog)
        .filter(ShiftLog.machine_id == payload.machine_id, ShiftLog.log_date == payload.log_date)
        .one_or_none()
    )
    if log is None:
        log = ShiftLog(**payload.model_dump(), created_by=current_user.id)
        db.add(log)
    else:
        for field, value in payload.model_dump().items():
            setattr(log, field, value)
    commit_or_409(db, "A shift log already exists for this machine and date")
    db.refresh(log)
    return log


@router.delete("/{shift_log_id}", status_code=204)
def delete_shift_log(
    shift_log_id: uuid.UUID, db: Session = Depends(get_db), _user=Depends(_correct_roles)
) -> None:
    log = get_or_404(db, ShiftLog, shift_log_id, "Shift log not found")
    db.delete(log)
    commit_or_409(db, "Cannot delete this shift log")
