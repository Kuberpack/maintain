import uuid
from datetime import date

from pydantic import Field

from app.schemas.base import CamelModel


class PartReplacementCreate(CamelModel):
    machine_id: uuid.UUID
    part_name: str = Field(min_length=1, max_length=255)
    replaced_at: date
    notes: str | None = None
    # Optional stock draw. Omitted (or null) keeps the old free-text log and
    # does not change inventory. quantity_used defaults to 1 when a spare is set.
    spare_part_id: uuid.UUID | None = None
    quantity_used: int | None = Field(default=None, ge=1)


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
    spare_part_id: uuid.UUID | None
    quantity_used: int | None
