"""Store consumables: issue slips, returns, close-out, counts, and the daily sheet.

Stock identity: qty_on_hand equals the sum of consumable_moves.qty_delta.
An issue subtracts the full quantity. A MIN (and any extra return entered at
close-out) adds it back. Quantity used and quantity left at the machine stay
out of the store. Unaccounted quantity is leakage and does not come back.

Shift clocks below are provisional (see CONFIRM_LATER.md). A slip still open
after the following shift has ended is "older than 1 shift".
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.config import get_settings
from app.core.access import work_machine_ids
from app.core.time import today_local
from app.models import (
    ConsumableCount,
    ConsumableItem,
    ConsumableMove,
    ConsumableReturn,
    ConsumableSlip,
    ConsumableSlipCounter,
    ConsumableSlipLine,
    Machine,
    User,
    UserRole,
)
from app.schemas.consumables import (
    CloseLineIn,
    ConfirmSlipIn,
    ConsumableItemCreate,
    ConsumableItemPublic,
    ConsumableItemUpdate,
    DailyDay,
    DailyItemRow,
    DailySheet,
    InwardCreate,
    LeakageBucket,
    LeakageReport,
    MonthBucket,
    ReturnCreate,
    ReturnPublic,
    SlipCreate,
    SlipLinePublic,
    SlipPublic,
    StaleSlipRow,
    StockCountCreate,
    StockCountPublic,
)

QTY_EPS = 0.0005
SHIFTS = ("A", "B", "C")
# Provisional Sonipat clocks. A 06:00–14:00, B 14:00–22:00, C 22:00–06:00.
SHIFT_START: dict[str, time] = {"A": time(6, 0), "B": time(14, 0), "C": time(22, 0)}
SHIFT_HOURS = 8


class ConsumableError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def round_qty(value: float) -> float:
    return round(float(value), 3)


def round_money(value: float) -> float:
    return round(float(value), 2)


def financial_year(day: date) -> str:
    """Indian FY label, April–March. 13 Nov 2026 -> 2026-27. 31 Mar 2026 -> 2025-26."""
    start = day.year if day.month >= 4 else day.year - 1
    return f"{start}-{(start + 1) % 100:02d}"


def financial_year_bounds(day: date) -> tuple[date, date]:
    start_year = day.year if day.month >= 4 else day.year - 1
    return date(start_year, 4, 1), date(start_year + 1, 3, 31)


def slip_no_label(number: int) -> str:
    return f"{number:02d}" if number < 100 else str(number)


def leakage_qty(issued: float, used: float, returned: float, carried: float) -> float:
    return round_qty(issued - used - returned - carried)


def balance_status(*, closed: bool, returned: float, leakage: float | None) -> str:
    if not closed:
        return "partial" if returned > QTY_EPS else "open"
    if leakage is None:
        return "open"
    return "leakage" if leakage > QTY_EPS else "balanced"


def expected_usage(standard_qty: float | None, standard_per: float | None, production_qty: float | None) -> float | None:
    if standard_qty is None or standard_per is None or production_qty is None:
        return None
    if standard_per <= QTY_EPS:
        return None
    return round_qty(standard_qty * (production_qty / standard_per))


def variance_pct(actual: float, expected: float | None) -> float | None:
    if expected is None or abs(expected) <= QTY_EPS:
        return None
    return round((actual - expected) / expected * 100, 1)


def plant_tz() -> ZoneInfo:
    return ZoneInfo(get_settings().local_timezone)


def now_local() -> datetime:
    return datetime.now(plant_tz())


def shift_end(slip_date: date, shift: str, tz: ZoneInfo) -> datetime:
    start = datetime.combine(slip_date, SHIFT_START[shift], tzinfo=tz)
    return start + timedelta(hours=SHIFT_HOURS)


def shift_has_aged(slip_date: date, shift: str, now: datetime) -> bool:
    """True once the shift after this one has also ended."""
    tz = now.tzinfo
    if not isinstance(tz, ZoneInfo):
        tz = plant_tz()
        now = now.replace(tzinfo=tz)
    return now >= shift_end(slip_date, shift, tz) + timedelta(hours=SHIFT_HOURS)


def current_shift(now: datetime | None = None) -> str:
    moment = now or now_local()
    hour = moment.hour
    if 6 <= hour < 14:
        return "A"
    if 14 <= hour < 22:
        return "B"
    return "C"


def month_bounds(month: str) -> tuple[date, date, int]:
    try:
        year_text, month_text = month.split("-")
        year = int(year_text)
        month_no = int(month_text)
        start = date(year, month_no, 1)
    except (ValueError, AttributeError):
        raise ConsumableError(422, "Month must look like 2026-11") from None
    if start.month == 12:
        nxt = date(start.year + 1, 1, 1)
    else:
        nxt = date(start.year, start.month + 1, 1)
    return start, nxt, (nxt - start).days


def _clean(value: str | None) -> str:
    if value is None:
        return ""
    return value.strip()


def _optional(value: str | None) -> str | None:
    text = _clean(value)
    return text or None


def item_public(item: ConsumableItem) -> ConsumableItemPublic:
    return ConsumableItemPublic.model_validate(item)


def _require_stock_bounds(min_stock: float, max_stock: float | None) -> None:
    if max_stock is not None and max_stock + QTY_EPS < min_stock:
        raise ConsumableError(422, "Max stock cannot be below min stock")


def _require_standard(qty: float | None, per: float | None, basis: str | None) -> None:
    present = [qty is not None, per is not None, bool(_clean(basis))]
    if any(present) and not all(present):
        raise ConsumableError(422, "Usage standard needs a quantity, a per-quantity, and a basis (boxes or ton of board)")


def _commit(db: Session, conflict: str) -> None:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConsumableError(409, conflict) from None


def _lock_item(db: Session, item_id: uuid.UUID) -> ConsumableItem:
    item = db.query(ConsumableItem).filter(ConsumableItem.id == item_id).with_for_update().one_or_none()
    if item is None:
        raise ConsumableError(404, "Item not found")
    return item


def _add_move(
    db: Session,
    item: ConsumableItem,
    *,
    kind: str,
    qty_delta: float,
    moved_on: date,
    actor: User,
    line_id: uuid.UUID | None = None,
    note: str | None = None,
) -> None:
    delta = round_qty(qty_delta)
    item.qty_on_hand = round_qty(item.qty_on_hand + delta)
    db.add(
        ConsumableMove(
            item_id=item.id,
            kind=kind,
            qty_delta=delta,
            moved_on=moved_on,
            line_id=line_id,
            note=_optional(note),
            actor_id=actor.id,
            actor_name=actor.name,
        )
    )


def create_item(
    db: Session,
    payload: ConsumableItemCreate,
    actor: User,
    *,
    opening_on: date | None = None,
) -> ConsumableItem:
    name = _clean(payload.name)
    unit = _clean(payload.unit)
    if not name or not unit:
        raise ConsumableError(422, "Name and unit are required")
    _require_stock_bounds(payload.min_stock, payload.max_stock)
    _require_standard(payload.standard_qty, payload.standard_per, payload.standard_basis)
    item = ConsumableItem(
        name=name,
        item_group=_clean(payload.item_group),
        party_name=_optional(payload.party_name),
        party_address=_optional(payload.party_address),
        contact_no=_optional(payload.contact_no),
        lead_time_days=payload.lead_time_days,
        min_stock=round_qty(payload.min_stock),
        max_stock=None if payload.max_stock is None else round_qty(payload.max_stock),
        rate=round_money(payload.rate),
        unit=unit,
        qty_on_hand=0,
        tracks_empty_core=payload.tracks_empty_core,
        standard_qty=payload.standard_qty,
        standard_per=payload.standard_per,
        standard_basis=_optional(payload.standard_basis),
        active=payload.active,
    )
    db.add(item)
    db.flush()
    opening = round_qty(payload.qty_on_hand)
    if opening > QTY_EPS:
        _add_move(
            db,
            item,
            kind="opening",
            qty_delta=opening,
            moved_on=opening_on or today_local(),
            actor=actor,
            note="Opening stock",
        )
    _commit(db, "An item with this name already exists")
    db.refresh(item)
    return item


def update_item(db: Session, item_id: uuid.UUID, payload: ConsumableItemUpdate) -> ConsumableItem:
    item = db.get(ConsumableItem, item_id)
    if item is None:
        raise ConsumableError(404, "Item not found")
    changes = payload.model_dump(exclude_unset=True)
    clear_standard = bool(changes.pop("clear_standard", False))
    clear_max = bool(changes.pop("clear_max_stock", False))
    if "name" in changes:
        changes["name"] = _clean(changes["name"])
        if not changes["name"]:
            raise ConsumableError(422, "Name is required")
    if "unit" in changes:
        changes["unit"] = _clean(changes["unit"])
        if not changes["unit"]:
            raise ConsumableError(422, "Unit is required")
    if "item_group" in changes:
        changes["item_group"] = _clean(changes["item_group"])
    for text_field in ("party_name", "party_address", "contact_no", "standard_basis"):
        if text_field in changes:
            changes[text_field] = _optional(changes[text_field])
    if "min_stock" in changes and changes["min_stock"] is not None:
        changes["min_stock"] = round_qty(changes["min_stock"])
    if "max_stock" in changes and changes["max_stock"] is not None:
        changes["max_stock"] = round_qty(changes["max_stock"])
    if "rate" in changes and changes["rate"] is not None:
        changes["rate"] = round_money(changes["rate"])
    for key, value in changes.items():
        setattr(item, key, value)
    if clear_max:
        item.max_stock = None
    if clear_standard:
        item.standard_qty = None
        item.standard_per = None
        item.standard_basis = None
    _require_stock_bounds(item.min_stock, item.max_stock)
    _require_standard(item.standard_qty, item.standard_per, item.standard_basis)
    _commit(db, "An item with this name already exists")
    db.refresh(item)
    return item


def list_items(
    db: Session,
    *,
    search: str | None = None,
    item_group: str | None = None,
    low_stock: bool = False,
    include_inactive: bool = False,
) -> list[ConsumableItem]:
    query = db.query(ConsumableItem)
    if not include_inactive:
        query = query.filter(ConsumableItem.active.is_(True))
    if search and search.strip():
        like = f"%{search.strip()}%"
        query = query.filter(
            or_(
                ConsumableItem.name.ilike(like),
                ConsumableItem.item_group.ilike(like),
                ConsumableItem.party_name.ilike(like),
            )
        )
    if item_group is not None and item_group.strip():
        query = query.filter(ConsumableItem.item_group == item_group.strip())
    if low_stock:
        query = query.filter(
            or_(ConsumableItem.qty_on_hand <= 0, ConsumableItem.qty_on_hand <= ConsumableItem.min_stock)
        )
    return query.order_by(ConsumableItem.item_group, ConsumableItem.name).all()


def receive_inward(db: Session, item_id: uuid.UUID, payload: InwardCreate, actor: User) -> ConsumableItem:
    item = _lock_item(db, item_id)
    moved_on = payload.received_on or today_local()
    _reject_future(moved_on, "Receipt date")
    _add_move(db, item, kind="inward", qty_delta=payload.qty, moved_on=moved_on, actor=actor, note=payload.note)
    _commit(db, "Could not record this receipt")
    db.refresh(item)
    return item


def record_count(db: Session, item_id: uuid.UUID, payload: StockCountCreate, actor: User) -> ConsumableCount:
    item = _lock_item(db, item_id)
    counted_on = payload.counted_on or today_local()
    _reject_future(counted_on, "Count date")
    book = round_qty(item.qty_on_hand)
    counted = round_qty(payload.counted_qty)
    variance = round_qty(counted - book)
    count = ConsumableCount(
        item_id=item.id,
        book_qty=book,
        counted_qty=counted,
        variance=variance,
        note=_optional(payload.note),
        counted_by_id=actor.id,
        counted_by_name=actor.name,
        counted_on=counted_on,
    )
    db.add(count)
    if abs(variance) > QTY_EPS:
        _add_move(
            db,
            item,
            kind="count",
            qty_delta=variance,
            moved_on=counted_on,
            actor=actor,
            note=payload.note or "Physical count",
        )
    _commit(db, "Could not record this count")
    db.refresh(count)
    return count


def list_counts(db: Session, item_id: uuid.UUID) -> list[ConsumableCount]:
    if db.get(ConsumableItem, item_id) is None:
        raise ConsumableError(404, "Item not found")
    return (
        db.query(ConsumableCount)
        .filter(ConsumableCount.item_id == item_id)
        .order_by(ConsumableCount.counted_on.desc(), ConsumableCount.created_at.desc())
        .limit(12)
        .all()
    )


def _reject_future(day: date, label: str) -> None:
    if day > today_local() + timedelta(days=1):
        raise ConsumableError(422, f"{label} cannot be in the future")


def _machine_for_issue(db: Session, user: User, machine_id: uuid.UUID) -> Machine:
    machine = db.get(Machine, machine_id)
    if machine is None:
        raise ConsumableError(404, "Machine not found")
    if user.role == UserRole.operator:
        raise ConsumableError(403, "Operators cannot issue store slips")
    if user.role == UserRole.supervisor:
        allowed = work_machine_ids(db, user) or []
        if machine.id not in allowed:
            raise ConsumableError(403, "This machine is assigned to another supervisor")
    return machine


def _receiver(db: Session, user_id: uuid.UUID) -> User:
    user = db.get(User, user_id)
    if user is None or user.role != UserRole.operator:
        raise ConsumableError(422, "Received by must be an operator")
    return user


def slip_visible(db: Session, user: User, slip: ConsumableSlip) -> bool:
    if user.role in (UserRole.management, UserRole.admin):
        return True
    if user.role == UserRole.operator:
        return slip.received_by_id == user.id
    if user.role == UserRole.supervisor:
        allowed = work_machine_ids(db, user) or []
        return slip.machine_id in allowed
    return False


def _load_slip(db: Session, slip_id: uuid.UUID) -> ConsumableSlip | None:
    return (
        db.query(ConsumableSlip)
        .options(
            selectinload(ConsumableSlip.lines).selectinload(ConsumableSlipLine.returns),
            selectinload(ConsumableSlip.lines).selectinload(ConsumableSlipLine.item),
        )
        .filter(ConsumableSlip.id == slip_id)
        .one_or_none()
    )


def require_slip(db: Session, user: User, slip_id: uuid.UUID) -> ConsumableSlip:
    slip = _load_slip(db, slip_id)
    if slip is None or not slip_visible(db, user, slip):
        raise ConsumableError(404, "Slip not found")
    return slip


def _can_touch_line(user: User) -> None:
    if user.role not in (UserRole.operator, UserRole.supervisor, UserRole.management, UserRole.admin):
        raise ConsumableError(403, "Not permitted for this role")


def allocate_slip_no(db: Session, fy: str) -> int:
    row = db.query(ConsumableSlipCounter).filter_by(financial_year=fy).with_for_update().one_or_none()
    if row is None:
        row = ConsumableSlipCounter(financial_year=fy, last_number=1)
        db.add(row)
        db.flush()
        return 1
    row.last_number += 1
    db.flush()
    return row.last_number


def create_slip(
    db: Session,
    payload: SlipCreate,
    actor: User,
    *,
    core_policy: str = "warn",
    now: datetime | None = None,
) -> tuple[ConsumableSlip, list[str]]:
    del now  # slip ageing uses the slip date, not the insert time
    _reject_future(payload.slip_date, "Slip date")
    department = _clean(payload.department)
    if not department:
        raise ConsumableError(422, "Department is required")
    machine = _machine_for_issue(db, actor, payload.machine_id)
    receiver = _receiver(db, payload.received_by_id)
    item_ids = sorted({line.item_id for line in payload.lines}, key=lambda value: str(value))
    locked = (
        db.query(ConsumableItem)
        .filter(ConsumableItem.id.in_(item_ids))
        .with_for_update()
        .order_by(ConsumableItem.id)
        .all()
    )
    by_id = {item.id: item for item in locked}
    if len(by_id) != len(item_ids):
        raise ConsumableError(422, "One of the items no longer exists")

    requested: dict[uuid.UUID, float] = {}
    for line in payload.lines:
        requested[line.item_id] = round_qty(requested.get(line.item_id, 0) + round_qty(line.qty))

    warnings: list[str] = []
    for item_id, qty in requested.items():
        item = by_id[item_id]
        if not item.active:
            raise ConsumableError(422, f"{item.name} is inactive")
        if item.qty_on_hand + QTY_EPS < qty:
            raise ConsumableError(
                409,
                f"Not enough {item.name} in stock ({round_qty(item.qty_on_hand)} {item.unit} on hand)",
            )
        if item.tracks_empty_core and item.cores_outstanding > 0:
            message = f"{item.name}: previous empty core not returned ({item.cores_outstanding} open)"
            if core_policy == "block" and not (
                payload.override_missing_cores and actor.role in (UserRole.management, UserRole.admin)
            ):
                raise ConsumableError(409, message)
            warnings.append(message)

    fy = financial_year(payload.slip_date)
    slip = ConsumableSlip(
        financial_year=fy,
        slip_no=allocate_slip_no(db, fy),
        slip_date=payload.slip_date,
        shift=payload.shift,
        department=department,
        machine_id=machine.id,
        machine_name=machine.name,
        issued_by_id=actor.id,
        issued_by_name=actor.name,
        received_by_id=receiver.id,
        received_by_name=receiver.name,
        hod_name=_optional(payload.hod_name),
        remark=_optional(payload.remark),
    )
    db.add(slip)
    db.flush()
    for index, line in enumerate(payload.lines, start=1):
        item = by_id[line.item_id]
        qty = round_qty(line.qty)
        core_due = bool(item.tracks_empty_core)
        row = ConsumableSlipLine(
            slip_id=slip.id,
            line_no=index,
            item_id=item.id,
            item_name=item.name,
            unit=item.unit,
            rate=item.rate,
            qty_issued=qty,
            qty_returned=0,
            core_due=core_due,
        )
        db.add(row)
        db.flush()
        _add_move(
            db,
            item,
            kind="issue",
            qty_delta=-qty,
            moved_on=payload.slip_date,
            actor=actor,
            line_id=row.id,
            note=f"Slip {fy}/{slip_no_label(slip.slip_no)}",
        )
        if core_due:
            item.cores_outstanding += 1
    _commit(db, "Could not save this slip. Try again.")
    loaded = _load_slip(db, slip.id)
    if loaded is None:
        raise ConsumableError(500, "Slip was saved but could not be reloaded")
    return loaded, warnings


def list_slips(db: Session, user: User) -> list[ConsumableSlip]:
    query = db.query(ConsumableSlip).options(
        selectinload(ConsumableSlip.lines).selectinload(ConsumableSlipLine.returns),
        selectinload(ConsumableSlip.lines).selectinload(ConsumableSlipLine.item),
    )
    if user.role == UserRole.operator:
        query = query.filter(ConsumableSlip.received_by_id == user.id)
    elif user.role == UserRole.supervisor:
        allowed = work_machine_ids(db, user) or []
        if not allowed:
            return []
        query = query.filter(ConsumableSlip.machine_id.in_(allowed))
    elif user.role not in (UserRole.management, UserRole.admin):
        return []
    return query.order_by(ConsumableSlip.slip_date.desc(), ConsumableSlip.slip_no.desc()).limit(400).all()


def _line_on_slip(slip: ConsumableSlip, line_id: uuid.UUID) -> ConsumableSlipLine:
    for line in slip.lines:
        if line.id == line_id:
            return line
    raise ConsumableError(404, "Slip line not found")


def return_material(
    db: Session,
    user: User,
    slip_id: uuid.UUID,
    line_id: uuid.UUID,
    payload: ReturnCreate,
) -> ConsumableSlip:
    _can_touch_line(user)
    slip = require_slip(db, user, slip_id)
    line = _line_on_slip(slip, line_id)
    if line.closed_at is not None:
        raise ConsumableError(409, "This line is already closed. Include any further return in the close-out.")
    qty = round_qty(payload.qty)
    if qty <= QTY_EPS:
        raise ConsumableError(422, "Return quantity must be more than zero")
    room = round_qty(line.qty_issued - line.qty_returned)
    if qty - room > QTY_EPS:
        raise ConsumableError(422, f"Only {room:g} {line.unit} can still come back on this line")
    returned_on = payload.returned_on or today_local()
    _reject_future(returned_on, "Return date")
    item = _lock_item(db, line.item_id)
    _add_move(
        db,
        item,
        kind="return",
        qty_delta=qty,
        moved_on=returned_on,
        actor=user,
        line_id=line.id,
        note=payload.note or "MIN",
    )
    line.qty_returned = round_qty(line.qty_returned + qty)
    db.add(
        ConsumableReturn(
            line_id=line.id,
            qty=qty,
            note=_optional(payload.note),
            returned_by_id=user.id,
            returned_by_name=user.name,
            returned_on=returned_on,
        )
    )
    _commit(db, "Could not record this return")
    loaded = _load_slip(db, slip.id)
    if loaded is None:
        raise ConsumableError(500, "Return was saved but the slip could not be reloaded")
    return loaded


def close_line(
    db: Session,
    user: User,
    slip_id: uuid.UUID,
    line_id: uuid.UUID,
    payload: CloseLineIn,
) -> ConsumableSlip:
    _can_touch_line(user)
    slip = require_slip(db, user, slip_id)
    line = _line_on_slip(slip, line_id)
    if line.closed_at is not None:
        raise ConsumableError(409, "This line is already closed")
    if slip.supervisor_confirmed_at is not None:
        raise ConsumableError(409, "This slip is already signed by the supervisor")
    used = round_qty(payload.qty_used)
    returned = round_qty(payload.qty_returned)
    carried = round_qty(payload.qty_carried)
    already = round_qty(line.qty_returned)
    extra = round_qty(returned - already)
    if extra < -QTY_EPS:
        raise ConsumableError(422, "Returned quantity is less than material already sent back on a MIN")
    leak = leakage_qty(line.qty_issued, used, returned, carried)
    if leak < -QTY_EPS:
        raise ConsumableError(422, "Used, returned, and left at the machine add up to more than was issued")
    if extra > QTY_EPS:
        item = _lock_item(db, line.item_id)
        _add_move(
            db,
            item,
            kind="return",
            qty_delta=extra,
            moved_on=today_local(),
            actor=user,
            line_id=line.id,
            note="Return at close-out",
        )
        db.add(
            ConsumableReturn(
                line_id=line.id,
                qty=extra,
                note="Return at close-out",
                returned_by_id=user.id,
                returned_by_name=user.name,
                returned_on=today_local(),
            )
        )
    line.qty_used = used
    line.qty_returned = returned
    line.qty_carried = carried
    line.closed_at = datetime.now(ZoneInfo("UTC"))
    line.closed_by_id = user.id
    line.production_qty = None if payload.production_qty is None else round_qty(payload.production_qty)
    item_row = line.item or db.get(ConsumableItem, line.item_id)
    if item_row is not None and line.production_qty is not None:
        line.expected_qty = expected_usage(item_row.standard_qty, item_row.standard_per, line.production_qty)
        line.variance_pct = variance_pct(used, line.expected_qty)
    else:
        line.expected_qty = None
        line.variance_pct = None
    note = _optional(payload.leakage_note)
    if user.role == UserRole.operator:
        note = None
    if leak > QTY_EPS:
        line.leakage_note = note
    else:
        line.leakage_note = note
    _commit(db, "Could not close this line")
    loaded = _load_slip(db, slip.id)
    if loaded is None:
        raise ConsumableError(500, "Close-out was saved but the slip could not be reloaded")
    return loaded


def return_core(db: Session, user: User, slip_id: uuid.UUID, line_id: uuid.UUID) -> ConsumableSlip:
    _can_touch_line(user)
    slip = require_slip(db, user, slip_id)
    line = _line_on_slip(slip, line_id)
    if not line.core_due:
        raise ConsumableError(422, "This item does not track an empty core")
    if line.core_returned:
        raise ConsumableError(409, "Empty core is already marked returned")
    item = _lock_item(db, line.item_id)
    line.core_returned = True
    line.core_returned_at = datetime.now(ZoneInfo("UTC"))
    line.core_returned_by_id = user.id
    item.cores_outstanding = max(0, item.cores_outstanding - 1)
    _commit(db, "Could not record the empty core")
    loaded = _load_slip(db, slip.id)
    if loaded is None:
        raise ConsumableError(500, "Core return was saved but the slip could not be reloaded")
    return loaded


def confirm_slip(db: Session, user: User, slip_id: uuid.UUID, payload: ConfirmSlipIn) -> ConsumableSlip:
    if user.role not in (UserRole.supervisor, UserRole.management, UserRole.admin):
        raise ConsumableError(403, "Supervisor confirmation is required")
    slip = require_slip(db, user, slip_id)
    if slip.supervisor_confirmed_at is not None:
        raise ConsumableError(409, "Supervisor has already signed this slip")
    notes = {row.line_id: _clean(row.leakage_note) for row in payload.line_notes}
    for line in slip.lines:
        if line.id in notes and notes[line.id]:
            line.leakage_note = notes[line.id]
    for line in slip.lines:
        if line.closed_at is None:
            raise ConsumableError(422, "Close every line before the supervisor signs")
        leak = leakage_qty(line.qty_issued, line.qty_used or 0, line.qty_returned, line.qty_carried or 0)
        if leak > QTY_EPS and not _clean(line.leakage_note):
            raise ConsumableError(422, f"{line.item_name} has leakage and needs a supervisor note")
    slip.supervisor_confirmed_at = datetime.now(ZoneInfo("UTC"))
    slip.supervisor_confirmed_by_id = user.id
    slip.supervisor_confirmed_name = user.name
    slip.supervisor_note = _optional(payload.note)
    _commit(db, "Could not confirm this slip")
    loaded = _load_slip(db, slip.id)
    if loaded is None:
        raise ConsumableError(500, "Confirmation was saved but the slip could not be reloaded")
    return loaded


def _line_leak(line: ConsumableSlipLine) -> float | None:
    if line.closed_at is None or line.qty_used is None or line.qty_carried is None:
        return None
    return leakage_qty(line.qty_issued, line.qty_used, line.qty_returned, line.qty_carried)


def slip_public(slip: ConsumableSlip, *, now: datetime | None = None) -> SlipPublic:
    moment = now or now_local()
    lines: list[SlipLinePublic] = []
    leakage_total = 0.0
    leakage_value = 0.0
    any_open = False
    has_leakage = False
    for line in slip.lines:
        leak = _line_leak(line)
        closed = line.closed_at is not None
        if not closed:
            any_open = True
        if leak is not None and leak > QTY_EPS:
            has_leakage = True
            leakage_total += leak
            leakage_value += leak * line.rate
        item = line.item
        lines.append(
            SlipLinePublic(
                id=line.id,
                line_no=line.line_no,
                item_id=line.item_id,
                item_name=line.item_name,
                unit=line.unit,
                rate=line.rate,
                qty_issued=line.qty_issued,
                qty_used=line.qty_used,
                qty_returned=line.qty_returned,
                qty_carried=line.qty_carried,
                leakage_qty=leak,
                leakage_value=None if leak is None else round_money(leak * line.rate),
                balance_status=balance_status(closed=closed, returned=line.qty_returned, leakage=leak),
                leakage_note=line.leakage_note,
                production_qty=line.production_qty,
                expected_qty=line.expected_qty,
                variance_pct=line.variance_pct,
                standard_qty=None if item is None else item.standard_qty,
                standard_per=None if item is None else item.standard_per,
                standard_basis=None if item is None else item.standard_basis,
                core_due=line.core_due,
                core_returned=line.core_returned,
                closed_at=line.closed_at,
                returns=[
                    ReturnPublic(
                        id=row.id,
                        qty=row.qty,
                        note=row.note,
                        returned_by_name=row.returned_by_name,
                        returned_on=row.returned_on,
                    )
                    for row in line.returns
                ],
            )
        )
    status = "open" if any_open or not lines else "closed"
    stale = status == "open" and shift_has_aged(slip.slip_date, slip.shift, moment)
    return SlipPublic(
        id=slip.id,
        financial_year=slip.financial_year,
        slip_no=slip.slip_no,
        slip_no_label=slip_no_label(slip.slip_no),
        slip_date=slip.slip_date,
        shift=slip.shift,
        department=slip.department,
        machine_id=slip.machine_id,
        machine_name=slip.machine_name,
        issued_by_id=slip.issued_by_id,
        issued_by_name=slip.issued_by_name,
        received_by_id=slip.received_by_id,
        received_by_name=slip.received_by_name,
        hod_name=slip.hod_name,
        remark=slip.remark,
        supervisor_confirmed_at=slip.supervisor_confirmed_at,
        supervisor_confirmed_name=slip.supervisor_confirmed_name,
        supervisor_note=slip.supervisor_note,
        status=status,
        stale=stale,
        has_leakage=has_leakage,
        needs_sign=status == "closed" and slip.supervisor_confirmed_at is None,
        leakage_qty=round_qty(leakage_total),
        leakage_value=round_money(leakage_value),
        lines=lines,
        created_at=slip.created_at,
    )


@dataclass
class _Acc:
    qty: float = 0.0
    value: float = 0.0
    used: float = 0.0
    expected: float = 0.0

    def add(self, line: ConsumableSlipLine) -> None:
        leak = _line_leak(line)
        if leak is not None and leak > QTY_EPS:
            self.qty += leak
            self.value += leak * line.rate
        if line.expected_qty is not None and line.qty_used is not None:
            self.used += line.qty_used
            self.expected += line.expected_qty

    def bucket(self, key: str, label: str) -> LeakageBucket:
        return LeakageBucket(
            key=key,
            label=label,
            qty=round_qty(self.qty),
            value_inr=round_money(self.value),
            variance_pct=variance_pct(self.used, self.expected if self.expected > QTY_EPS else None),
        )


def leakage_report(db: Session, month: str, *, now: datetime | None = None) -> LeakageReport:
    start, nxt, _days = month_bounds(month)
    moment = now or now_local()
    fy_start, fy_end = financial_year_bounds(start)
    rows = (
        db.query(ConsumableSlipLine)
        .join(ConsumableSlip)
        .options(selectinload(ConsumableSlipLine.slip))
        .filter(ConsumableSlip.slip_date >= fy_start, ConsumableSlip.slip_date <= fy_end)
        .all()
    )
    by_item: dict[str, _Acc] = {}
    by_machine: dict[str, _Acc] = {}
    by_operator: dict[str, _Acc] = {}
    by_month: dict[str, _Acc] = {}
    labels_item: dict[str, str] = {}
    labels_machine: dict[str, str] = {}
    labels_operator: dict[str, str] = {}
    month_acc = _Acc()
    for line in rows:
        slip = line.slip
        key_month = slip.slip_date.strftime("%Y-%m")
        by_month.setdefault(key_month, _Acc()).add(line)
        if not (start <= slip.slip_date < nxt):
            continue
        month_acc.add(line)
        by_item.setdefault(str(line.item_id), _Acc()).add(line)
        labels_item[str(line.item_id)] = line.item_name
        by_machine.setdefault(str(slip.machine_id), _Acc()).add(line)
        labels_machine[str(slip.machine_id)] = slip.machine_name
        op_key = str(slip.received_by_id or slip.received_by_name)
        by_operator.setdefault(op_key, _Acc()).add(line)
        labels_operator[op_key] = slip.received_by_name

    def buckets(accs: dict[str, _Acc], labels: dict[str, str]) -> list[LeakageBucket]:
        built = [acc.bucket(key, labels.get(key, key)) for key, acc in accs.items()]
        built.sort(key=lambda row: (-row.value_inr, row.label))
        return built

    months: list[MonthBucket] = []
    cursor = fy_start
    while cursor <= fy_end:
        key = cursor.strftime("%Y-%m")
        acc = by_month.get(key, _Acc())
        months.append(MonthBucket(month=key, qty=round_qty(acc.qty), value_inr=round_money(acc.value)))
        if cursor.month == 12:
            cursor = date(cursor.year + 1, 1, 1)
        else:
            cursor = date(cursor.year, cursor.month + 1, 1)

    item_buckets = buckets(by_item, labels_item)
    stale = [
        row
        for row in (
            slip_public(slip, now=moment)
            for slip in db.query(ConsumableSlip)
            .options(
                selectinload(ConsumableSlip.lines).selectinload(ConsumableSlipLine.returns),
                selectinload(ConsumableSlip.lines).selectinload(ConsumableSlipLine.item),
            )
            .order_by(ConsumableSlip.slip_date, ConsumableSlip.slip_no)
            .all()
        )
        if row.stale
    ]
    return LeakageReport(
        month=month,
        total_qty=round_qty(month_acc.qty),
        total_value_inr=round_money(month_acc.value),
        by_item=item_buckets,
        by_machine=buckets(by_machine, labels_machine),
        by_operator=buckets(by_operator, labels_operator),
        by_month=months,
        top_items=item_buckets[:10],
        stale_slips=[
            StaleSlipRow(
                id=row.id,
                slip_no_label=row.slip_no_label,
                financial_year=row.financial_year,
                slip_date=row.slip_date,
                shift=row.shift,
                department=row.department,
                machine_name=row.machine_name,
                received_by_name=row.received_by_name,
                issued_by_name=row.issued_by_name,
            )
            for row in stale
        ],
    )


@dataclass
class _DayFold:
    inward: float = 0.0
    consumption: float = 0.0


@dataclass
class _SheetFold:
    opening: float = 0.0
    days: dict[int, _DayFold] = field(default_factory=dict)

    def day(self, number: int) -> _DayFold:
        return self.days.setdefault(number, _DayFold())


def fold_daily(
    *,
    moves: list[tuple[str, float, date]],
    start: date,
    next_month: date,
    days_in_month: int,
) -> tuple[float, list[tuple[float, float]], float, float]:
    """Return opening, per-day (inward, consumption), month inward, month consumption.

    Opening-kind moves dated before the next month stay in Op. Stock, matching
    the sheet column, and are not repeated as a day's inward. Returns reduce
    that day's consumption (the number can be negative) so
    opening + inward − consumption equals the book stock implied by these moves.
    """
    opening = 0.0
    fold = _SheetFold()
    for kind, delta, moved_on in moves:
        delta = round_qty(delta)
        if kind == "opening":
            if moved_on < next_month:
                opening += delta
            continue
        if moved_on < start:
            opening += delta
            continue
        if moved_on >= next_month:
            continue
        slot = fold.day(moved_on.day)
        if kind == "inward":
            slot.inward += delta
        elif kind == "count":
            if delta >= 0:
                slot.inward += delta
            else:
                slot.consumption += -delta
        else:
            # issue (negative delta) and return (positive delta)
            slot.consumption += -delta
    days = []
    month_in = 0.0
    month_out = 0.0
    for number in range(1, days_in_month + 1):
        slot = fold.days.get(number, _DayFold())
        inward = round_qty(slot.inward)
        consumption = round_qty(slot.consumption)
        days.append((inward, consumption))
        month_in += inward
        month_out += consumption
    return round_qty(opening), days, round_qty(month_in), round_qty(month_out)


def daily_sheet(db: Session, month: str) -> DailySheet:
    start, nxt, days_in_month = month_bounds(month)
    items = db.query(ConsumableItem).order_by(ConsumableItem.item_group, ConsumableItem.name).all()
    moves = db.query(ConsumableMove).all()
    by_item: dict[uuid.UUID, list[tuple[str, float, date]]] = {}
    for move in moves:
        by_item.setdefault(move.item_id, []).append((move.kind, move.qty_delta, move.moved_on))
    rows: list[DailyItemRow] = []
    for item in items:
        opening, day_pairs, month_in, month_out = fold_daily(
            moves=by_item.get(item.id, []),
            start=start,
            next_month=nxt,
            days_in_month=days_in_month,
        )
        closing = round_qty(opening + month_in - month_out)
        rows.append(
            DailyItemRow(
                item_id=item.id,
                item_name=item.name,
                item_group=item.item_group,
                party_name=item.party_name,
                party_address=item.party_address,
                contact_no=item.contact_no,
                lead_time_days=item.lead_time_days,
                min_stock=item.min_stock,
                max_stock=item.max_stock,
                rate=item.rate,
                opening_stock=opening,
                unit=item.unit,
                days=[DailyDay(day=index + 1, inward=pair[0], consumption=pair[1]) for index, pair in enumerate(day_pairs)],
                month_inward=month_in,
                month_consumption=month_out,
                closing_stock=closing,
            )
        )
    return DailySheet(month=month, days_in_month=days_in_month, rows=rows)


def count_public(row: ConsumableCount) -> StockCountPublic:
    return StockCountPublic.model_validate(row)
