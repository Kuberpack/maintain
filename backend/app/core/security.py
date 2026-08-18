import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from pydantic import BaseModel

from app.config import get_settings
from app.models import UserRole

settings = get_settings()


def hash_secret(secret: str) -> str:
    """Hash a PIN or password. Same mechanism for both -- bcrypt doesn't
    care which, only that operator/supervisor use it for pin_hash and
    management uses it for password_hash."""
    return bcrypt.hashpw(secret.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_secret(secret: str, hashed: str) -> bool:
    return bcrypt.checkpw(secret.encode("utf-8"), hashed.encode("utf-8"))


class TokenPayload(BaseModel):
    user_id: uuid.UUID
    role: UserRole


def create_access_token(user_id: uuid.UUID, role: UserRole) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "role": role.value,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expires_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> TokenPayload:
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    return TokenPayload(user_id=uuid.UUID(payload["sub"]), role=UserRole(payload["role"]))
