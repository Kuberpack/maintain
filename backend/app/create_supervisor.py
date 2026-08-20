"""One-off bootstrap script: creates a single real supervisor account so a
fresh, empty database (no seed data) has someone who can log in and start
adding real machines/task types/users through the app itself.

Deliberately separate from seed.py -- this never wipes or touches anything
else in the database, and only ever creates the one account you ask for.

Run inside the backend container:
    docker compose exec backend python -m app.create_supervisor

Or locally (from backend/):
    .venv/bin/python -m app.create_supervisor

Prompts for name, phone number, and PIN interactively -- the PIN prompt is
hidden like a password field -- rather than taking them as command-line
arguments, so the PIN never ends up in shell history or a process listing.
"""

import re
import sys
from getpass import getpass

from sqlalchemy.exc import IntegrityError

from app.core.security import hash_secret
from app.database import SessionLocal
from app.models import User, UserRole

# Same rule the API itself enforces (UserCreate.pin in app/schemas/users.py) --
# kept in sync manually since this script talks to the DB directly and never
# goes through that schema.
PIN_PATTERN = re.compile(r"^\d{4,6}$")


def main() -> None:
    name = input("Full name: ").strip()
    if not name:
        sys.exit("Name is required.")

    phone_number = input("Phone number (login, e.g. 9812345001): ").strip()
    if not phone_number:
        sys.exit("Phone number is required.")

    pin = getpass("PIN (4-6 digits, input hidden): ").strip()
    if not PIN_PATTERN.match(pin):
        sys.exit("PIN must be 4-6 digits.")
    if getpass("Confirm PIN: ").strip() != pin:
        sys.exit("PINs didn't match -- nothing was created.")

    whatsapp_number = input(f"WhatsApp number for alerts (blank to reuse {phone_number}): ").strip() or phone_number

    db = SessionLocal()
    try:
        user = User(
            name=name,
            role=UserRole.supervisor,
            phone_number=phone_number,
            whatsapp_number=whatsapp_number,
            pin_hash=hash_secret(pin),
        )
        db.add(user)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            sys.exit(f"Could not create user -- phone number {phone_number} is already in use.")
        db.refresh(user)
        print(f"Created supervisor '{user.name}' (id={user.id}). They can now log in with phone + PIN.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
