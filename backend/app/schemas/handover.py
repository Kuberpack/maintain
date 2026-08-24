import uuid
from datetime import datetime

from pydantic import Field

from app.schemas.base import CamelModel


class HandoverNoteCreate(CamelModel):
    machine_id: uuid.UUID
    note: str = Field(min_length=1)


class HandoverNotePublic(CamelModel):
    id: uuid.UUID
    machine_id: uuid.UUID
    note: str
    created_by: uuid.UUID | None
    created_at: datetime
