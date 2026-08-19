from pydantic import Field

from app.schemas.base import CamelModel
from app.schemas.users import UserPublic


class PinLoginRequest(CamelModel):
    phone_number: str
    pin: str = Field(pattern=r"^\d{4,6}$")


class PasswordLoginRequest(CamelModel):
    email: str
    password: str = Field(min_length=1)


class TokenResponse(CamelModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic
