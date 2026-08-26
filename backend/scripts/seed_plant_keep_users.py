"""Replace machines/PM data on an existing DB without deleting users.

Upserts operators/supervisors from the plant roster by phone. Existing
admin/management accounts are left alone. New people get a random PIN
written to backend/.plant_pins.txt.

Run on Railway: python -m scripts.seed_plant_keep_users
"""

from app.core.security import hash_secret
from app.data.roster import USERS
from app.database import SessionLocal
from app.models import User
from app.seed import create_machines_from_roster, random_pin, wipe_plant_data, write_pin_file


def run() -> None:
    db = SessionLocal()
    try:
        print("Removing machines and PM data; keeping users...")
        wipe_plant_data(db, users=False)

        users_by_phone: dict[str, User] = {
            u.phone_number: u for u in db.query(User).filter(User.phone_number.isnot(None)).all() if u.phone_number
        }
        pin_rows: list[tuple[str, str, str, str]] = []
        created = 0
        for spec in USERS:
            phone = spec["phone_number"]
            existing = users_by_phone.get(phone)
            if existing is not None:
                existing.name = spec["name"]
                existing.role = spec["role"]
                existing.whatsapp_number = existing.whatsapp_number or phone
                existing.can_assign_operators = bool(spec.get("can_assign_operators"))
                continue
            pin = "1234" if spec.get("can_assign_operators") else random_pin()
            user = User(
                name=spec["name"],
                role=spec["role"],
                phone_number=phone,
                whatsapp_number=phone,
                pin_hash=hash_secret(pin),
                can_assign_operators=bool(spec.get("can_assign_operators")),
            )
            db.add(user)
            db.flush()
            users_by_phone[phone] = user
            pin_rows.append((spec["name"], spec["role"].value, phone, pin))
            created += 1

        if pin_rows:
            write_pin_file(pin_rows)
            print(f"Created {created} users. PINs written for NEW accounts only.")
        else:
            print("All roster phones already had accounts; no new PINs.")

        machines_by_name, task_types, items, instances = create_machines_from_roster(db, users_by_phone)
        db.commit()
        print(
            f"Seeded {len(machines_by_name)} machines, {task_types} PM types, "
            f"{items} checklist items, {instances} due tasks. Users kept."
        )
    finally:
        db.close()


if __name__ == "__main__":
    run()
