"""Seed the database with Kuberpack plant machines and PM checklists.

Destructive: wipes existing machines/users/task data before reseeding.

Run with: .venv/bin/python -m app.seed  (from backend/)
"""

from datetime import datetime, timedelta, timezone

from app.core.security import hash_secret
from app.core.time import today_local
from app.data.checklists import CORRUGATION, ETP, GENERIC
from app.data.checklists.common import PmTemplate
from app.database import SessionLocal
from app.models import (
    ChecklistItem,
    ChecklistItemResult,
    HandoverNote,
    Machine,
    PartReplacement,
    RepairLog,
    TaskCategory,
    TaskInstance,
    TaskType,
    User,
    UserRole,
)

MACHINES = [
    {"name": "Corrugation Machine", "type": "corrugator", "location": "Sonipat plant"},
    {"name": "Lead Edge Printing", "type": "printer", "location": "Sonipat plant"},
    {"name": "Chain Feeder Printing", "type": "printer", "location": "Sonipat plant"},
    {"name": "Auto Gluer Machine", "type": "folder-gluer", "location": "Sonipat plant"},
    {"name": "Auto Gluer Machine DGM", "type": "folder-gluer", "location": "Sonipat plant"},
    {"name": "Auto Stitching Machine", "type": "stitcher", "location": "Sonipat plant"},
    {"name": "Semi Auto Stitching Machine", "type": "stitcher", "location": "Sonipat plant"},
    {"name": "Flat Bed Die", "type": "die-cutter", "location": "Sonipat plant"},
    {"name": "Die Punching Machine - 56x76 (old)", "type": "die-cutter", "location": "Sonipat plant"},
    {"name": "Die Punching Machine - 44x56 (new)", "type": "die-cutter", "location": "Sonipat plant"},
    {"name": "Die Punching Machine - 52x72 (small)", "type": "die-cutter", "location": "Sonipat plant"},
    {"name": "Rotary", "type": "rotary", "location": "Sonipat plant"},
    {"name": "Flute Laminator", "type": "laminator", "location": "Sonipat plant"},
    {"name": "Manual Pasting", "type": "pasting", "location": "Sonipat plant"},
    {"name": "Manual Stitching Machine (1)", "type": "stitcher", "location": "Sonipat plant"},
    {"name": "Manual Stitching Machine (2)", "type": "stitcher", "location": "Sonipat plant"},
    {"name": "Manual Stitching Machine (3)", "type": "stitcher", "location": "Sonipat plant"},
    {"name": "ETP and STP", "type": "utility", "location": "Sonipat plant"},
]

USERS = [
    {"name": "Ramesh Kumar", "role": UserRole.operator, "phone_number": "9812345001", "pin": "1234"},
    {"name": "Suresh Yadav", "role": UserRole.operator, "phone_number": "9812345002", "pin": "2345"},
    {"name": "Vikram Singh", "role": UserRole.operator, "phone_number": "9812345003", "pin": "3456"},
    {"name": "Anita Sharma", "role": UserRole.supervisor, "phone_number": "9812345004", "pin": "4567"},
    {"name": "Rajesh Verma", "role": UserRole.supervisor, "phone_number": "9812345005", "pin": "5678"},
    {
        "name": "Priya Kapoor",
        "role": UserRole.management,
        "email": "priya.kapoor@kuberpack.com",
        "password": "ChangeMe123!",
        "whatsapp_number": "9812345006",
    },
]

DUE_DATE_OFFSETS = [-5, -1, 0, 1, 2, 3, 5, 7, 10, 14, 20, 30]


def templates_for_machine(name: str) -> list[PmTemplate]:
    if name == "Corrugation Machine":
        return CORRUGATION
    if name == "ETP and STP":
        return ETP
    return GENERIC


def run_seed() -> None:
    db = SessionLocal()
    try:
        print("Wiping existing data...")
        db.query(ChecklistItemResult).delete()
        db.query(HandoverNote).delete()
        db.query(TaskInstance).delete()
        db.query(RepairLog).delete()
        db.query(PartReplacement).delete()
        db.query(ChecklistItem).delete()
        db.query(TaskType).delete()
        db.query(Machine).delete()
        db.query(User).delete()
        db.commit()

        print("Creating users...")
        users_by_name: dict[str, User] = {}
        for u in USERS:
            user = User(
                name=u["name"],
                role=u["role"],
                email=u.get("email"),
                phone_number=u.get("phone_number"),
                whatsapp_number=u.get("whatsapp_number", u.get("phone_number")),
                pin_hash=hash_secret(u["pin"]) if "pin" in u else None,
                password_hash=hash_secret(u["password"]) if "password" in u else None,
            )
            db.add(user)
            users_by_name[u["name"]] = user
        db.flush()

        operators = [u for u in users_by_name.values() if u.role == UserRole.operator]
        supervisors = [u for u in users_by_name.values() if u.role == UserRole.supervisor]

        print("Creating machines, PM task types, and checklist items...")
        machines_by_name: dict[str, Machine] = {}
        offsets = iter(DUE_DATE_OFFSETS)
        seeded_instances = 0
        seeded_task_types = 0
        seeded_items = 0
        for m in MACHINES:
            machine = Machine(**m)
            db.add(machine)
            db.flush()
            machines_by_name[m["name"]] = machine
            for template in templates_for_machine(m["name"]):
                task_type = TaskType(
                    machine_id=machine.id,
                    category=TaskCategory.preventive,
                    description=template["description"],
                    default_interval_days=template["default_interval_days"],
                )
                db.add(task_type)
                db.flush()
                seeded_task_types += 1
                for sort_order, spec in enumerate(template["items"]):
                    db.add(
                        ChecklistItem(
                            task_type_id=task_type.id,
                            section=spec["section"],
                            sort_order=sort_order,
                            description=spec["description"],
                            requires_value=spec["requires_value"],
                            value_unit=spec["value_unit"] or None,
                            min_value=spec.get("min_value"),
                            max_value=spec.get("max_value"),
                        )
                    )
                    seeded_items += 1
                due_date = today_local() + timedelta(days=next(offsets, 0))
                db.add(TaskInstance(task_type_id=task_type.id, due_date=due_date))
                seeded_instances += 1

        print("Creating repair logs...")
        corrugator = machines_by_name["Corrugation Machine"]
        printer = machines_by_name["Lead Edge Printing"]
        db.add(
            RepairLog(
                machine_id=corrugator.id,
                reported_by=operators[1].id,
                issue_description="Belt slipping under load",
                downtime_minutes=45,
                resolved_at=datetime.now(timezone.utc),
                resolved_by=supervisors[0].id,
                resolution_notes="Replaced drive belt",
            )
        )
        db.add(
            RepairLog(
                machine_id=printer.id,
                reported_by=operators[2].id,
                issue_description="Ink pump making unusual noise",
            )
        )

        print("Creating part replacements...")
        db.add(
            PartReplacement(
                machine_id=corrugator.id,
                part_name="Drive belt",
                replaced_at=today_local() - timedelta(days=10),
                replaced_by=supervisors[0].id,
                notes="Worn from extended use",
            )
        )

        db.commit()
        print(
            f"Seeded {len(MACHINES)} machines, {len(USERS)} users, "
            f"{seeded_task_types} task types, {seeded_items} checklist items, "
            f"{seeded_instances} task instances."
        )
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()
