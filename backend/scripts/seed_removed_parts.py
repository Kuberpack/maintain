"""Idempotent demo rows for parts that came off machines.

A few realistic removals over the last two weeks: one still pending (old
enough to highlight), one in the maintenance store, and one of each
disposition. The refurbished blade is added to an existing "Used Refurbish"
spare when the plant has one, otherwise to "Thin Blade Used Refurbish".

Re-running skips a row whose note already contains [[demo-removed:<key>]],
so stock is not credited twice.

    python -m scripts.seed_removed_parts

Inside Docker:

    docker compose exec backend python -m scripts.seed_removed_parts
"""

from __future__ import annotations

import sys
from datetime import date, datetime, timedelta

from sqlalchemy import func
from zoneinfo import ZoneInfo

from app.config import get_settings
from app.core.time import today_local
from app.database import SessionLocal
from app.models import Machine, PartReplacement, RemovedPartStatus, SparePart, User, UserRole
from app.schemas.removed_parts import RemovedPartCapture, RemovedPartDisposition
from app.services.removed_parts import open_removed_part, update_disposition

TAG_PREFIX = "demo-removed"
REFURB_NAME = "Thin Blade Used Refurbish"

# hints are matched against machine names already in the plant. The first
# hit wins; if none of the names exist, the row lands on the first real machine.
SPECS: list[dict] = [
    {
        "key": "corrugator-thin-blade",
        "machines": ["Corrugation (A/B)", "Corrugation"],
        "part_name": "Thin blade",
        "days_ago": 13,
        "condition": "worn",
        "quantity": 1,
        "notes": "Slitter thin blade worn. Board edge on the A flute is fuzzy.",
        "initial": "pending_decision",
        "later": None,
    },
    {
        "key": "lead-edge-anilox",
        "machines": ["Lead Edge Printing", "Leefee Printing"],
        "part_name": "Anilox roller",
        "days_ago": 11,
        "condition": "damaged",
        "quantity": 1,
        "notes": "Score line on the roller, print streak on the liner.",
        "initial": "in_maintenance_store",
        "location": "Maintenance store, awaiting vendor",
        "later": {
            "days_ago": 10,
            "status": "sent_for_repair",
            "vendor": "Gupta Anilox, Murthal",
            "notes": "Sent for re-engraving.",
        },
    },
    {
        "key": "rotary-timing-belt",
        "machines": ["Rotary", "NC Cutter"],
        "part_name": "Timing belt",
        "days_ago": 9,
        "condition": "broken",
        "quantity": 1,
        "notes": "Belt snapped on the rotary. Teeth stripped.",
        "initial": "pending_decision",
        "later": {
            "days_ago": 8,
            "status": "scrapped",
            "scrap_qty": 1.8,
            "scrap_unit": "kg",
            "scrap_buyer": "Sonipat Scrap Co.",
            "notes": "Weighed at the gate.",
        },
    },
    {
        "key": "stitch-blade-refurb",
        "machines": ["Manual Stitching Machine (6 nos)", "Auto Stitching Machine", "Semi Auto Stitching Machine"],
        "part_name": "Thin blade",
        "days_ago": 8,
        "condition": "worn",
        "quantity": 1,
        "notes": "Stitching blade still has life after grinding.",
        "initial": "in_maintenance_store",
        "location": "Maintenance store, grinding bench",
        "later": {
            "days_ago": 7,
            "status": "returned_to_stock",
            "refurb": True,
            "notes": "Ground and put back as used refurbish.",
        },
    },
    {
        "key": "die-bearing",
        "machines": ["Flat Bed Die", "Die Punching"],
        "part_name": "6204 bearing",
        "days_ago": 5,
        "condition": "reusable",
        "quantity": 1,
        "notes": "Came off during the die change. Still turns smoothly.",
        "initial": "in_maintenance_store",
        "location": "Maintenance store, rack B",
        "later": None,
    },
    {
        "key": "nc-knife",
        "machines": ["NC Cutter", "Corrugation (B/C)"],
        "part_name": "Cut-off knife",
        "days_ago": 4,
        "condition": "damaged",
        "quantity": 1,
        "notes": "Chipped knife. Not worth grinding.",
        "initial": "in_maintenance_store",
        "location": "Maintenance store, hold for sale",
        "later": {
            "days_ago": 3,
            "status": "sold",
            "sale_buyer": "Ravi Engineering, Kundli",
            "sale_amount": 2200,
            "notes": "Sold as a used knife.",
        },
    },
    {
        "key": "compressor-seal",
        "machines": ["Compressor (Hytech Pneumatics 30HP)", "Compressor"],
        "part_name": "Shaft seal",
        "days_ago": 2,
        "condition": "worn",
        "quantity": 1,
        "notes": "Oil weep on the 30HP compressor. Seal still under warranty.",
        "initial": "pending_decision",
        "later": {
            "days_ago": 1,
            "status": "returned_to_vendor",
            "vendor": "Hytech Pneumatics",
            "warranty_note": "Warranty claim HP-30-1042",
            "notes": "Handed to the service engineer.",
        },
    },
]


def marker(prefix: str, key: str) -> str:
    return f"[[{prefix}:{key}]]"


def _moment(day: date, hour: int) -> datetime:
    tz = ZoneInfo(get_settings().local_timezone)
    return datetime(day.year, day.month, day.day, hour, minute=30, tzinfo=tz)


def _pick(machines: list[Machine], hints: list[str]) -> Machine | None:
    real = [machine for machine in machines if not machine.name.startswith("ZZ Test")]
    pool = real or machines
    if not pool:
        return None
    for hint in hints:
        for machine in pool:
            if machine.name.lower() == hint.lower():
                return machine
    for hint in hints:
        for machine in pool:
            if hint.lower() in machine.name.lower():
                return machine
    return pool[0]


def _actor(db, machine: Machine) -> User | None:
    if machine.supervisor_id is not None:
        user = db.get(User, machine.supervisor_id)
        if user is not None and user.role in (UserRole.supervisor, UserRole.admin):
            return user
    return (
        db.query(User)
        .filter(User.role.in_([UserRole.supervisor, UserRole.admin]))
        .order_by(User.name)
        .first()
    )


def find_refurb_spare(db) -> SparePart | None:
    exact = (
        db.query(SparePart)
        .filter(func.lower(SparePart.name) == REFURB_NAME.lower())
        .order_by(SparePart.name)
        .first()
    )
    if exact is not None:
        return exact
    return (
        db.query(SparePart)
        .filter(SparePart.name.ilike("%used refurbish%"))
        .order_by(SparePart.name)
        .first()
    )


def ensure_refurb_spare(db) -> SparePart:
    found = find_refurb_spare(db)
    if found is not None:
        return found
    spare = SparePart(
        name=REFURB_NAME,
        item_group="Blade",
        category="Refurbish",
        qty_on_hand=0,
        unit="pcs",
    )
    db.add(spare)
    db.flush()
    return spare


def seed_removed_parts(
    db,
    *,
    machines: list[Machine] | None = None,
    refurb_spare: SparePart | None = None,
    lookup_refurb: bool = True,
    tag_prefix: str = TAG_PREFIX,
    today: date | None = None,
) -> dict:
    """Insert the demo rows. Caller may pass machines and a spare so a test does not touch plant stock."""
    today = today or today_local()
    if machines is None:
        machines = db.query(Machine).order_by(Machine.name).all()
    if not machines:
        return {"created": 0, "skipped": 0, "refurb_spare": None, "error": "No machines in the database"}

    actor_fallback = (
        db.query(User).filter(User.role.in_([UserRole.supervisor, UserRole.admin])).order_by(User.name).first()
    )
    if actor_fallback is None:
        return {"created": 0, "skipped": 0, "refurb_spare": None, "error": "No supervisor or admin to attribute the rows"}

    created = 0
    skipped = 0
    refurb_name: str | None = None
    for spec in SPECS:
        token = marker(tag_prefix, spec["key"])
        existing = db.query(PartReplacement.id).filter(PartReplacement.notes.contains(token)).first()
        if existing is not None:
            skipped += 1
            print(f"skip  {spec['key']}")
            continue
        machine = _pick(machines, spec["machines"])
        if machine is None:
            return {"created": created, "skipped": skipped, "refurb_spare": refurb_name, "error": "No machine to attach to"}
        user = _actor(db, machine) or actor_fallback
        removed_on = today - timedelta(days=spec["days_ago"])
        replacement = PartReplacement(
            machine_id=machine.id,
            part_name=spec["part_name"],
            replaced_at=removed_on,
            replaced_by=user.id,
            notes=f"{spec['notes']}\n{token}",
        )
        db.add(replacement)
        db.flush()
        capture = RemovedPartCapture(
            part_name=spec["part_name"],
            condition=spec["condition"],
            status=spec["initial"],
            quantity=spec["quantity"],
            location=spec.get("location"),
            notes=spec["notes"],
        )
        try:
            removed = open_removed_part(db, replacement, user, capture, at=_moment(removed_on, 9))
            later = spec.get("later")
            if later is not None:
                decided_on = today - timedelta(days=later["days_ago"])
                payload = _later_payload(
                    db,
                    later,
                    removed.quantity,
                    refurb_spare,
                    lookup_refurb,
                    on=decided_on,
                )
                if payload is not None:
                    if later["status"] == "returned_to_stock" and payload.spare_part_id is not None:
                        spare = db.get(SparePart, payload.spare_part_id)
                        refurb_name = spare.name if spare is not None else refurb_name
                    update_disposition(db, removed, user, payload, at=_moment(decided_on, 15))
            db.commit()
        except Exception:
            db.rollback()
            raise
        created += 1
        print(f"add   {spec['key']} on {machine.name} ({removed_on.isoformat()})")
    return {"created": created, "skipped": skipped, "refurb_spare": refurb_name, "error": None}


def _later_payload(
    db,
    later: dict,
    quantity: int,
    refurb_spare: SparePart | None,
    lookup_refurb: bool,
    *,
    on: date,
) -> RemovedPartDisposition | None:
    status = RemovedPartStatus(later["status"])
    if status == RemovedPartStatus.returned_to_stock:
        spare = refurb_spare
        if spare is None and lookup_refurb:
            spare = ensure_refurb_spare(db)
        if spare is None:
            return None
        return RemovedPartDisposition(
            status=status,
            spare_part_id=spare.id,
            quantity=quantity,
            notes=later.get("notes"),
        )
    if status == RemovedPartStatus.sent_for_repair:
        return RemovedPartDisposition(
            status=status,
            vendor=later["vendor"],
            sent_on=on,
            notes=later.get("notes"),
        )
    if status == RemovedPartStatus.scrapped:
        return RemovedPartDisposition(
            status=status,
            scrap_on=on,
            scrap_qty=later["scrap_qty"],
            scrap_unit=later["scrap_unit"],
            scrap_buyer=later["scrap_buyer"],
            notes=later.get("notes"),
        )
    if status == RemovedPartStatus.sold:
        return RemovedPartDisposition(
            status=status,
            sale_buyer=later["sale_buyer"],
            sale_amount=later["sale_amount"],
            sale_on=on,
            notes=later.get("notes"),
        )
    if status == RemovedPartStatus.returned_to_vendor:
        return RemovedPartDisposition(
            status=status,
            vendor=later["vendor"],
            sent_on=on,
            warranty_note=later.get("warranty_note"),
            notes=later.get("notes"),
        )
    raise ValueError(f"Unsupported demo disposition {status}")


def main() -> int:
    db = SessionLocal()
    try:
        result = seed_removed_parts(db, today=today_local())
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    if result.get("error") and result["created"] == 0 and result["skipped"] == 0:
        print(result["error"], file=sys.stderr)
        return 1
    spare = result.get("refurb_spare")
    spare_bit = f" Refurbished spare: {spare}." if spare else ""
    print(f"Removed-part demo: {result['created']} added, {result['skipped']} already present.{spare_bit}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
