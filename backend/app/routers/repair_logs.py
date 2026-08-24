import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_roles
from app.core.utils import commit_or_409, get_or_404
from app.database import get_db
from app.models import Machine, RepairLog, User, UserRole
from app.schemas.repair_logs import RepairLogCreate, RepairLogPublic, RepairLogResolve

router = APIRouter(prefix="/repair-logs", tags=["repair_logs"])

# Reporting an issue is operator+supervisor+admin (floor-level); resolving
# it is supervisor+admin; management is read-only.
_report_roles = require_roles(UserRole.operator, UserRole.supervisor, UserRole.admin)
_resolve_roles = require_roles(UserRole.supervisor, UserRole.admin)


@router.get("", response_model=list[RepairLogPublic])
def list_repair_logs(
    machine_id: uuid.UUID | None = Query(default=None, alias="machineId"),
    unresolved_only: bool = Query(default=False, alias="unresolvedOnly"),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
) -> list[RepairLog]:
    query = db.query(RepairLog)
    if machine_id is not None:
        query = query.filter(RepairLog.machine_id == machine_id)
    if unresolved_only:
        query = query.filter(RepairLog.resolved_at.is_(None))
    return query.order_by(RepairLog.reported_at.desc()).all()


@router.get("/{repair_log_id}", response_model=RepairLogPublic)
def get_repair_log(
    repair_log_id: uuid.UUID, db: Session = Depends(get_db), _user=Depends(get_current_user)
) -> RepairLog:
    return get_or_404(db, RepairLog, repair_log_id, "Repair log not found")


@router.post("", response_model=RepairLogPublic, status_code=201)
def create_repair_log(
    payload: RepairLogCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(_report_roles),
) -> RepairLog:
    machine = get_or_404(db, Machine, payload.machine_id, "Machine not found")
    repair_log = RepairLog(**payload.model_dump(), reported_by=current_user.id)
    db.add(repair_log)
    db.commit()
    db.refresh(repair_log)
    from app.services.notifications import notify_new_repair

    notify_new_repair(db, machine.name, repair_log.issue_description)
    return repair_log


@router.patch("/{repair_log_id}/resolve", response_model=RepairLogPublic)
def resolve_repair_log(
    repair_log_id: uuid.UUID,
    payload: RepairLogResolve,
    db: Session = Depends(get_db),
    current_user: User = Depends(_resolve_roles),
) -> RepairLog:
    repair_log = get_or_404(db, RepairLog, repair_log_id, "Repair log not found")
    repair_log.resolved_at = datetime.now(timezone.utc)
    repair_log.resolved_by = current_user.id
    if payload.resolution_notes is not None:
        repair_log.resolution_notes = payload.resolution_notes
    db.commit()
    db.refresh(repair_log)
    return repair_log


@router.delete("/{repair_log_id}", status_code=204)
def delete_repair_log(
    repair_log_id: uuid.UUID, db: Session = Depends(get_db), _user=Depends(_resolve_roles)
) -> None:
    repair_log = get_or_404(db, RepairLog, repair_log_id, "Repair log not found")
    db.delete(repair_log)
    commit_or_409(db, "Cannot delete this repair log")
