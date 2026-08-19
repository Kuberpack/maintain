import uuid
from datetime import datetime

from pydantic import Field

from app.schemas.base import CamelModel


class RepairLogCreate(CamelModel):
    machine_id: uuid.UUID
    issue_description: str = Field(min_length=1)
    downtime_minutes: int | None = Field(default=None, ge=0)


class RepairLogResolve(CamelModel):
    resolution_notes: str | None = None


class RepairLogPublic(CamelModel):
    id: uuid.UUID
    machine_id: uuid.UUID
    reported_at: datetime
    reported_by: uuid.UUID | None
    issue_description: str
    downtime_minutes: int | None
    resolved_at: datetime | None
    resolved_by: uuid.UUID | None
    resolution_notes: str | None
