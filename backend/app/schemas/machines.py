import uuid
from datetime import datetime

from pydantic import Field

from app.schemas.base import CamelModel


class MachineCreate(CamelModel):
    name: str = Field(min_length=1, max_length=255)
    type: str = Field(min_length=1, max_length=100)
    location: str | None = Field(default=None, max_length=255)


class MachineUpdate(CamelModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    type: str | None = Field(default=None, min_length=1, max_length=100)
    location: str | None = None


class MachinePublic(CamelModel):
    id: uuid.UUID
    name: str
    type: str
    location: str | None
    created_at: datetime
