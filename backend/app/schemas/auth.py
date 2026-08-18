import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.models import UserRole


class PinLoginRequest(BaseModel):
    phone_number: str
    pin: str = Field(pattern=r"^\d{4,6}$")


class PasswordLoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=1)


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    role: UserRole
    email: str | None = None
    phone_number: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic
