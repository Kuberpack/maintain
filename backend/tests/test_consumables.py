import unittest
import uuid
from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.exc import OperationalError, ProgrammingError

from app.core.time import today_local
from app.database import SessionLocal, engine
from app.models import (
    ConsumableItem,
    ConsumableMove,
    ConsumableSlip,
    Machine,
    User,
    UserRole,
)
from app.schemas.consumables import (
    CloseLineIn,
    ConfirmSlipIn,
    ConsumableItemCreate,
    LineNoteIn,
    ReturnCreate,
    SlipCreate,
    SlipLineIn,
    StockCountCreate,
)
from app.services.consumables import (
    ConsumableError,
    balance_status,
    close_line,
    confirm_slip,
    create_item,
    create_slip,
    current_shift,
    daily_sheet,
    expected_usage,
    financial_year,
    fold_daily,
    leakage_qty,
    leakage_report,
    list_slips,
    record_count,
    require_slip,
    return_core,
    return_material,
    round_qty,
    shift_has_aged,
    slip_public,
    variance_pct,
)
from scripts.seed_consumables import CATALOG

IST = ZoneInfo("Asia/Kolkata")


class ConsumableMathTest(unittest.TestCase):
    def test_financial_year_crosses_april(self) -> None:
        self.assertEqual(financial_year(date(2026, 11, 13)), "2026-27")
        self.assertEqual(financial_year(date(2026, 4, 1)), "2026-27")
        self.assertEqual(financial_year(date(2026, 3, 31)), "2025-26")

    def test_leakage_and_balance(self) -> None:
        self.assertEqual(leakage_qty(28.9, 20, 2, 4), 2.9)
        self.assertEqual(leakage_qty(4, 4, 0, 0), 0)
        self.assertEqual(balance_status(closed=False, returned=0, leakage=None), "open")
        self.assertEqual(balance_status(closed=False, returned=10, leakage=None), "partial")
        self.assertEqual(balance_status(closed=True, returned=2, leakage=2.9), "leakage")
        self.assertEqual(balance_status(closed=True, returned=0, leakage=0), "balanced")

    def test_usage_standard_variance(self) -> None:
        expected = expected_usage(0.35, 1000, 50000)
        self.assertEqual(expected, 17.5)
        self.assertEqual(variance_pct(20, expected), 14.3)
        self.assertIsNone(expected_usage(0.35, 1000, None))
        self.assertIsNone(variance_pct(20, None))
        self.assertIsNone(variance_pct(20, 0))

    def test_shift_is_stale_only_after_the_next_shift(self) -> None:
        slip_day = date(2026, 11, 13)
        before = datetime(2026, 11, 13, 21, 59, tzinfo=IST)
        at_end = datetime(2026, 11, 13, 22, 0, tzinfo=IST)
        self.assertFalse(shift_has_aged(slip_day, "A", before))
        self.assertTrue(shift_has_aged(slip_day, "A", at_end))
        # Shift C starts 22:00 and the following shift ends 14:00 the day after.
        self.assertFalse(shift_has_aged(slip_day, "C", datetime(2026, 11, 14, 13, 59, tzinfo=IST)))
        self.assertTrue(shift_has_aged(slip_day, "C", datetime(2026, 11, 14, 14, 0, tzinfo=IST)))
        self.assertIn(current_shift(datetime(2026, 11, 13, 9, 0, tzinfo=IST)), "A")

    def test_daily_sheet_fold_ties_back_to_stock(self) -> None:
        moves = [
            ("opening", 100, date(2026, 10, 1)),
            ("inward", 10, date(2026, 11, 2)),
            ("issue", -28.9, date(2026, 11, 13)),
            ("return", 2, date(2026, 11, 14)),
            ("count", -1, date(2026, 11, 20)),
            ("opening", 50, date(2026, 12, 1)),
        ]
        opening, days, month_in, month_out = fold_daily(
            moves=moves,
            start=date(2026, 11, 1),
            next_month=date(2026, 12, 1),
            days_in_month=30,
        )
        self.assertEqual(opening, 100)
        self.assertEqual(days[1], (10, 0))
        self.assertEqual(days[12], (0, 28.9))
        self.assertEqual(days[13], (0, -2))
        self.assertEqual(days[19], (0, 1))
        self.assertEqual((month_in, month_out), (10, 27.9))
        self.assertEqual(round_qty(opening + month_in - month_out), 82.1)

    def test_catalog_covers_the_sheet_examples(self) -> None:
        self.assertGreaterEqual(len(CATALOG), 30)
        by_name = {row["name"]: row for row in CATALOG}
        self.assertEqual(len(by_name), len(CATALOG))
        strip = by_name["Strip Roll 9 mm Black"]
        self.assertEqual((strip["item_group"], strip["party_name"], strip["rate"], strip["unit"]), ("Strap Roll", "Industrial Tapes & Packers", 760, "Roll"))
        self.assertEqual((strip["min_stock"], strip["max_stock"]), (20, 50))
        wire = by_name["Stitching Wire 15/22 Jumbo"]
        self.assertEqual(wire["party_name"], "Taarobaar Packaging Solution")
        self.assertEqual(wire["rate"], 114)
        self.assertEqual((wire["min_stock"], wire["max_stock"]), (200, 630))
        self.assertEqual(by_name["Stitching Wire 14/25"]["rate"], 111)
        self.assertEqual(by_name['2" Brown Tape']["rate"], 52)
        self.assertEqual(by_name["Maize Starch Powder"]["party_name"], "Dujania Polychem")
        self.assertEqual(by_name["Maize Starch Powder"]["rate"], 45)
        self.assertEqual(by_name["Borax Powder"]["rate"], 100)
        self.assertEqual(by_name["Caustic Soda Flakes"]["rate"], 59)
        self.assertEqual(by_name["Adhesive Fevicol PG 003"]["party_name"], "JSS Polymers")
        self.assertEqual(by_name["Adhesive Fevicol PG 003"]["rate"], 57)
        self.assertEqual(by_name["Pasting Powder"]["rate"], 60)
        self.assertEqual(by_name["Modified Starch"]["rate"], 42)
        self.assertEqual(by_name["Stretch Film Roll"]["rate"], 190)
        self.assertEqual(by_name["Dlx 1034 Brilliant Red ink"]["rate"], 220)
        self.assertLess(by_name["Borax Powder"]["qty_on_hand"], by_name["Borax Powder"]["min_stock"])


def _database_up() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except OperationalError:
        return False


def _consumables_ready() -> bool:
    if not _database_up():
        return False
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1 FROM consumable_items LIMIT 1"))
        return True
    except (OperationalError, ProgrammingError):
        return False


@unittest.skipUnless(_consumables_ready(), "Postgres with the consumables migration is not running")
class ConsumableFlowTest(unittest.TestCase):
    def setUp(self) -> None:
        self.db = SessionLocal()
        self.suffix = uuid.uuid4().hex[:8]
        phone = f"8{uuid.uuid4().int % 10**9:09d}"
        phone_b = f"7{uuid.uuid4().int % 10**9:09d}"
        phone_op_b = f"6{uuid.uuid4().int % 10**9:09d}"
        self.supervisor = User(name=f"ZZ Cons Sup A {self.suffix}", role=UserRole.supervisor, phone_number=phone)
        self.other_supervisor = User(name=f"ZZ Cons Sup B {self.suffix}", role=UserRole.supervisor, phone_number=phone_b)
        self.operator = User(name=f"ZZ Cons Op A {self.suffix}", role=UserRole.operator, phone_number=f"5{uuid.uuid4().int % 10**9:09d}")
        self.other_operator = User(name=f"ZZ Cons Op B {self.suffix}", role=UserRole.operator, phone_number=phone_op_b)
        self.management = User(name=f"ZZ Cons Mgmt {self.suffix}", role=UserRole.management, email=f"zz-cons-{self.suffix}@example.com")
        self.machine = Machine(name=f"ZZ Cons Stitch {self.suffix}", type="stitcher", kind="production")
        self.other_machine = Machine(name=f"ZZ Cons Other {self.suffix}", type="gluer", kind="production")
        self.db.add_all([self.supervisor, self.other_supervisor, self.operator, self.other_operator, self.management, self.machine, self.other_machine])
        self.db.commit()
        self.machine.supervisor_id = self.supervisor.id
        self.machine.operator_id = self.operator.id
        self.other_machine.supervisor_id = self.other_supervisor.id
        self.db.commit()
        self.wire = create_item(
            self.db,
            ConsumableItemCreate(
                name=f"ZZ Cons Wire {self.suffix}",
                item_group="Stitching Wire",
                rate=10,
                unit="Kg",
                qty_on_hand=20,
                min_stock=5,
                standard_qty=0.35,
                standard_per=1000,
                standard_basis="boxes",
            ),
            self.supervisor,
        )
        self.film = create_item(
            self.db,
            ConsumableItemCreate(
                name=f"ZZ Cons Film {self.suffix}",
                item_group="Film",
                rate=190,
                unit="Roll",
                qty_on_hand=5,
                min_stock=1,
                tracks_empty_core=True,
            ),
            self.supervisor,
        )

    def tearDown(self) -> None:
        self.db.rollback()
        machine_ids = [self.machine.id, self.other_machine.id]
        slip_ids = [row[0] for row in self.db.query(ConsumableSlip.id).filter(ConsumableSlip.machine_id.in_(machine_ids)).all()]
        if slip_ids:
            self.db.query(ConsumableSlip).filter(ConsumableSlip.id.in_(slip_ids)).delete(synchronize_session=False)
        self.db.query(ConsumableItem).filter(ConsumableItem.name.like(f"ZZ Cons %{self.suffix}")).delete(synchronize_session=False)
        self.db.query(Machine).filter(Machine.id.in_(machine_ids)).delete(synchronize_session=False)
        self.db.query(User).filter(User.name.like(f"ZZ Cons %{self.suffix}")).delete(synchronize_session=False)
        self.db.commit()
        self.db.close()

    def _issue(self, item: ConsumableItem, qty: float, *, policy: str = "warn", override: bool = False, actor: User | None = None):
        return create_slip(
            self.db,
            SlipCreate(
                slip_date=today_local(),
                shift="A",
                department="Auto Semi",
                machine_id=self.machine.id,
                received_by_id=self.operator.id,
                lines=[SlipLineIn(item_id=item.id, qty=qty)],
                override_missing_cores=override,
            ),
            actor or self.supervisor,
            core_policy=policy,
        )

    def test_issue_return_leakage_scope_and_sheet(self) -> None:
        slip, warnings = self._issue(self.wire, 10)
        self.assertEqual(warnings, [])
        self.db.refresh(self.wire)
        self.assertEqual(self.wire.qty_on_hand, 10)
        self.assertEqual(slip.financial_year, financial_year(today_local()))
        public = slip_public(slip)
        self.assertEqual(public.lines[0].balance_status, "open")
        self.assertEqual(public.slip_no_label, f"{slip.slip_no:02d}" if slip.slip_no < 100 else str(slip.slip_no))

        visible = {row.id for row in list_slips(self.db, self.operator)}
        self.assertIn(slip.id, visible)
        self.assertNotIn(slip.id, {row.id for row in list_slips(self.db, self.other_operator)})
        with self.assertRaises(ConsumableError) as hidden:
            require_slip(self.db, self.other_supervisor, slip.id)
        self.assertEqual(hidden.exception.status_code, 404)
        with self.assertRaises(ConsumableError) as denied:
            create_slip(
                self.db,
                SlipCreate(
                    slip_date=today_local(),
                    shift="A",
                    department="Auto Semi",
                    machine_id=self.machine.id,
                    received_by_id=self.operator.id,
                    lines=[SlipLineIn(item_id=self.wire.id, qty=1)],
                ),
                self.operator,
            )
        self.assertEqual(denied.exception.status_code, 403)
        with self.assertRaises(ConsumableError) as other_machine:
            create_slip(
                self.db,
                SlipCreate(
                    slip_date=today_local(),
                    shift="A",
                    department="Other",
                    machine_id=self.machine.id,
                    received_by_id=self.operator.id,
                    lines=[SlipLineIn(item_id=self.wire.id, qty=1)],
                ),
                self.other_supervisor,
            )
        self.assertEqual(other_machine.exception.status_code, 403)

        slip = return_material(
            self.db,
            self.operator,
            slip.id,
            slip.lines[0].id,
            ReturnCreate(qty=1, note="MIN"),
        )
        self.db.refresh(self.wire)
        self.assertEqual(self.wire.qty_on_hand, 11)
        self.assertEqual(slip.lines[0].qty_returned, 1)
        self.assertEqual(slip_public(slip).lines[0].balance_status, "partial")

        line_id = slip.lines[0].id
        slip = close_line(
            self.db,
            self.operator,
            slip.id,
            line_id,
            CloseLineIn(qty_used=6, qty_returned=1, qty_carried=1, production_qty=1000, leakage_note="operator guess"),
        )
        closed = slip_public(slip).lines[0]
        self.assertEqual(closed.balance_status, "leakage")
        self.assertEqual(closed.leakage_qty, 2)
        self.assertEqual(closed.leakage_value, 20)
        self.assertEqual(closed.expected_qty, 0.35)
        self.assertIsNone(closed.leakage_note)
        self.db.refresh(self.wire)
        self.assertEqual(self.wire.qty_on_hand, 11)

        with self.assertRaises(ConsumableError) as operator_sign:
            confirm_slip(self.db, self.operator, slip.id, ConfirmSlipIn())
        self.assertEqual(operator_sign.exception.status_code, 403)
        with self.assertRaises(ConsumableError) as needs_note:
            confirm_slip(self.db, self.supervisor, slip.id, ConfirmSlipIn())
        self.assertEqual(needs_note.exception.status_code, 422)
        signed = confirm_slip(
            self.db,
            self.supervisor,
            slip.id,
            ConfirmSlipIn(note="Checked", line_notes=[LineNoteIn(line_id=line_id, leakage_note="2 kg short, scrap bin not verified")]),
        )
        self.assertIsNotNone(signed.supervisor_confirmed_at)
        self.assertEqual(slip_public(signed).lines[0].leakage_note, "2 kg short, scrap bin not verified")

        report = leakage_report(self.db, today_local().strftime("%Y-%m"))
        bucket = next(row for row in report.by_item if row.label == self.wire.name)
        self.assertEqual(bucket.qty, 2)
        self.assertEqual(bucket.value_inr, 20)
        self.assertEqual(bucket.variance_pct, variance_pct(6, 0.35))
        self.assertEqual(len(report.by_month), 12)

        before = self.wire.qty_on_hand
        with self.assertRaises(ConsumableError) as short:
            self._issue(self.wire, 1000)
        self.assertEqual(short.exception.status_code, 409)
        self.db.refresh(self.wire)
        self.assertEqual(self.wire.qty_on_hand, before)

        sheet = daily_sheet(self.db, today_local().strftime("%Y-%m"))
        row = next(item for item in sheet.rows if item.item_id == self.wire.id)
        self.assertEqual(row.opening_stock, 20)
        self.assertGreater(row.month_consumption, 0)
        self.assertEqual(row.closing_stock, round_qty(row.opening_stock + row.month_inward - row.month_consumption))
        self.assertEqual(row.closing_stock, self.wire.qty_on_hand)

        move_count = self.db.query(ConsumableMove).filter(ConsumableMove.item_id == self.wire.id).count()
        self.assertGreaterEqual(move_count, 3)

    def test_missing_core_and_physical_count(self) -> None:
        first, warnings = self._issue(self.film, 1)
        self.assertEqual(warnings, [])
        self.db.refresh(self.film)
        self.assertEqual(self.film.cores_outstanding, 1)
        self.assertEqual(self.film.qty_on_hand, 4)
        with self.assertRaises(ConsumableError) as blocked:
            self._issue(self.film, 1, policy="block")
        self.assertEqual(blocked.exception.status_code, 409)
        self.db.refresh(self.film)
        self.assertEqual(self.film.qty_on_hand, 4)

        second, warnings = self._issue(self.film, 1, policy="warn")
        self.assertTrue(warnings)
        self.assertIn("empty core", warnings[0])
        self.db.refresh(self.film)
        self.assertEqual(self.film.qty_on_hand, 3)
        self.assertEqual(self.film.cores_outstanding, 2)

        overridden, override_warnings = self._issue(self.film, 1, policy="block", override=True, actor=self.management)
        self.assertTrue(override_warnings)
        self.db.refresh(self.film)
        self.assertEqual(self.film.qty_on_hand, 2)

        returned = return_core(self.db, self.operator, first.id, first.lines[0].id)
        self.assertTrue(returned.lines[0].core_returned)
        self.db.refresh(self.film)
        self.assertEqual(self.film.cores_outstanding, 2)

        count = record_count(self.db, self.film.id, StockCountCreate(counted_qty=1, note="Floor count"), self.supervisor)
        self.assertEqual(count.book_qty, 2)
        self.assertEqual(count.variance, -1)
        self.db.refresh(self.film)
        self.assertEqual(self.film.qty_on_hand, 1)
        self.assertTrue(self.film.low_stock)

        # Silence unused names from the extra issues; they exist so stock moved.
        self.assertIsNotNone(second.id)
        self.assertIsNotNone(overridden.id)


if __name__ == "__main__":
    unittest.main()
