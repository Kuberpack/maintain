"""Seed the database with the Kuberpack plant roster and PM checklists.

Destructive: wipes existing machines/users/task data before reseeding.

PINs are random and written to backend/.plant_pins.txt (gitignored).

Run with: .venv/bin/python -m app.seed  (from backend/)
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.security import hash_secret
from app.core.time import today_local
from app.data.checklists import (
    BOILER,
    COMPRESSOR,
    ETP,
    FORKLIFT,
    GENERIC,
    GENERATOR,
    SCRAP,
    TEMPLATES_FAC_GLUE,
    TEMPLATES_FAC_LINE,
    TEMPLATES_FAC_NC,
    TEMPLATES_FAC_PASTING,
    TRANSFORMER,
)
from app.data.checklists.common import PmTemplate
from app.data.roster import MACHINES, USERS
from app.database import SessionLocal
from app.models import (
    ChecklistItem,
    ChecklistItemResult,
    HandoverNote,
    Machine,
    PartReplacement,
    RepairLog,
    ShiftLog,
    TaskCategory,
    TaskInstance,
    TaskType,
    User,
    UserAuditEvent,
    UserRole,
    VendorContact,
)

PIN_FILE = Path(__file__).resolve().parent.parent / ".plant_pins.txt"

DUE_DATE_OFFSETS = [-5, -1, 0, 1, 2, 3, 5, 7, 10, 14, 20, 30]

_TEMPLATE_MAP: dict[str, list[PmTemplate]] = {
    "fac_line": TEMPLATES_FAC_LINE,
    "fac_pasting": TEMPLATES_FAC_PASTING,
    "fac_nc": TEMPLATES_FAC_NC,
    "fac_glue": TEMPLATES_FAC_GLUE,
    "generic": GENERIC,
    "etp": ETP,
    "compressor": COMPRESSOR,
    "generator": GENERATOR,
    "transformer": TRANSFORMER,
    "boiler": BOILER,
    "forklift": FORKLIFT,
    "scrap": SCRAP,
}


def templates_for(key: str) -> list[PmTemplate]:
    return _TEMPLATE_MAP[key]


def random_pin() -> str:
    return f"{secrets.randbelow(10000):04d}"


def write_pin_file(rows: list[tuple[str, str, str, str]]) -> None:
    lines = [
        "# Generated plant logins. Do not commit this file.",
        "# name | role | phone | pin",
        *(f"{name} | {role} | {phone} | {pin}" for name, role, phone, pin in rows),
        "",
    ]
    PIN_FILE.write_text("\n".join(lines), encoding="utf-8")


def attach_pm(
    db: Session,
    machine: Machine,
    templates: list[PmTemplate],
    offsets: object,
) -> tuple[int, int, int]:
    task_types = 0
    items = 0
    instances = 0
    for template in templates:
        task_type = TaskType(
            machine_id=machine.id,
            category=TaskCategory.preventive,
            description=template["description"],
            default_interval_days=template["default_interval_days"],
        )
        db.add(task_type)
        db.flush()
        task_types += 1
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
            items += 1
        due_date = today_local() + timedelta(days=next(offsets, 0))
        db.add(TaskInstance(task_type_id=task_type.id, due_date=due_date))
        instances += 1
    return task_types, items, instances


def create_machines_from_roster(db: Session, users_by_phone: dict[str, User]) -> tuple[dict[str, Machine], int, int, int]:
    offsets = iter(DUE_DATE_OFFSETS)
    machines_by_name: dict[str, Machine] = {}
    seeded_task_types = 0
    seeded_items = 0
    seeded_instances = 0
    for spec in MACHINES:
        operator = users_by_phone.get(spec["operator_phone"]) if spec.get("operator_phone") else None
        supervisor = users_by_phone.get(spec["supervisor_phone"]) if spec.get("supervisor_phone") else None
        machine = Machine(
            name=spec["name"],
            type=spec["type"],
            location=spec.get("location"),
            group_name=spec.get("group_name"),
            kind=spec["kind"],
            operator_id=operator.id if operator else None,
            supervisor_id=supervisor.id if supervisor else None,
        )
        db.add(machine)
        db.flush()
        machines_by_name[spec["name"]] = machine
        tt, items, inst = attach_pm(db, machine, templates_for(spec["template"]), offsets)
        seeded_task_types += tt
        seeded_items += items
        seeded_instances += inst
    return machines_by_name, seeded_task_types, seeded_items, seeded_instances


def wipe_plant_data(db: Session, *, users: bool) -> None:
    db.query(ChecklistItemResult).delete()
    db.query(HandoverNote).delete()
    db.query(ShiftLog).delete()
    db.query(TaskInstance).delete()
    db.query(RepairLog).delete()
    db.query(PartReplacement).delete()
    db.query(VendorContact).delete()
    db.query(ChecklistItem).delete()
    db.query(TaskType).delete()
    db.query(Machine).delete()
    if users:
        db.query(UserAuditEvent).delete()
        db.query(User).delete()
    db.commit()


def run_seed() -> None:
    db = SessionLocal()
    try:
        print("Wiping existing data...")
        wipe_plant_data(db, users=True)

        print("Creating users...")
        users_by_phone: dict[str, User] = {}
        pin_rows: list[tuple[str, str, str, str]] = []
        for u in USERS:
            pin = "1234" if u.get("can_assign_operators") else random_pin()
            user = User(
                name=u["name"],
                role=u["role"],
                phone_number=u["phone_number"],
                whatsapp_number=u["phone_number"],
                pin_hash=hash_secret(pin),
                can_assign_operators=bool(u.get("can_assign_operators")),
            )
            db.add(user)
            users_by_phone[u["phone_number"]] = user
            pin_rows.append((u["name"], u["role"].value, u["phone_number"], pin))

        management = User(
            name="Priya Kapoor",
            role=UserRole.management,
            email="priya.kapoor@kuberpack.com",
            password_hash=hash_secret("ChangeMe123!"),
            whatsapp_number="9812345006",
        )
        db.add(management)
        db.flush()

        write_pin_file(pin_rows)
        print(f"Wrote operator/supervisor PINs to {PIN_FILE}")

        print("Creating machines, PM task types, and checklist items...")
        machines_by_name, seeded_task_types, seeded_items, seeded_instances = create_machines_from_roster(
            db, users_by_phone
        )

        print("Creating sample repair logs...")
        fac = machines_by_name["Corrugation (A/B)"]
        printer = machines_by_name["Lead Edge Printing"]
        db.add(
            RepairLog(
                machine_id=fac.id,
                reported_by=users_by_phone["7077132073"].id,
                issue_description="Belt slipping under load",
                downtime_minutes=45,
                resolved_at=datetime.now(timezone.utc),
                resolved_by=users_by_phone["9052330003"].id,
                resolution_notes="Replaced drive belt",
            )
        )
        db.add(
            RepairLog(
                machine_id=printer.id,
                reported_by=users_by_phone["8396865982"].id,
                issue_description="Ink pump making unusual noise",
            )
        )
        db.add(
            PartReplacement(
                machine_id=fac.id,
                part_name="Drive belt",
                replaced_at=today_local() - timedelta(days=10),
                replaced_by=users_by_phone["9052330003"].id,
                notes="Worn from extended use",
            )
        )

        db.commit()
        print(
            f"Seeded {len(MACHINES)} machines, {len(USERS) + 1} users, "
            f"{seeded_task_types} task types, {seeded_items} checklist items, "
            f"{seeded_instances} task instances."
        )
        print("Hand out PINs from backend/.plant_pins.txt — they are not in git.")
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()
