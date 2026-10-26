"""Old parts that come off a machine, and where they end up.

Logging a replacement always opens one removed-part row. The floor records
condition and whether it is still awaiting a decision or already in the
maintenance store. A supervisor later records the disposition. Each change
appends an event; events are not edited.

Returning a part to stock adds whole pieces onto a spare row (often a
'Used Refurbish' item, separate from the new part that was fitted). That
credit is reversed if the disposition changes or the replacement is undone.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import PartReplacement, RemovedPart, RemovedPartEvent, RemovedPartStatus, SparePart, User
from app.schemas.removed_parts import RemovedPartCapture, RemovedPartDisposition
from app.services.spares import deduct_stock, restore_stock
from app.services.storage import filename_from_url

STALE_PENDING_DAYS = 7

INITIAL_STATUSES = {
    RemovedPartStatus.pending_decision,
    RemovedPartStatus.in_maintenance_store,
}


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    return text or None


def _photo(url: str | None) -> str | None:
    text = _clean(url)
    if text is None:
        return None
    if filename_from_url(text) is None:
        raise ValueError("Photo must be an uploaded image")
    return text


def _lock_spares(db: Session, ids: list[uuid.UUID]) -> dict[uuid.UUID, SparePart]:
    unique = list(dict.fromkeys(ids))
    if not unique:
        return {}
    rows = (
        db.query(SparePart)
        .filter(SparePart.id.in_(unique))
        .order_by(SparePart.id)
        .with_for_update()
        .all()
    )
    return {row.id: row for row in rows}


def check_initial(capture: RemovedPartCapture) -> None:
    if capture.status not in INITIAL_STATUSES:
        raise ValueError(
            "When logging the replacement, mark the old part as pending a decision "
            "or already in the maintenance store. Repair, scrap, sale, and stock return "
            "are recorded afterwards."
        )
    _photo(capture.photo_url)


def check_disposition(payload: RemovedPartDisposition) -> None:
    _photo(payload.photo_url)
    status = payload.status
    if status == RemovedPartStatus.sent_for_repair:
        if _clean(payload.vendor) is None:
            raise ValueError("Vendor is required when a part is sent for repair")
        if payload.sent_on is None:
            raise ValueError("The date it was sent is required")
    elif status == RemovedPartStatus.returned_to_stock:
        if payload.spare_part_id is None:
            raise ValueError("Choose the refurbished spare that this part goes back onto")
        if payload.quantity is None:
            raise ValueError("Quantity returned to stock is required")
    elif status == RemovedPartStatus.scrapped:
        if payload.scrap_on is None:
            raise ValueError("Scrap date is required")
        if payload.scrap_qty is None:
            raise ValueError("Scrap quantity or weight is required")
        if _clean(payload.scrap_unit) is None:
            raise ValueError("Scrap unit is required (kg or pcs)")
        if _clean(payload.scrap_buyer) is None:
            raise ValueError("Scrap buyer is required")
    elif status == RemovedPartStatus.sold:
        if _clean(payload.sale_buyer) is None:
            raise ValueError("Buyer is required")
        if payload.sale_amount is None:
            raise ValueError("Sale amount is required")
        if payload.sale_on is None:
            raise ValueError("Sale date is required")
    elif status == RemovedPartStatus.returned_to_vendor:
        if _clean(payload.vendor) is None:
            raise ValueError("Vendor is required")
        if payload.sent_on is None:
            raise ValueError("The date it was returned is required")


def _add_event(
    db: Session,
    row: RemovedPart,
    user: User,
    *,
    at: datetime | None,
    notes: str | None,
    photo_url: str | None,
    spare: SparePart | None,
    quantity: int | None,
) -> RemovedPartEvent:
    event = RemovedPartEvent(
        removed_part_id=row.id,
        status=row.status,
        actor_id=user.id,
        actor_name=user.name,
        at=at or datetime.now(timezone.utc),
        notes=_clean(notes),
        photo_url=photo_url,
        location=row.location,
        vendor=row.vendor,
        sent_on=row.sent_on,
        spare_part_id=spare.id if spare is not None else None,
        spare_part_name=spare.name if spare is not None else None,
        quantity=quantity,
        scrap_on=row.scrap_on,
        scrap_qty=row.scrap_qty,
        scrap_unit=row.scrap_unit,
        scrap_buyer=row.scrap_buyer,
        sale_buyer=row.sale_buyer,
        sale_amount=row.sale_amount,
        sale_on=row.sale_on,
        warranty_note=row.warranty_note,
    )
    db.add(event)
    return event


def open_removed_part(
    db: Session,
    replacement: PartReplacement,
    user: User,
    capture: RemovedPartCapture | None,
    *,
    at: datetime | None = None,
) -> RemovedPart:
    """Open the trail for a replacement that was just inserted (flushed, not committed)."""
    incoming = capture or RemovedPartCapture()
    check_initial(incoming)
    if replacement.id is None:
        db.flush()
    name = _clean(incoming.part_name) or replacement.part_name.strip()
    notes = _clean(incoming.notes) or _clean(replacement.notes)
    row = RemovedPart(
        part_replacement_id=replacement.id,
        machine_id=replacement.machine_id,
        part_name=name,
        condition=incoming.condition,
        status=incoming.status,
        quantity=incoming.quantity,
        location=_clean(incoming.location),
        notes=notes,
        stock_credited=False,
        created_by=user.id,
    )
    db.add(row)
    db.flush()
    _add_event(
        db,
        row,
        user,
        at=at,
        notes=notes,
        photo_url=_photo(incoming.photo_url),
        spare=None,
        quantity=row.quantity,
    )
    return row


def _sync_stock(
    db: Session, row: RemovedPart, status: RemovedPartStatus, spare_id: uuid.UUID | None, qty: int | None
) -> SparePart | None:
    needs_credit = status == RemovedPartStatus.returned_to_stock
    same = (
        needs_credit
        and row.stock_credited
        and row.credited_spare_part_id == spare_id
        and row.credited_qty == qty
    )
    if same and spare_id is not None:
        return db.get(SparePart, spare_id)

    ids: list[uuid.UUID] = []
    if row.stock_credited and row.credited_spare_part_id is not None:
        ids.append(row.credited_spare_part_id)
    if needs_credit and spare_id is not None:
        ids.append(spare_id)
    locked = _lock_spares(db, ids)

    if row.stock_credited and row.credited_spare_part_id is not None and row.credited_qty:
        previous = locked.get(row.credited_spare_part_id)
        if previous is None:
            raise LookupError("The refurbished spare this part was added to is missing")
        deduct_stock(previous, row.credited_qty)
        row.stock_credited = False
        row.credited_spare_part_id = None
        row.credited_qty = None

    if not needs_credit:
        return None
    if spare_id is None or qty is None:
        raise ValueError("Choose the refurbished spare and the quantity to add back")
    spare = locked.get(spare_id)
    if spare is None:
        raise LookupError("Spare part not found")
    restore_stock(spare, qty)
    row.stock_credited = True
    row.credited_spare_part_id = spare.id
    row.credited_qty = qty
    return spare


def _apply_details(row: RemovedPart, payload: RemovedPartDisposition) -> None:
    row.status = payload.status
    if payload.condition is not None:
        row.condition = payload.condition
    row.location = _clean(payload.location)
    if _clean(payload.notes) is not None:
        row.notes = _clean(payload.notes)
    row.vendor = None
    row.sent_on = None
    row.scrap_on = None
    row.scrap_qty = None
    row.scrap_unit = None
    row.scrap_buyer = None
    row.sale_buyer = None
    row.sale_amount = None
    row.sale_on = None
    row.warranty_note = None
    status = payload.status
    if status in (RemovedPartStatus.sent_for_repair, RemovedPartStatus.returned_to_vendor):
        row.vendor = _clean(payload.vendor)
        row.sent_on = payload.sent_on
        if status == RemovedPartStatus.returned_to_vendor:
            row.warranty_note = _clean(payload.warranty_note)
    elif status == RemovedPartStatus.scrapped:
        row.scrap_on = payload.scrap_on
        row.scrap_qty = payload.scrap_qty
        row.scrap_unit = _clean(payload.scrap_unit)
        row.scrap_buyer = _clean(payload.scrap_buyer)
    elif status == RemovedPartStatus.sold:
        row.sale_buyer = _clean(payload.sale_buyer)
        row.sale_amount = payload.sale_amount
        row.sale_on = payload.sale_on


def update_disposition(
    db: Session,
    row: RemovedPart,
    user: User,
    payload: RemovedPartDisposition,
    *,
    at: datetime | None = None,
) -> RemovedPart:
    if payload.status == RemovedPartStatus.returned_to_stock:
        # A note or photo on a part already back in stock must not credit it twice.
        spare_id = payload.spare_part_id or row.credited_spare_part_id
        qty = payload.quantity
        if qty is None:
            qty = row.credited_qty or row.quantity
        payload = payload.model_copy(update={"spare_part_id": spare_id, "quantity": qty})
    check_disposition(payload)
    spare = _sync_stock(db, row, payload.status, payload.spare_part_id, payload.quantity)
    _apply_details(row, payload)
    qty = row.credited_qty if payload.status == RemovedPartStatus.returned_to_stock else row.quantity
    _add_event(
        db,
        row,
        user,
        at=at,
        notes=_clean(payload.notes),
        photo_url=_photo(payload.photo_url),
        spare=spare,
        quantity=qty,
    )
    return row


def release_replacement_stock(db: Session, replacement: PartReplacement) -> None:
    """Put fitted stock back, and take refurbished stock back out, before the log is deleted."""
    removed = (
        db.query(RemovedPart).filter(RemovedPart.part_replacement_id == replacement.id).one_or_none()
    )
    credit_id = None
    credit_qty = None
    if (
        removed is not None
        and removed.stock_credited
        and removed.credited_spare_part_id is not None
        and removed.credited_qty
    ):
        credit_id = removed.credited_spare_part_id
        credit_qty = removed.credited_qty
    fitted_id = replacement.spare_part_id if replacement.quantity_used else None
    ids = [value for value in (credit_id, fitted_id) if value is not None]
    locked = _lock_spares(db, ids)
    if credit_id is not None and credit_qty is not None:
        spare = locked.get(credit_id)
        if spare is None:
            raise LookupError(
                "The refurbished spare this part was added to is missing, so the replacement cannot be undone"
            )
        deduct_stock(spare, credit_qty)
    if fitted_id is not None and replacement.quantity_used:
        spare = locked.get(fitted_id)
        if spare is not None:
            restore_stock(spare, replacement.quantity_used)
