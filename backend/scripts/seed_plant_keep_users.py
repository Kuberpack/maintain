"""Replace machines/PM data on an existing DB without deleting users.

Run on Railway: python -m scripts.seed_plant_keep_users
"""

from datetime import timedelta

from app.core.time import today_local
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
)
from app.seed import DUE_DATE_OFFSETS, MACHINES, templates_for_machine


def run() -> None:
    db = SessionLocal()
    try:
        print("Removing machines and PM data; keeping users...")
        db.query(ChecklistItemResult).delete()
        db.query(HandoverNote).delete()
        db.query(TaskInstance).delete()
        db.query(RepairLog).delete()
        db.query(PartReplacement).delete()
        db.query(ChecklistItem).delete()
        db.query(TaskType).delete()
        db.query(Machine).delete()
        db.commit()

        offsets = iter(DUE_DATE_OFFSETS)
        seeded_task_types = 0
        seeded_items = 0
        seeded_instances = 0
        for m in MACHINES:
            machine = Machine(**m)
            db.add(machine)
            db.flush()
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

        db.commit()
        print(
            f"Seeded {len(MACHINES)} machines, {seeded_task_types} PM types, "
            f"{seeded_items} checklist items, {seeded_instances} due tasks. Users kept."
        )
    finally:
        db.close()


if __name__ == "__main__":
    run()
