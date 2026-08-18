import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class PartReplacementCreate(BaseModel):
    machine_id: uuid.UUID
    part_name: str = Field(min_length=1, max_length=255)
    replaced_at: date
    notes: str | None = None


class PartReplacementUpdate(BaseModel):
    part_name: str | None = Field(default=None, min_length=1, max_length=255)
    replaced_at: date | None = None
    notes: str | None = None


class PartReplacementPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    machine_id: uuid.UUID
    part_name: str
    replaced_at: date
    replaced_by: uuid.UUID | None
    notes: str | None
