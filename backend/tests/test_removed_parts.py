import unittest
import uuid
from datetime import date, timedelta

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.core.deps import require_roles
from app.core.time import today_local
from app.database import SessionLocal, engine
from app.models import Machine, PartReplacement, RemovedPart, RemovedPartStatus, SparePart, User, UserRole
from app.routers.part_replacements import create_part_replacement, delete_part_replacement
from app.routers.removed_parts import list_removed_parts, removed_parts_report, set_disposition
from app.schemas.part_replacements import PartReplacementCreate
from app.schemas.removed_parts import RemovedPartCapture, RemovedPartDisposition
from app.services.removed_parts import check_disposition, check_initial
from scripts.seed_removed_parts import seed_removed_parts as seed_demo


class DispositionRulesTest(unittest.TestCase):
    def test_floor_log_only_accepts_an_open_status(self) -> None:
        check_initial(RemovedPartCapture(condition="worn", status="pending_decision"))
        check_initial(RemovedPartCapture(condition="reusable", status="in_maintenance_store", location="Rack B"))
        with self.assertRaises(ValueError):
            check_initial(RemovedPartCapture(status="scrapped"))
        with self.assertRaises(ValueError):
            check_initial(RemovedPartCapture(photo_url="https://example.com/not-an-upload.jpg"))

    def test_disposition_requires_the_fields_for_that_outcome(self) -> None:
        with self.assertRaises(ValueError):
            check_disposition(RemovedPartDisposition(status="sent_for_repair", vendor="  "))
        with self.assertRaises(ValueError):
            check_disposition(
                RemovedPartDisposition(status="scrapped", scrap_on=date(2026, 10, 1), scrap_qty=1.5, scrap_unit="kg")
            )
        with self.assertRaises(ValueError):
            check_disposition(RemovedPartDisposition(status="sold", sale_buyer="Ravi", sale_amount=100))
        check_disposition(
            RemovedPartDisposition(
                status="scrapped",
                scrap_on=date(2026, 10, 1),
                scrap_qty=1.8,
                scrap_unit="kg",
                scrap_buyer="Sonipat Scrap Co.",
            )
        )
        with self.assertRaises(ValidationError):
            RemovedPartDisposition(status="returned_to_stock", quantity=0)

    def test_photo_must_be_an_upload_url(self) -> None:
        check_disposition(
            RemovedPartDisposition(
                status="pending_decision",
                photo_url="/uploads/123e4567-e89b-12d3-a456-426614174000.jpg",
            )
        )


def _database_up() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except OperationalError:
        return False


@unittest.skipUnless(_database_up(), "Postgres is not running")
class RemovedPartFlowTest(unittest.TestCase):
    def setUp(self) -> None:
        self.db = SessionLocal()
        suffix = uuid.uuid4().hex[:8]
        self.user = User(name="Removed Tester", role=UserRole.supervisor, phone_number=f"8{uuid.uuid4().int % 10**9:09d}")
        self.operator = User(name="Removed Operator", role=UserRole.operator, phone_number=f"7{uuid.uuid4().int % 10**9:09d}")
        self.other = User(name="Other Supervisor", role=UserRole.supervisor, phone_number=f"6{uuid.uuid4().int % 10**9:09d}")
        self.management = User(name="Removed Management", role=UserRole.management, email=f"removed-{suffix}@example.com")
        self.machine = Machine(name=f"ZZ Test Corrugator {suffix}", type="corrugator", kind="production")
        self.other_machine = Machine(name=f"ZZ Test Printer {suffix}", type="printer", kind="production")
        self.db.add_all([self.user, self.operator, self.other, self.management, self.machine, self.other_machine])
        self.db.commit()
        self.machine.supervisor_id = self.user.id
        self.machine.operator_id = self.operator.id
        self.other_machine.supervisor_id = self.other.id
        self.fitted = SparePart(
            name=f"ZZ New blade {suffix}",
            item_group="Blade",
            category=f"zztest-removed-{suffix}",
            qty_on_hand=5,
        )
        self.refurb = SparePart(
            name="Thin Blade Used Refurbish",
            item_group="Blade",
            category=f"zztest-removed-{suffix}",
            qty_on_hand=2,
            unit="pcs",
        )
        self.db.add_all([self.fitted, self.refurb])
        self.db.commit()
        self.user_id = self.user.id
        self.operator_id = self.operator.id
        self.other_id = self.other.id
        self.management_id = self.management.id
        self.machine_id = self.machine.id
        self.other_machine_id = self.other_machine.id
        self.fitted_id = self.fitted.id
        self.refurb_id = self.refurb.id
        self.suffix = suffix

    def tearDown(self) -> None:
        self.db.rollback()
        machine_ids = [self.machine_id, self.other_machine_id]
        self.db.query(PartReplacement).filter(PartReplacement.machine_id.in_(machine_ids)).delete(synchronize_session=False)
        self.db.query(SparePart).filter(SparePart.category == f"zztest-removed-{self.suffix}").delete(synchronize_session=False)
        self.db.query(Machine).filter(Machine.id.in_(machine_ids)).delete(synchronize_session=False)
        self.db.query(User).filter(User.id.in_([self.user_id, self.operator_id, self.other_id, self.management_id])).delete(
            synchronize_session=False
        )
        self.db.commit()
        self.db.close()

    def _reload(self) -> tuple[SparePart, SparePart]:
        fitted = self.db.get(SparePart, self.fitted_id)
        refurb = self.db.get(SparePart, self.refurb_id)
        assert fitted is not None and refurb is not None
        return fitted, refurb

    def test_replacement_opens_a_trail_and_disposition_moves_stock_once(self) -> None:
        created = create_part_replacement(
            PartReplacementCreate(
                machine_id=self.machine_id,
                part_name="Thin blade",
                replaced_at=today_local() - timedelta(days=13),
                notes="Edge worn",
                spare_part_id=self.fitted_id,
                quantity_used=1,
                removed=RemovedPartCapture(
                    condition="worn",
                    status="pending_decision",
                    quantity=1,
                    notes="Edge worn",
                ),
            ),
            self.db,
            self.user,
        )
        fitted, refurb = self._reload()
        self.assertEqual(fitted.qty_on_hand, 4)
        self.assertEqual(refurb.qty_on_hand, 2)
        self.assertIsNotNone(created.removed_part)
        assert created.removed_part is not None
        self.assertEqual(created.removed_part.condition.value, "worn")
        self.assertEqual(created.removed_part.status, RemovedPartStatus.pending_decision)
        self.assertEqual(len(created.removed_part.events), 1)
        self.assertGreaterEqual(created.removed_part.age_days, 13)

        updated = set_disposition(
            created.removed_part.id,
            RemovedPartDisposition(
                status="returned_to_stock",
                spare_part_id=self.refurb_id,
                quantity=1,
                notes="Ground and back in the refurb bin",
                photo_url="/uploads/123e4567-e89b-12d3-a456-426614174000.jpg",
            ),
            self.db,
            self.user,
        )
        _, refurb = self._reload()
        self.assertEqual(refurb.qty_on_hand, 3)
        self.assertEqual(updated.status, RemovedPartStatus.returned_to_stock)
        self.assertEqual(updated.refurb_spare_name, "Thin Blade Used Refurbish")
        self.assertEqual(len(updated.events), 2)
        self.assertEqual(updated.events[0].notes, "Edge worn")
        self.assertEqual(updated.events[1].photo_url, "/uploads/123e4567-e89b-12d3-a456-426614174000.jpg")

        noted = set_disposition(
            created.removed_part.id,
            RemovedPartDisposition(status="returned_to_stock", notes="Photo added earlier, no extra piece"),
            self.db,
            self.user,
        )
        _, refurb = self._reload()
        self.assertEqual(refurb.qty_on_hand, 3)
        self.assertEqual(len(noted.events), 3)
        self.assertEqual(noted.events[0].notes, "Edge worn")

        scrapped = set_disposition(
            created.removed_part.id,
            RemovedPartDisposition(
                status="scrapped",
                scrap_on=date(2026, 10, 20),
                scrap_qty=0.4,
                scrap_unit="kg",
                scrap_buyer="Sonipat Scrap Co.",
                notes="Cracked after grinding",
            ),
            self.db,
            self.user,
        )
        _, refurb = self._reload()
        self.assertEqual(refurb.qty_on_hand, 2)
        self.assertEqual(scrapped.status, RemovedPartStatus.scrapped)
        self.assertEqual(scrapped.scrap_buyer, "Sonipat Scrap Co.")

        with self.assertRaises(HTTPException) as denied:
            set_disposition(
                created.removed_part.id,
                RemovedPartDisposition(status="in_maintenance_store", location="Rack B"),
                self.db,
                self.other,
            )
        self.assertEqual(denied.exception.status_code, 403)
        with self.assertRaises(HTTPException) as management_denied:
            set_disposition(
                created.removed_part.id,
                RemovedPartDisposition(status="in_maintenance_store", location="Rack B"),
                self.db,
                self.management,
            )
        self.assertEqual(management_denied.exception.status_code, 403)

        rows = list_removed_parts(
            status_filter=RemovedPartStatus.scrapped,
            machine_id=self.machine_id,
            from_date=None,
            to_date=None,
            pending_only=False,
            stale_only=False,
            stale_days=7,
            db=self.db,
            current_user=self.user,
        )
        self.assertEqual([row.id for row in rows], [created.removed_part.id])

        stale = list_removed_parts(
            status_filter=None,
            machine_id=self.machine_id,
            from_date=None,
            to_date=None,
            pending_only=False,
            stale_only=True,
            stale_days=7,
            db=self.db,
            current_user=self.user,
        )
        self.assertEqual(stale, [])

        report = removed_parts_report(stale_days=7, db=self.db, current_user=self.user)
        by_status = {item.status: item.count for item in report.by_status}
        self.assertEqual(by_status[RemovedPartStatus.scrapped], 1)
        self.assertEqual(by_status[RemovedPartStatus.pending_decision], 0)
        self.assertEqual(report.months[0].scrap[0].unit, "kg")
        self.assertEqual(report.months[0].scrap[0].qty, 0.4)
        self.assertEqual(report.machines[0].machine_id, self.machine_id)
        self.assertEqual(report.machines[0].replacements, 1)

        hidden = list_removed_parts(
            status_filter=None,
            machine_id=None,
            from_date=None,
            to_date=None,
            pending_only=False,
            stale_only=False,
            stale_days=7,
            db=self.db,
            current_user=self.other,
        )
        self.assertTrue(all(row.machine_id != self.machine_id for row in hidden))

    def test_undo_restores_fitted_stock_and_reverses_a_refurb_credit(self) -> None:
        created = create_part_replacement(
            PartReplacementCreate(
                machine_id=self.machine_id,
                part_name="Thin blade",
                replaced_at=today_local(),
                spare_part_id=self.fitted_id,
                quantity_used=1,
                removed=RemovedPartCapture(condition="reusable", status="in_maintenance_store", location="Rack B"),
            ),
            self.db,
            self.operator,
        )
        assert created.removed_part is not None
        removed_id = created.removed_part.id
        set_disposition(
            created.removed_part.id,
            RemovedPartDisposition(status="returned_to_stock", spare_part_id=self.refurb_id, quantity=1),
            self.db,
            self.user,
        )
        refurb = self.db.get(SparePart, self.refurb_id)
        assert refurb is not None
        refurb.qty_on_hand = 0
        self.db.commit()
        with self.assertRaises(HTTPException) as blocked:
            delete_part_replacement(created.id, self.db, self.user)
        self.assertEqual(blocked.exception.status_code, 409)
        self.assertIsNotNone(self.db.get(PartReplacement, created.id))
        refurb = self.db.get(SparePart, self.refurb_id)
        assert refurb is not None
        self.assertEqual(refurb.qty_on_hand, 0)

        refurb.qty_on_hand = 1
        self.db.commit()
        delete_part_replacement(created.id, self.db, self.user)
        fitted, refurb = self._reload()
        self.assertEqual(fitted.qty_on_hand, 5)
        self.assertEqual(refurb.qty_on_hand, 0)
        self.assertIsNone(self.db.get(RemovedPart, removed_id))

    def test_operator_cannot_set_a_final_disposition_while_logging(self) -> None:
        with self.assertRaises(HTTPException) as raised:
            create_part_replacement(
                PartReplacementCreate(
                    machine_id=self.machine_id,
                    part_name="Anilox roller",
                    replaced_at=today_local(),
                    spare_part_id=self.fitted_id,
                    quantity_used=1,
                    removed=RemovedPartCapture(status="sold"),
                ),
                self.db,
                self.operator,
            )
        self.assertEqual(raised.exception.status_code, 422)
        fitted, refurb = self._reload()
        self.assertEqual(fitted.qty_on_hand, 5)
        self.assertEqual(refurb.qty_on_hand, 2)
        self.assertEqual(self.db.query(PartReplacement).filter(PartReplacement.machine_id == self.machine_id).count(), 0)

    def test_demo_seed_is_idempotent_and_credits_refurb_once(self) -> None:
        prefix = f"zztest-removed-seed-{self.suffix}"
        before = self.refurb.qty_on_hand
        first = seed_demo(
            self.db,
            machines=[self.machine],
            refurb_spare=self.refurb,
            lookup_refurb=False,
            tag_prefix=prefix,
            today=date(2026, 10, 26),
        )
        self.assertEqual(first["created"], 7)
        self.assertEqual(first["skipped"], 0)
        self.db.refresh(self.refurb)
        self.assertEqual(self.refurb.qty_on_hand, before + 1)
        pending = (
            self.db.query(RemovedPart)
            .join(RemovedPart.part_replacement)
            .filter(PartReplacement.machine_id == self.machine_id, RemovedPart.status == RemovedPartStatus.pending_decision)
            .all()
        )
        self.assertTrue(any((date(2026, 10, 26) - row.replaced_at).days >= 7 for row in pending))
        second = seed_demo(
            self.db,
            machines=[self.machine],
            refurb_spare=self.refurb,
            lookup_refurb=False,
            tag_prefix=prefix,
            today=date(2026, 10, 26),
        )
        self.assertEqual(second["created"], 0)
        self.assertEqual(second["skipped"], 7)
        self.db.refresh(self.refurb)
        self.assertEqual(self.refurb.qty_on_hand, before + 1)

    def test_write_role_matches_the_rest_of_stores(self) -> None:
        gate = require_roles(UserRole.supervisor, UserRole.admin)
        with self.assertRaises(HTTPException) as raised:
            gate(self.management)
        self.assertEqual(raised.exception.status_code, 403)
        self.assertEqual(gate(self.user).id, self.user_id)
        read = require_roles(UserRole.supervisor, UserRole.management, UserRole.admin)
        self.assertEqual(read(self.management).role, UserRole.management)
        with self.assertRaises(HTTPException):
            read(self.operator)


if __name__ == "__main__":
    unittest.main()
