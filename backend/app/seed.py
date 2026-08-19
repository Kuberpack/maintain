"""Seed the database with realistic dummy data for local development and
testing. There is no real Kuberpack data yet -- the MACHINES/USERS/
TASK_TYPES constants below are placeholders. When real data is available,
replace those constants; the seeding logic itself shouldn't need to change.

Destructive: wipes existing machines/users/task data before reseeding.

Run with: .venv/bin/python -m app.seed  (from backend/)
"""

from datetime import datetime, timedelta, timezone

from app.core.security import hash_secret
from app.core.time import today_local
from app.database import SessionLocal
from app.models import (
    Machine,
    PartReplacement,
    RepairLog,
    TaskCategory,
    TaskInstance,
    TaskType,
    User,
    UserRole,
)
from app.services.scheduling import complete_task_instance

# --- Dummy data: replace with real Kuberpack data when available -----------

MACHINES = [
    {"name": "Corrugator 1", "type": "corrugator", "location": "Bay A"},
    {"name": "Flexo Printer 1", "type": "printer", "location": "Bay B"},
    {"name": "Folder-Gluer 1", "type": "folder-gluer", "location": "Bay B"},
    {"name": "Laminator 1", "type": "laminator", "location": "Bay C"},
    {"name": "Die-Cutter 1", "type": "die-cutter", "location": "Bay C"},
]

# pin/password are plaintext here only because this is the seed script --
# hashed via hash_secret() before ever touching the users table.
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

# machine name -> task types for that machine. default_interval_days is
# omitted (None) for repair -- event-driven, not scheduled, per schema.md.
TASK_TYPES: dict[str, list[dict]] = {
    "Corrugator 1": [
        {"category": TaskCategory.cleaning, "description": "Clean rollers and belts", "default_interval_days": 7},
        {"category": TaskCategory.oiling, "description": "Grease main shaft bearings", "default_interval_days": 14},
        {
            "category": TaskCategory.part_replacement,
            "description": "Inspect/replace glue applicator tips",
            "default_interval_days": 30,
        },
        {"category": TaskCategory.repair, "description": "Unscheduled repair", "default_interval_days": None},
    ],
    "Flexo Printer 1": [
        {
            "category": TaskCategory.cleaning,
            "description": "Clean print rollers and ink trays",
            "default_interval_days": 3,
        },
        {"category": TaskCategory.oiling, "description": "Oil drive chain", "default_interval_days": 14},
        {"category": TaskCategory.repair, "description": "Unscheduled repair", "default_interval_days": None},
    ],
    "Folder-Gluer 1": [
        {"category": TaskCategory.cleaning, "description": "Clean glue nozzles", "default_interval_days": 5},
        {"category": TaskCategory.oiling, "description": "Lubricate folding belts", "default_interval_days": 21},
        {"category": TaskCategory.repair, "description": "Unscheduled repair", "default_interval_days": None},
    ],
    "Laminator 1": [
        {"category": TaskCategory.cleaning, "description": "Clean laminate rollers", "default_interval_days": 7},
        {
            "category": TaskCategory.oiling,
            "description": "Grease heating roller bearings",
            "default_interval_days": 30,
        },
        {"category": TaskCategory.repair, "description": "Unscheduled repair", "default_interval_days": None},
    ],
    "Die-Cutter 1": [
        {"category": TaskCategory.cleaning, "description": "Clean cutting bed", "default_interval_days": 7},
        {
            "category": TaskCategory.part_replacement,
            "description": "Replace cutting die blades",
            "default_interval_days": 60,
        },
        {"category": TaskCategory.repair, "description": "Unscheduled repair", "default_interval_days": None},
    ],
}

# Due-date offsets (days from today), cycled across the non-repair task
# types, to spread seeded instances across overdue / due-soon / comfortably
# pending -- so all three status colors have something to show once the
# frontend is built. Falls back to "due today" if TASK_TYPES grows past
# this list's length.
DUE_DATE_OFFSETS = [-5, -1, 0, 1, 2, 3, 5, 7, 10, 14, 20]


def run_seed() -> None:
    db = SessionLocal()
    try:
        print("Wiping existing data...")
        # Deletion order matters: task_instances/repair_logs/part_replacements
        # hold RESTRICT FKs to users, so they must go before users. Bulk
        # .delete() issues plain SQL DELETEs -- no ORM cascade surprises.
        db.query(TaskInstance).delete()
        db.query(RepairLog).delete()
        db.query(PartReplacement).delete()
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

        print("Creating machines...")
        machines_by_name: dict[str, Machine] = {}
        for m in MACHINES:
            machine = Machine(**m)
            db.add(machine)
            machines_by_name[m["name"]] = machine
        db.flush()

        print("Creating task types and task instances...")
        offsets = iter(DUE_DATE_OFFSETS)
        seeded_instances: list[TaskInstance] = []
        for machine_name, task_types in TASK_TYPES.items():
            machine = machines_by_name[machine_name]
            for tt in task_types:
                task_type = TaskType(machine_id=machine.id, **tt)
                db.add(task_type)
                db.flush()
                if tt["default_interval_days"] is not None:
                    due_date = today_local() + timedelta(days=next(offsets, 0))
                    instance = TaskInstance(task_type_id=task_type.id, due_date=due_date)
                    db.add(instance)
                    seeded_instances.append(instance)
        db.flush()

        print("Marking one task instance done, to demonstrate the recurring chain...")
        complete_task_instance(
            db, seeded_instances[0], completed_by=operators[0].id, notes="Seed data: completed for demo"
        )

        print("Creating repair logs...")
        corrugator = machines_by_name["Corrugator 1"]
        printer = machines_by_name["Flexo Printer 1"]
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
        total_task_types = sum(len(v) for v in TASK_TYPES.values())
        print(
            f"Seeded {len(MACHINES)} machines, {len(USERS)} users, "
            f"{total_task_types} task types, {len(seeded_instances)} task instances."
        )
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()
