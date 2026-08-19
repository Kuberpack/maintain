import uuid
from datetime import date

from pydantic import Field

from app.schemas.base import CamelModel


class PartReplacementCreate(CamelModel):
    machine_id: uuid.UUID
    part_name: str = Field(min_length=1, max_length=255)
    replaced_at: date
    notes: str | None = None


class PartReplacementUpdate(CamelModel):
    part_name: str | None = Field(default=None, min_length=1, max_length=255)
    replaced_at: date | None = None
    notes: str | None = None


class PartReplacementPublic(CamelModel):
    id: uuid.UUID
    machine_id: uuid.UUID
    part_name: str
    replaced_at: date
    replaced_by: uuid.UUID | None
    notes: str | None
