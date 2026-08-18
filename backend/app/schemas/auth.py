from pydantic import BaseModel, Field

from app.schemas.users import UserPublic


class PinLoginRequest(BaseModel):
    phone_number: str
    pin: str = Field(pattern=r"^\d{4,6}$")


class PasswordLoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic
