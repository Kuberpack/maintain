import uuid
from datetime import date

from pydantic import Field

from app.schemas.base import CamelModel
from app.schemas.removed_parts import RemovedPartCapture, RemovedPartPublic


class PartReplacementCreate(CamelModel):
    machine_id: uuid.UUID
    part_name: str = Field(min_length=1, max_length=255)
    replaced_at: date
    notes: str | None = None
    # Optional stock draw. Omitted (or null) keeps the old free-text log and
    # does not change inventory. quantity_used defaults to 1 when a spare is set.
    spare_part_id: uuid.UUID | None = None
    quantity_used: int | None = Field(default=None, ge=1)
    # The old part that came off. Omitted still opens a pending trail so every
    # new replacement is traceable. Older rows logged before this field stay null.
    removed: RemovedPartCapture | None = None


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
    removed_part: RemovedPartPublic | None = None
