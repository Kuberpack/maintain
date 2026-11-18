"""Idempotent demo data for the consumables store.

Loads about 30 real item-master rows (rates and min/max from the plant sheet,
usage standards marked as placeholders) and a handful of store issue slips:
one leakage case, one balanced close-out, one MIN that is still open, one
slip left open long enough to count as older than a shift, and one closed
slip still waiting for the supervisor signature.

Running it again matches items by name and slips by a [[demo-consumable:<key>]]
tag in the remark, so stock is not deducted twice.

    python -m scripts.seed_consumables

Inside Docker:

    docker compose exec backend python -m scripts.seed_consumables
"""

from __future__ import annotations

import sys
from datetime import timedelta

from sqlalchemy.orm import Session

from app.core.time import today_local
from app.database import SessionLocal
from app.models import ConsumableItem, ConsumableMove, ConsumableSlip, Machine, User, UserRole
from app.schemas.consumables import (
    CloseLineIn,
    ConfirmSlipIn,
    ConsumableItemCreate,
    InwardCreate,
    LineNoteIn,
    ReturnCreate,
    SlipCreate,
    SlipLineIn,
)
from app.services.consumables import (
    ConsumableError,
    close_line,
    confirm_slip,
    create_item,
    create_slip,
    current_shift,
    receive_inward,
    return_material,
)

TAG = "demo-consumable"

# Usage standards are examples only. Real kg-per-1000-boxes and kg-per-ton
# figures are still to be confirmed (CONFIRM_LATER.md).
CATALOG: list[dict] = [
    {
        "name": "Strip Roll 9 mm Black",
        "item_group": "Strap Roll",
        "party_name": "Industrial Tapes & Packers",
        "party_address": "Kundli, Sonipat",
        "contact_no": "9810001101",
        "lead_time_days": 3,
        "min_stock": 20,
        "max_stock": 50,
        "rate": 760,
        "unit": "Roll",
        "qty_on_hand": 36,
        "tracks_empty_core": True,
    },
    {
        "name": "Stitching Wire 15/22 Jumbo",
        "item_group": "Stitching Wire",
        "party_name": "Taarobaar Packaging Solution",
        "party_address": "Rai, Sonipat",
        "contact_no": "9810001102",
        "lead_time_days": 2,
        "min_stock": 200,
        "max_stock": 630,
        "rate": 114,
        "unit": "Kg",
        "qty_on_hand": 410,
        "tracks_empty_core": True,
        "standard_qty": 0.35,
        "standard_per": 1000,
        "standard_basis": "boxes",
    },
    {
        "name": "Stitching Wire 14/25",
        "item_group": "Stitching Wire",
        "party_name": "Taarobaar Packaging Solution",
        "party_address": "Rai, Sonipat",
        "contact_no": "9810001102",
        "lead_time_days": 2,
        "min_stock": 150,
        "max_stock": 400,
        "rate": 111,
        "unit": "Kg",
        "qty_on_hand": 260,
        "tracks_empty_core": True,
    },
    {
        "name": "Stitching Wire 17/18",
        "item_group": "Stitching Wire",
        "party_name": "Taarobaar Packaging Solution",
        "party_address": "Rai, Sonipat",
        "contact_no": "9810001102",
        "lead_time_days": 2,
        "min_stock": 80,
        "max_stock": 250,
        "rate": 108,
        "unit": "Kg",
        "qty_on_hand": 140,
        "tracks_empty_core": True,
    },
    {
        "name": '2" Brown Tape',
        "item_group": "Tape",
        "party_name": "Industrial Tapes & Packers",
        "party_address": "Kundli, Sonipat",
        "contact_no": "9810001101",
        "lead_time_days": 2,
        "min_stock": 40,
        "max_stock": 200,
        "rate": 52,
        "unit": "Pcs",
        "qty_on_hand": 86,
        "tracks_empty_core": True,
    },
    {
        "name": '2" Transparent Tape',
        "item_group": "Tape",
        "party_name": "Industrial Tapes & Packers",
        "party_address": "Kundli, Sonipat",
        "contact_no": "9810001101",
        "lead_time_days": 2,
        "min_stock": 30,
        "max_stock": 120,
        "rate": 48,
        "unit": "Pcs",
        "qty_on_hand": 54,
        "tracks_empty_core": True,
    },
    {
        "name": '3" Brown Tape',
        "item_group": "Tape",
        "party_name": "Industrial Tapes & Packers",
        "party_address": "Kundli, Sonipat",
        "contact_no": "9810001101",
        "lead_time_days": 2,
        "min_stock": 20,
        "max_stock": 80,
        "rate": 78,
        "unit": "Pcs",
        "qty_on_hand": 32,
        "tracks_empty_core": True,
    },
    {
        "name": "BOPP Tape 48 mm",
        "item_group": "Tape",
        "party_name": "Industrial Tapes & Packers",
        "party_address": "Kundli, Sonipat",
        "contact_no": "9810001101",
        "lead_time_days": 3,
        "min_stock": 24,
        "max_stock": 100,
        "rate": 55,
        "unit": "Pcs",
        "qty_on_hand": 40,
        "tracks_empty_core": True,
    },
    {
        "name": "Maize Starch Powder",
        "item_group": "Starch & Chemicals",
        "party_name": "Dujania Polychem",
        "party_address": "Sonipat",
        "contact_no": "9810001103",
        "lead_time_days": 4,
        "min_stock": 200,
        "max_stock": 800,
        "rate": 45,
        "unit": "Kg",
        "qty_on_hand": 520,
        "standard_qty": 12,
        "standard_per": 1,
        "standard_basis": "ton of board",
    },
    {
        "name": "Borax Powder",
        "item_group": "Starch & Chemicals",
        "party_name": "Rai Chemical Store",
        "party_address": "Rai, Sonipat",
        "contact_no": "9810001104",
        "lead_time_days": 3,
        "min_stock": 25,
        "max_stock": 80,
        "rate": 100,
        "unit": "Kg",
        "qty_on_hand": 18,
    },
    {
        "name": "Caustic Soda Flakes",
        "item_group": "Starch & Chemicals",
        "party_name": "Dujania Polychem",
        "party_address": "Sonipat",
        "contact_no": "9810001103",
        "lead_time_days": 3,
        "min_stock": 50,
        "max_stock": 200,
        "rate": 59,
        "unit": "Kg",
        "qty_on_hand": 90,
    },
    {
        "name": "Adhesive Fevicol PG 003",
        "item_group": "Adhesive",
        "party_name": "JSS Polymers",
        "party_address": "Delhi",
        "contact_no": "9810001105",
        "lead_time_days": 5,
        "min_stock": 40,
        "max_stock": 150,
        "rate": 57,
        "unit": "Kg",
        "qty_on_hand": 70,
    },
    {
        "name": "Pasting Powder",
        "item_group": "Adhesive",
        "party_name": "JSS Polymers",
        "party_address": "Delhi",
        "contact_no": "9810001105",
        "lead_time_days": 4,
        "min_stock": 50,
        "max_stock": 200,
        "rate": 60,
        "unit": "Kg",
        "qty_on_hand": 110,
    },
    {
        "name": "Modified Starch",
        "item_group": "Starch & Chemicals",
        "party_name": "Dujania Polychem",
        "party_address": "Sonipat",
        "contact_no": "9810001103",
        "lead_time_days": 5,
        "min_stock": 100,
        "max_stock": 400,
        "rate": 42,
        "unit": "Kg",
        "qty_on_hand": 240,
        "standard_qty": 8,
        "standard_per": 1,
        "standard_basis": "ton of board",
    },
    {
        "name": "Stretch Film Roll",
        "item_group": "Film",
        "party_name": "Packwell Films",
        "party_address": "Kundli, Sonipat",
        "contact_no": "9810001106",
        "lead_time_days": 3,
        "min_stock": 15,
        "max_stock": 60,
        "rate": 190,
        "unit": "Roll",
        "qty_on_hand": 22,
        "tracks_empty_core": True,
    },
    {
        "name": "Dlx 1034 Brilliant Red ink",
        "item_group": "Ink",
        "party_name": "DIC India",
        "party_address": "Noida",
        "contact_no": "9810001107",
        "lead_time_days": 7,
        "min_stock": 10,
        "max_stock": 40,
        "rate": 220,
        "unit": "Kg",
        "qty_on_hand": 8,
    },
    {
        "name": "Dlx 1034 Process Blue ink",
        "item_group": "Ink",
        "party_name": "DIC India",
        "party_address": "Noida",
        "contact_no": "9810001107",
        "lead_time_days": 7,
        "min_stock": 8,
        "max_stock": 30,
        "rate": 215,
        "unit": "Kg",
        "qty_on_hand": 12,
    },
    {
        "name": "Dlx 1034 Black ink",
        "item_group": "Ink",
        "party_name": "DIC India",
        "party_address": "Noida",
        "contact_no": "9810001107",
        "lead_time_days": 7,
        "min_stock": 8,
        "max_stock": 30,
        "rate": 200,
        "unit": "Kg",
        "qty_on_hand": 16,
    },
    {
        "name": "Dlx 1034 Yellow ink",
        "item_group": "Ink",
        "party_name": "DIC India",
        "party_address": "Noida",
        "contact_no": "9810001107",
        "lead_time_days": 7,
        "min_stock": 6,
        "max_stock": 24,
        "rate": 230,
        "unit": "Kg",
        "qty_on_hand": 9,
    },
    {
        "name": "Strap Roll 12 mm Green",
        "item_group": "Strap Roll",
        "party_name": "Industrial Tapes & Packers",
        "party_address": "Kundli, Sonipat",
        "contact_no": "9810001101",
        "lead_time_days": 4,
        "min_stock": 10,
        "max_stock": 40,
        "rate": 820,
        "unit": "Roll",
        "qty_on_hand": 14,
        "tracks_empty_core": True,
    },
    {
        "name": "Strap Roll 15 mm White",
        "item_group": "Strap Roll",
        "party_name": "Industrial Tapes & Packers",
        "party_address": "Kundli, Sonipat",
        "contact_no": "9810001101",
        "lead_time_days": 4,
        "min_stock": 8,
        "max_stock": 30,
        "rate": 910,
        "unit": "Roll",
        "qty_on_hand": 11,
        "tracks_empty_core": True,
    },
    {
        "name": "Strapping Clip",
        "item_group": "Strap Roll",
        "party_name": "Industrial Tapes & Packers",
        "party_address": "Kundli, Sonipat",
        "contact_no": "9810001101",
        "lead_time_days": 5,
        "min_stock": 5,
        "max_stock": 20,
        "rate": 180,
        "unit": "Kg",
        "qty_on_hand": 7,
    },
    {
        "name": "Fevicol SH",
        "item_group": "Adhesive",
        "party_name": "Pidilite stockist, Sonipat",
        "party_address": "Sonipat",
        "contact_no": "9810001108",
        "lead_time_days": 3,
        "min_stock": 10,
        "max_stock": 40,
        "rate": 240,
        "unit": "Kg",
        "qty_on_hand": 18,
    },
    {
        "name": "Corrugation Gum Powder",
        "item_group": "Adhesive",
        "party_name": "Dujania Polychem",
        "party_address": "Sonipat",
        "contact_no": "9810001103",
        "lead_time_days": 4,
        "min_stock": 100,
        "max_stock": 400,
        "rate": 38,
        "unit": "Kg",
        "qty_on_hand": 210,
    },
    {
        "name": "Sodium Silicate Alkaline",
        "item_group": "Starch & Chemicals",
        "party_name": "Dujania Polychem",
        "party_address": "Sonipat",
        "contact_no": "9810001103",
        "lead_time_days": 4,
        "min_stock": 100,
        "max_stock": 500,
        "rate": 18,
        "unit": "Kg",
        "qty_on_hand": 260,
    },
    {
        "name": "Bundle Strap 12 mm",
        "item_group": "Strap Roll",
        "party_name": "Industrial Tapes & Packers",
        "party_address": "Kundli, Sonipat",
        "contact_no": "9810001101",
        "lead_time_days": 3,
        "min_stock": 20,
        "max_stock": 80,
        "rate": 95,
        "unit": "Kg",
        "qty_on_hand": 34,
    },
    {
        "name": "Cotton Wiping Cloth",
        "item_group": "Housekeeping",
        "party_name": "Local general store",
        "party_address": "Rai, Sonipat",
        "contact_no": "9810001109",
        "lead_time_days": 2,
        "min_stock": 10,
        "max_stock": 40,
        "rate": 80,
        "unit": "Kg",
        "qty_on_hand": 15,
    },
    {
        "name": "Hand Gloves Cotton",
        "item_group": "Housekeeping",
        "party_name": "Local general store",
        "party_address": "Rai, Sonipat",
        "contact_no": "9810001109",
        "lead_time_days": 2,
        "min_stock": 20,
        "max_stock": 100,
        "rate": 12,
        "unit": "Pair",
        "qty_on_hand": 48,
    },
    {
        "name": "Kraft Tape 48 mm",
        "item_group": "Tape",
        "party_name": "Industrial Tapes & Packers",
        "party_address": "Kundli, Sonipat",
        "contact_no": "9810001101",
        "lead_time_days": 3,
        "min_stock": 12,
        "max_stock": 48,
        "rate": 65,
        "unit": "Pcs",
        "qty_on_hand": 20,
        "tracks_empty_core": True,
    },
    {
        "name": "Ink Reducer",
        "item_group": "Ink",
        "party_name": "DIC India",
        "party_address": "Noida",
        "contact_no": "9810001107",
        "lead_time_days": 7,
        "min_stock": 5,
        "max_stock": 20,
        "rate": 90,
        "unit": "Kg",
        "qty_on_hand": 6,
    },
]


def _tag(key: str) -> str:
    return f"[[{TAG}:{key}]]"


def _pick_machine(machines: list[Machine], hints: list[str]) -> Machine | None:
    for hint in hints:
        for machine in machines:
            if hint.lower() in machine.name.lower():
                return machine
    return machines[0] if machines else None


def _issuer(db: Session, machine: Machine) -> User | None:
    """Someone allowed to issue to this machine: its supervisor, else management or admin."""
    if machine.supervisor_id is not None:
        supervisor = db.get(User, machine.supervisor_id)
        if supervisor is not None and supervisor.role in (UserRole.supervisor, UserRole.admin):
            return supervisor
    return (
        db.query(User)
        .filter(User.role.in_((UserRole.management, UserRole.admin)))
        .order_by(User.name)
        .first()
    )


def _receiver(db: Session, machine: Machine) -> User | None:
    if machine.operator_id is not None:
        operator = db.get(User, machine.operator_id)
        if operator is not None and operator.role == UserRole.operator:
            return operator
    return db.query(User).filter(User.role == UserRole.operator).order_by(User.name).first()


def _slip_exists(db: Session, key: str) -> bool:
    return db.query(ConsumableSlip.id).filter(ConsumableSlip.remark.contains(_tag(key))).first() is not None


def seed_consumables(db: Session) -> dict:
    today = today_local()
    actor = (
        db.query(User)
        .filter(User.role.in_((UserRole.management, UserRole.admin, UserRole.supervisor)))
        .order_by(User.name)
        .first()
    )
    if actor is None:
        return {"items_created": 0, "items_skipped": 0, "slips_created": 0, "slips_skipped": 0, "error": "No management, admin, or supervisor user to own the stock moves"}

    created = 0
    skipped = 0
    opening_on = today - timedelta(days=40)
    for row in CATALOG:
        if db.query(ConsumableItem.id).filter(ConsumableItem.name == row["name"]).first() is not None:
            skipped += 1
            continue
        create_item(db, ConsumableItemCreate(**row), actor, opening_on=opening_on)
        created += 1
        print(f"item  {row['name']}")

    borax = db.query(ConsumableItem).filter(ConsumableItem.name == "Borax Powder").one_or_none()
    inward_note = _tag("inward-borax")
    if borax is not None and db.query(ConsumableMove.id).filter(ConsumableMove.note.contains(inward_note)).first() is None:
        receive_inward(db, borax.id, InwardCreate(qty=5, received_on=today - timedelta(days=1), note=f"Demo receipt {inward_note}"), actor)
        print("in    Borax Powder 5 kg")

    machines = db.query(Machine).order_by(Machine.name).all()
    if not machines:
        return {
            "items_created": created,
            "items_skipped": skipped,
            "slips_created": 0,
            "slips_skipped": 0,
            "error": "No machine to attach slips to",
        }

    slips_created = 0
    slips_skipped = 0

    def issue(key: str, hints: list[str], shift: str, slip_date, item_name: str, qty: float, department: str | None = None):
        nonlocal slips_created, slips_skipped
        if _slip_exists(db, key):
            slips_skipped += 1
            print(f"skip  {key}")
            return None
        machine = _pick_machine(machines, hints)
        if machine is None:
            return None
        issuer = _issuer(db, machine)
        receiver = _receiver(db, machine)
        item = db.query(ConsumableItem).filter(ConsumableItem.name == item_name).one_or_none()
        if issuer is None or receiver is None or item is None:
            print(f"skip  {key} (need an issuer, an operator, and {item_name})")
            slips_skipped += 1
            return None
        dept = department or ("Auto Semi" if "stitch" in machine.name.lower() else (machine.group_name or machine.name))
        try:
            slip, warnings = create_slip(
                db,
                SlipCreate(
                    slip_date=slip_date,
                    shift=shift,
                    department=dept,
                    machine_id=machine.id,
                    received_by_id=receiver.id,
                    hod_name=None,
                    remark=f"Demo store issue. {_tag(key)}",
                    lines=[SlipLineIn(item_id=item.id, qty=qty)],
                ),
                issuer,
                core_policy="warn",
            )
        except ConsumableError as exc:
            print(f"fail  {key}: {exc.detail}")
            slips_skipped += 1
            return None
        slips_created += 1
        warn = f" warning: {warnings[0]}" if warnings else ""
        print(f"slip  {key} {slip.financial_year}/{slip.slip_no:02d} {machine.name}{warn}")
        return slip, issuer, receiver

    leak = issue(
        "leak-wire",
        ["Semi Auto Stitching", "Auto Stitching", "Stitch"],
        "A",
        today - timedelta(days=2),
        "Stitching Wire 15/22 Jumbo",
        28.9,
    )
    if leak is not None:
        slip, issuer, receiver = leak
        line = slip.lines[0]
        close_line(
            db,
            receiver,
            slip.id,
            line.id,
            CloseLineIn(qty_used=20, qty_returned=2, qty_carried=4, production_qty=50000),
        )
        confirm_slip(
            db,
            issuer,
            slip.id,
            ConfirmSlipIn(
                note="Signed after the shift. Leakage noted.",
                line_notes=[
                    LineNoteIn(
                        line_id=line.id,
                        leakage_note="2.9 kg short at shift end. Operator says it went to the scrap bin. Not verified.",
                    )
                ],
            ),
        )

    tape = issue(
        "balanced-tape",
        ["Auto Stitching", "Semi Auto Stitching", "Stitch"],
        "B",
        today - timedelta(days=1),
        '2" Brown Tape',
        4,
    )
    if tape is not None:
        slip, issuer, receiver = tape
        line = slip.lines[0]
        close_line(db, receiver, slip.id, line.id, CloseLineIn(qty_used=4, qty_returned=0, qty_carried=0))
        confirm_slip(db, issuer, slip.id, ConfirmSlipIn(note="Used on the shift. Nothing left over."))

    starch = issue(
        "min-starch",
        ["Corrugation (A/B)", "Corrugation", "Gluer"],
        current_shift(),
        today,
        "Maize Starch Powder",
        50,
        department="Corrugation",
    )
    if starch is not None:
        slip, _issuer_user, receiver = starch
        return_material(
            db,
            receiver,
            slip.id,
            slip.lines[0].id,
            ReturnCreate(qty=10, returned_on=today, note="MIN — bag still half full, sent back to store"),
        )

    issue(
        "stale-film",
        ["Dispatch", "Gluer", "Corrugation (B/C)", "Corrugation"],
        "A",
        today - timedelta(days=4),
        "Stretch Film Roll",
        2,
        department="Dispatch",
    )
    issue(
        "film-core-open",
        ["Dispatch", "Gluer", "Corrugation (A/B)"],
        current_shift(),
        today,
        "Stretch Film Roll",
        1,
        department="Dispatch",
    )
    waiting = issue(
        "await-sign",
        ["Auto Gluer", "Gluer", "Pasting"],
        "C",
        today - timedelta(days=1),
        "Adhesive Fevicol PG 003",
        5,
        department="Pasting",
    )
    if waiting is not None:
        slip, _issuer_user, receiver = waiting
        close_line(db, receiver, slip.id, slip.lines[0].id, CloseLineIn(qty_used=5, qty_returned=0, qty_carried=0))

    return {
        "items_created": created,
        "items_skipped": skipped,
        "slips_created": slips_created,
        "slips_skipped": slips_skipped,
        "error": None,
    }


def main() -> int:
    db = SessionLocal()
    try:
        result = seed_consumables(db)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    if result.get("error") and result["items_created"] == 0 and result["slips_created"] == 0:
        print(result["error"], file=sys.stderr)
        return 1
    if result.get("error"):
        print(result["error"])
    print(
        f"Consumables demo: {result['items_created']} items added, {result['items_skipped']} already present, "
        f"{result['slips_created']} slips added, {result['slips_skipped']} slips already present."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
