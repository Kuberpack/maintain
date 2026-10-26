import unittest
import uuid
from datetime import date
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.core.deps import require_roles
from app.database import SessionLocal, engine
from app.models import Machine, PartReplacement, SparePart, User, UserRole
from app.routers.part_replacements import create_part_replacement, delete_part_replacement
from app.schemas.part_replacements import PartReplacementCreate
from app.schemas.spare_parts import SparePartCreate
from app.services.spares import OutOfStock, deduct_stock, restore_stock
from app.services.spares_import import ParsedSpare, apply_import, obvious_machine_name, parse_qty, parse_workbook

XLSX = Path(__file__).resolve().parents[1] / "data" / "maintenance_spares_24oct2026.xlsx"

EXPECTED = {
    "Bearing": (105, 104),
    "Rewinding": (5, 5),
    "Fire Line": (10, 10),
    "Timing Belt": (82, 81),
    "Auto Die": (8, 8),
    "Manul Die": (7, 7),
    "Flute Laminetar": (12, 12),
    "Manual Stitching": (45, 44),
}


class ParseSparesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.parsed = parse_workbook(XLSX)

    def test_counts_per_sheet(self) -> None:
        by_category = {sheet.category: sheet for sheet in self.parsed.sheets}
        self.assertEqual(set(by_category), set(EXPECTED))
        for category, (rows, items) in EXPECTED.items():
            sheet = by_category[category]
            self.assertEqual(sheet.sheet_rows, rows, category)
            self.assertEqual(sheet.items, items, category)
        self.assertEqual(len(self.parsed.items), 271)
        self.assertEqual(self.parsed.sheet_rows, 274)
        self.assertEqual(self.parsed.duplicate_rows_merged, 3)
        self.assertEqual(self.parsed.blank_rows_skipped, 1)

    def test_duplicate_names_are_summed(self) -> None:
        bearing = next(item for item in self.parsed.items if item.category == "Bearing" and item.name == "6002- SKF")
        belt = next(
            item
            for item in self.parsed.items
            if item.category == "Timing Belt" and item.name == "Timing Belt - Size- 330H T-66"
        )
        spring = next(
            item
            for item in self.parsed.items
            if item.category == "Manual Stitching" and item.name == "Locking Spring"
        )
        self.assertEqual(bearing.qty_on_hand, 11)
        self.assertEqual(belt.qty_on_hand, 9)
        self.assertEqual(spring.qty_on_hand, 7)

    def test_text_quantities_keep_the_number_and_unit(self) -> None:
        patta = next(item for item in self.parsed.items if item.name == "Boardline - Lailon Patta")
        stacker = next(item for item in self.parsed.items if item.name == "Printing Stacker Belt- 70 MM")
        matrix = next(item for item in self.parsed.items if item.name == "Creasing Matrix -C2")
        self.assertEqual((patta.qty_on_hand, patta.unit), (12, "Mtr"))
        self.assertEqual((stacker.qty_on_hand, stacker.unit), (50, "Mtr"))
        self.assertEqual((matrix.qty_on_hand, matrix.unit), (2, "pkt"))

    def test_blank_group_and_trimmed_category(self) -> None:
        gripper = next(item for item in self.parsed.items if item.category == "Flute Laminetar" and item.name == "Gripper")
        carbon = next(item for item in self.parsed.items if item.category == "Rewinding" and item.name == "Carbon")
        self.assertEqual(gripper.item_group, "")
        self.assertEqual(carbon.item_group, "")
        self.assertTrue(all(item.category == item.category.strip() for item in self.parsed.items))
        self.assertNotIn("Bearing ", {item.category for item in self.parsed.items})

    def test_identity_is_unique(self) -> None:
        keys = [(item.category, item.name, item.item_group) for item in self.parsed.items]
        self.assertEqual(len(keys), len(set(keys)))

    def test_obvious_machine_links(self) -> None:
        self.assertEqual(obvious_machine_name("Flute Laminetar"), "Flute Laminator")
        self.assertEqual(obvious_machine_name("Manual Stitching"), "Manual Stitching Machine (6 nos)")
        self.assertIsNone(obvious_machine_name("Bearing"))
        self.assertIsNone(obvious_machine_name("Auto Die"))
        self.assertIsNone(obvious_machine_name("Manul Die"))
        self.assertIsNone(obvious_machine_name("Rewinding"))

    def test_parse_qty(self) -> None:
        self.assertEqual(parse_qty(4), (4, None))
        self.assertEqual(parse_qty(5.0), (5, None))
        self.assertEqual(parse_qty("12 Mtr"), (12, "Mtr"))
        self.assertEqual(parse_qty("2 pkt"), (2, "pkt"))
        self.assertIsNone(parse_qty("n/a"))
        self.assertIsNone(parse_qty(-1))
        self.assertIsNone(parse_qty(None))
        self.assertIsNone(parse_qty(3.999))
        self.assertIsNone(parse_qty(1.001))
        self.assertIsNone(parse_qty(1.5))
        self.assertIsNone(parse_qty("12.5 Mtr"))


class StockMathTest(unittest.TestCase):
    def test_deduct_and_restore(self) -> None:
        part = SparePart(name="Gripper Bolt", item_group="Bolt", category="Auto Die", qty_on_hand=4)
        taken = deduct_stock(part, 1)
        self.assertEqual(taken, 1)
        self.assertEqual(part.qty_on_hand, 3)
        self.assertFalse(part.low_stock)
        part.min_qty = 3
        self.assertTrue(part.low_stock)
        restore_stock(part, taken)
        self.assertEqual(part.qty_on_hand, 4)
        self.assertFalse(part.low_stock)

    def test_out_of_stock(self) -> None:
        part = SparePart(name="Sensor", item_group="Sensor", category="Auto Die", qty_on_hand=1)
        with self.assertRaises(OutOfStock):
            deduct_stock(part, 2)
        self.assertEqual(part.qty_on_hand, 1)

    def test_zero_on_hand_is_low(self) -> None:
        part = SparePart(name="Sensor", item_group="", category="Auto Die", qty_on_hand=0)
        self.assertTrue(part.low_stock)

    def test_fractional_draw_is_rejected(self) -> None:
        part = SparePart(name="1213 - NTN", item_group="Bearing", category="Bearing", qty_on_hand=5)
        with self.assertRaises(ValueError):
            deduct_stock(part, 1.001)
        self.assertEqual(part.qty_on_hand, 5)

    def test_api_rejects_fractional_quantities(self) -> None:
        machine_id = uuid.uuid4()
        with self.assertRaises(ValidationError):
            PartReplacementCreate(
                machine_id=machine_id,
                part_name="1213 - NTN",
                replaced_at=date(2026, 10, 26),
                spare_part_id=uuid.uuid4(),
                quantity_used=1.001,
            )
        with self.assertRaises(ValidationError):
            SparePartCreate(name="Bolt", category="Auto Die", qty_on_hand=3.999)
        created = PartReplacementCreate(
            machine_id=machine_id,
            part_name="1213 - NTN",
            replaced_at=date(2026, 10, 26),
            quantity_used=1,
        )
        spare = SparePartCreate(name="Bolt", category="Auto Die", qty_on_hand=4, min_qty=1)
        self.assertEqual(created.quantity_used, 1)
        self.assertEqual((spare.qty_on_hand, spare.min_qty), (4, 1))


def _as_test_rows(items: list[ParsedSpare]) -> list[ParsedSpare]:
    """Prefix the area so a test import cannot overwrite plant stock."""
    return [
        ParsedSpare(
            category=f"zztest-{item.category}",
            name=item.name,
            item_group=item.item_group,
            qty_on_hand=item.qty_on_hand,
            unit=item.unit,
        )
        for item in items
    ]


def _database_up() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except OperationalError:
        return False


@unittest.skipUnless(_database_up(), "Postgres is not running")
class ImportAndDeductTest(unittest.TestCase):
    def setUp(self) -> None:
        self.db = SessionLocal()
        self.user = User(name="Spare Tester", role=UserRole.supervisor, phone_number=f"9{uuid.uuid4().int % 10**9:09d}")
        suffix = uuid.uuid4().hex[:8]
        self.flute = Machine(name=f"ZZ Test Flute {suffix}", type="laminator", kind="production", supervisor_id=None)
        self.stitch = Machine(name=f"ZZ Test Stitch {suffix}", type="stitcher", kind="production")
        self.link_map = {
            "zztest-flute laminetar": self.flute.name,
            "zztest-manual stitching": self.stitch.name,
        }
        self.db.add(self.user)
        self.db.add(self.flute)
        self.db.add(self.stitch)
        self.db.commit()
        self.user_id = self.user.id
        self.flute_id = self.flute.id
        self.stitch_id = self.stitch.id
        self.flute.supervisor_id = self.user.id
        self.db.commit()

    def tearDown(self) -> None:
        self.db.rollback()
        machine_ids = [self.flute_id, self.stitch_id]
        self.db.query(PartReplacement).filter(PartReplacement.machine_id.in_(machine_ids)).delete(
            synchronize_session=False
        )
        self.db.query(SparePart).filter(SparePart.category.like("zztest-%")).delete(synchronize_session=False)
        self.db.query(Machine).filter(Machine.id.in_(machine_ids)).delete(synchronize_session=False)
        self.db.query(User).filter(User.id == self.user_id).delete(synchronize_session=False)
        self.db.commit()
        self.db.close()

    def _import(self, items: list[ParsedSpare]):
        with patch.dict("app.services.spares_import.OBVIOUS_MACHINE_NAMES", self.link_map, clear=False):
            return apply_import(self.db, items)

    def test_import_is_idempotent_and_links_obvious_machines(self) -> None:
        items = _as_test_rows(parse_workbook(XLSX).items)
        first = self._import(items)
        self.assertEqual(first.created, 271)
        self.assertEqual(first.updated, 0)
        self.assertEqual(first.linked["zztest-Flute Laminetar"], self.flute.name)
        self.assertEqual(first.linked["zztest-Manual Stitching"], self.stitch.name)
        self.assertNotIn("zztest-Bearing", first.linked)

        flute_part = (
            self.db.query(SparePart)
            .filter(SparePart.category == "zztest-Flute Laminetar", SparePart.name == "Gripper")
            .one()
        )
        bearing = self.db.query(SparePart).filter(SparePart.category == "zztest-Bearing").first()
        self.assertIsNotNone(bearing)
        assert bearing is not None
        self.assertEqual(flute_part.machine_id, self.flute.id)
        self.assertIsNone(bearing.machine_id)
        flute_part.min_qty = 20
        self.db.commit()

        second = self._import(items)
        self.assertEqual((second.created, second.updated, second.unchanged), (0, 0, 271))
        self.db.refresh(flute_part)
        self.assertEqual(flute_part.min_qty, 20)
        self.assertEqual(self.db.query(SparePart).filter(SparePart.category.like("zztest-%")).count(), 271)

    def test_replacement_deducts_only_when_a_spare_is_named(self) -> None:
        self._import(_as_test_rows(parse_workbook(XLSX).items))
        part = (
            self.db.query(SparePart)
            .filter(SparePart.category == "zztest-Flute Laminetar", SparePart.name == "Gear")
            .one()
        )
        before = part.qty_on_hand
        created = create_part_replacement(
            PartReplacementCreate(
                machine_id=self.flute.id,
                part_name="ignored",
                replaced_at=date(2026, 10, 26),
                spare_part_id=part.id,
                quantity_used=1,
            ),
            self.db,
            self.user,
        )
        self.db.refresh(part)
        self.assertEqual(part.qty_on_hand, before - 1)
        self.assertEqual(created.quantity_used, 1)
        self.assertEqual(created.spare_part_id, part.id)

        with self.assertRaises(HTTPException) as raised:
            create_part_replacement(
                PartReplacementCreate(
                    machine_id=self.flute.id,
                    part_name=part.name,
                    replaced_at=date(2026, 10, 26),
                    spare_part_id=part.id,
                    quantity_used=10_000,
                ),
                self.db,
                self.user,
            )
        self.assertEqual(raised.exception.status_code, 409)
        self.db.refresh(part)
        self.assertEqual(part.qty_on_hand, before - 1)

        delete_part_replacement(created.id, self.db, self.user)
        self.db.refresh(part)
        self.assertEqual(part.qty_on_hand, before)

        plain = create_part_replacement(
            PartReplacementCreate(
                machine_id=self.flute.id,
                part_name="Drive belt",
                replaced_at=date(2026, 10, 26),
            ),
            self.db,
            self.user,
        )
        self.assertIsNone(plain.spare_part_id)
        self.assertIsNone(plain.quantity_used)
        self.db.refresh(part)
        self.assertEqual(part.qty_on_hand, before)
        delete_part_replacement(plain.id, self.db, self.user)

    def test_operator_cannot_read_stock(self) -> None:
        operator = User(name="Op", role=UserRole.operator)
        gate = require_roles(UserRole.supervisor, UserRole.management, UserRole.admin)
        with self.assertRaises(HTTPException) as raised:
            gate(operator)
        self.assertEqual(raised.exception.status_code, 403)
        supervisor = User(name="Sup", role=UserRole.supervisor)
        management = User(name="Mgmt", role=UserRole.management)
        admin = User(name="Admin", role=UserRole.admin)
        self.assertEqual(gate(supervisor).role, UserRole.supervisor)
        self.assertEqual(gate(management).role, UserRole.management)
        self.assertEqual(gate(admin).role, UserRole.admin)
        write_gate = require_roles(UserRole.supervisor, UserRole.admin)
        with self.assertRaises(HTTPException) as denied:
            write_gate(management)
        self.assertEqual(denied.exception.status_code, 403)
        self.assertEqual(write_gate(admin).role, UserRole.admin)


if __name__ == "__main__":
    unittest.main()
