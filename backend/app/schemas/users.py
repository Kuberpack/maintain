import uuid
from datetime import datetime

from pydantic import Field, model_validator

from app.models import UserAuditAction, UserRole
from app.schemas.base import CamelModel


class UserCreate(CamelModel):
    name: str = Field(min_length=1, max_length=255)
    role: UserRole
    email: str | None = None
    phone_number: str | None = None
    whatsapp_number: str | None = None
    pin: str | None = Field(default=None, pattern=r"^\d{4,6}$")
    password: str | None = Field(default=None, min_length=8)

    @model_validator(mode="after")
    def _check_credential_matches_role(self) -> "UserCreate":
        if self.role == UserRole.management:
            if not self.password:
                raise ValueError("password is required for management users")
            if self.pin:
                raise ValueError("management users log in with a password, not a PIN")
            if not self.email:
                raise ValueError("email is required for management users")
        else:
            if not self.pin:
                raise ValueError("pin is required for operator/supervisor users")
            if self.password:
                raise ValueError("operator/supervisor users log in with a PIN, not a password")
            if not self.phone_number:
                raise ValueError("phone_number is required for operator/supervisor users")
        return self


class UserUpdate(CamelModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    role: UserRole | None = None
    email: str | None = None
    phone_number: str | None = None
    whatsapp_number: str | None = None
    pin: str | None = Field(default=None, pattern=r"^\d{4,6}$")
    password: str | None = Field(default=None, min_length=8)
    # Role/credential consistency is re-checked in the router after merging
    # with the existing row (a PATCH may only touch one of role/pin/password).


class UserPublic(CamelModel):
    id: uuid.UUID
    name: str
    role: UserRole
    email: str | None
    phone_number: str | None
    whatsapp_number: str | None
    created_at: datetime
    created_by_id: uuid.UUID | None


class UserAuditEventPublic(CamelModel):
    id: uuid.UUID
    action: UserAuditAction
    actor_id: uuid.UUID | None
    actor_name: str
    actor_role: UserRole
    target_user_id: uuid.UUID | None
    target_name: str
    target_role: UserRole
    at: datetime
