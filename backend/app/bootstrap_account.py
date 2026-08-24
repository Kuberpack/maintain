"""One-off bootstrap script: creates a single real admin or supervisor
account so a fresh, empty database (no seed data) has someone who can log
in and start managing everything else -- machines, task types, and other
staff accounts -- through the app itself.

Deliberately separate from seed.py -- this never wipes or touches anything
else in the database, and only ever creates the one account you ask for.

Renamed from create_supervisor.py (its original, PIN-only-supervisor
form) once the admin role was added -- it now bootstraps either PIN-family
role. Management accounts don't need a bootstrap path here: once either an
admin or supervisor account exists, one can create a management account
through the app itself.

Run inside the backend container:
    docker compose exec backend python -m app.bootstrap_account

Or locally (from backend/):
    .venv/bin/python -m app.bootstrap_account

Prompts for role, name, phone number, and PIN interactively -- the PIN
prompt is hidden like a password field -- rather than taking them as
command-line arguments, so the PIN never ends up in shell history or a
process listing.
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

# Only the two PIN-family roles: this script exists to unblock a database
# with literally no login path yet, and either role can bootstrap the rest
# from there (admin can create anyone; supervisor can create operators, and
# any of them can create a management account through the app itself).
BOOTSTRAPPABLE_ROLES = {"admin": UserRole.admin, "supervisor": UserRole.supervisor}


def main() -> None:
    role_input = input(f"Role ({'/'.join(BOOTSTRAPPABLE_ROLES)}): ").strip().lower()
    role = BOOTSTRAPPABLE_ROLES.get(role_input)
    if role is None:
        sys.exit(f"Role must be one of: {', '.join(BOOTSTRAPPABLE_ROLES)}")

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
            role=role,
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
        print(f"Created {role.value} '{user.name}' (id={user.id}). They can now log in with phone + PIN.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
