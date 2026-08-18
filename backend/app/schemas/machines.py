import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MachineCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    type: str = Field(min_length=1, max_length=100)
    location: str | None = Field(default=None, max_length=255)


class MachineUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    type: str | None = Field(default=None, min_length=1, max_length=100)
    location: str | None = None


class MachinePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    type: str
    location: str | None
    created_at: datetime
