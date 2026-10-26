import uuid
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.access import require_machine_access, work_machine_ids
from app.core.deps import require_roles
from app.core.time import today_local
from app.database import get_db
from app.models import (
    Machine,
    PartReplacement,
    RemovedPart,
    RemovedPartStatus,
    User,
    UserRole,
)
from app.schemas.removed_parts import (
    DispositionCount,
    MachineReplacementCount,
    MonthTotal,
    RemovedPartDisposition,
    RemovedPartPublic,
    RemovedPartsReport,
    ScrapTotal,
)
from app.services.removed_parts import STALE_PENDING_DAYS, update_disposition
from app.services.spares import OutOfStock

router = APIRouter(prefix="/removed-parts", tags=["removed_parts"])

# The stores trail is a supervisor/management view. Operators see the same
# trail on the machine they already work. Only supervisor and admin move a
# part to its disposition — management reads the report.
_read_roles = require_roles(UserRole.supervisor, UserRole.management, UserRole.admin)
_write_roles = require_roles(UserRole.supervisor, UserRole.admin)

# part_replacement is also an explicit join for the date filter, so it must
# not be a joinedload on the same query (SQLAlchemy rejects that mix).
_LOAD = (
    selectinload(RemovedPart.events),
    joinedload(RemovedPart.machine),
    joinedload(RemovedPart.credited_spare),
    selectinload(RemovedPart.part_replacement).joinedload(PartReplacement.replaced_by_user),
)


def _load(db: Session, removed_part_id: uuid.UUID) -> RemovedPart | None:
    return (
        db.query(RemovedPart)
        .options(*_LOAD)
        .filter(RemovedPart.id == removed_part_id)
        .one_or_none()
    )


def _scoped_query(db: Session, user: User):
    query = db.query(RemovedPart).join(RemovedPart.part_replacement).options(*_LOAD)
    scoped_ids = work_machine_ids(db, user)
    if scoped_ids is not None:
        if not scoped_ids:
            return None
        query = query.filter(RemovedPart.machine_id.in_(scoped_ids))
    return query


@router.get("", response_model=list[RemovedPartPublic])
def list_removed_parts(
    status_filter: RemovedPartStatus | None = Query(default=None, alias="status"),
    machine_id: uuid.UUID | None = Query(default=None, alias="machineId"),
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    pending_only: bool = Query(default=False, alias="pendingOnly"),
    stale_only: bool = Query(default=False, alias="staleOnly"),
    stale_days: int = Query(default=STALE_PENDING_DAYS, alias="staleDays", ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(_read_roles),
) -> list[RemovedPart]:
    if machine_id is not None:
        require_machine_access(db, current_user, machine_id)
    query = _scoped_query(db, current_user)
    if query is None:
        return []
    if machine_id is not None:
        query = query.filter(RemovedPart.machine_id == machine_id)
    if status_filter is not None:
        query = query.filter(RemovedPart.status == status_filter)
    if pending_only or stale_only:
        query = query.filter(RemovedPart.status == RemovedPartStatus.pending_decision)
    if from_date is not None:
        query = query.filter(PartReplacement.replaced_at >= from_date)
    if to_date is not None:
        query = query.filter(PartReplacement.replaced_at <= to_date)
    if stale_only:
        cutoff = today_local() - timedelta(days=stale_days)
        query = query.filter(PartReplacement.replaced_at <= cutoff)
    return query.order_by(PartReplacement.replaced_at.desc(), RemovedPart.created_at.desc()).all()


@router.get("/report", response_model=RemovedPartsReport)
def removed_parts_report(
    stale_days: int = Query(default=STALE_PENDING_DAYS, alias="staleDays", ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(_read_roles),
) -> RemovedPartsReport:
    return _build_report(db, current_user, stale_days)


@router.get("/{removed_part_id}", response_model=RemovedPartPublic)
def get_removed_part(
    removed_part_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(_read_roles),
) -> RemovedPart:
    row = _load(db, removed_part_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Removed part not found")
    require_machine_access(db, current_user, row.machine_id)
    return row


@router.post("/{removed_part_id}/disposition", response_model=RemovedPartPublic)
def set_disposition(
    removed_part_id: uuid.UUID,
    payload: RemovedPartDisposition,
    db: Session = Depends(get_db),
    current_user: User = Depends(_write_roles),
) -> RemovedPart:
    if current_user.role not in (UserRole.supervisor, UserRole.admin):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not permitted for this role")
    row = _load(db, removed_part_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Removed part not found")
    require_machine_access(db, current_user, row.machine_id)
    try:
        update_disposition(db, row, current_user, payload)
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    except OutOfStock as exc:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    except LookupError as exc:
        db.rollback()
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    loaded = _load(db, removed_part_id)
    if loaded is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Removed part not found")
    return loaded


def _parts_query(db: Session, scoped_ids: list[uuid.UUID] | None):
    query = db.query(RemovedPart)
    if scoped_ids is not None:
        query = query.filter(RemovedPart.machine_id.in_(scoped_ids))
    return query


def _build_report(db: Session, user: User, stale_days: int) -> RemovedPartsReport:
    empty = RemovedPartsReport(
        by_status=[DispositionCount(status=item, count=0) for item in RemovedPartStatus],
        pending=0,
        pending_older_than_days=0,
        stale_days=stale_days,
        months=[],
        machines=[],
    )
    scoped_ids = work_machine_ids(db, user)
    if scoped_ids is not None and not scoped_ids:
        return empty

    parts = _parts_query(db, scoped_ids)
    counts = {item: 0 for item in RemovedPartStatus}
    grouped = parts.with_entities(RemovedPart.status, func.count(RemovedPart.id)).group_by(RemovedPart.status)
    for status_value, count in grouped:
        counts[RemovedPartStatus(status_value)] = count

    cutoff = today_local() - timedelta(days=stale_days)
    pending_older = (
        _parts_query(db, scoped_ids)
        .filter(RemovedPart.status == RemovedPartStatus.pending_decision)
        .join(RemovedPart.part_replacement)
        .filter(PartReplacement.replaced_at <= cutoff)
        .count()
    )

    month_scrap: dict[str, dict[str, float]] = {}
    month_scrap_count: dict[str, int] = {}
    month_resale_count: dict[str, int] = {}
    month_resale_amount: dict[str, float] = {}
    for row in _parts_query(db, scoped_ids).filter(
        RemovedPart.status.in_([RemovedPartStatus.scrapped, RemovedPartStatus.sold])
    ):
        if row.status == RemovedPartStatus.scrapped and row.scrap_on is not None:
            key = row.scrap_on.strftime("%Y-%m")
            month_scrap_count[key] = month_scrap_count.get(key, 0) + 1
            unit = (row.scrap_unit or "kg").strip() or "kg"
            bucket = month_scrap.setdefault(key, {})
            bucket[unit] = bucket.get(unit, 0.0) + float(row.scrap_qty or 0)
        if row.status == RemovedPartStatus.sold and row.sale_on is not None:
            key = row.sale_on.strftime("%Y-%m")
            month_resale_count[key] = month_resale_count.get(key, 0) + 1
            month_resale_amount[key] = month_resale_amount.get(key, 0.0) + float(row.sale_amount or 0)

    months = []
    for key in sorted(set(month_scrap_count) | set(month_resale_count), reverse=True):
        scrap = month_scrap.get(key, {})
        months.append(
            MonthTotal(
                month=key,
                scrap_count=month_scrap_count.get(key, 0),
                scrap=[ScrapTotal(unit=unit, qty=round(qty, 3)) for unit, qty in sorted(scrap.items())],
                resale_count=month_resale_count.get(key, 0),
                resale_amount=round(month_resale_amount.get(key, 0.0), 2),
            )
        )

    machine_rows = (
        db.query(Machine.id, Machine.name, func.count(PartReplacement.id))
        .join(PartReplacement, PartReplacement.machine_id == Machine.id)
        .group_by(Machine.id, Machine.name)
        .order_by(func.count(PartReplacement.id).desc(), Machine.name)
    )
    if scoped_ids is not None:
        machine_rows = machine_rows.filter(Machine.id.in_(scoped_ids))
    machines = [
        MachineReplacementCount(machine_id=machine_id, machine_name=name, replacements=count)
        for machine_id, name, count in machine_rows.limit(8)
    ]

    return RemovedPartsReport(
        by_status=[DispositionCount(status=status, count=counts[status]) for status in RemovedPartStatus],
        pending=counts[RemovedPartStatus.pending_decision],
        pending_older_than_days=pending_older,
        stale_days=stale_days,
        months=months,
        machines=machines,
    )
