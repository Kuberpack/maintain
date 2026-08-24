import uuid
from datetime import date, datetime

from pydantic import Field

from app.models import ExceptionLevel, ReviewStatus, TaskStatus
from app.schemas.base import CamelModel
from app.schemas.checklists import ChecklistItemResultInput, ChecklistItemResultPublic


class TaskInstanceCreate(CamelModel):
    task_type_id: uuid.UUID
    due_date: date
    notes: str | None = None
    # status is never client-settable: it always starts pending, and only
    # changes via mark-done, reschedule, approve, or the daily overdue job.


class TaskInstanceMarkDone(CamelModel):
    notes: str | None = None
    photo_url: str | None = None
    exception_photo_url: str | None = None
    started_at: datetime | None = None
    results: list[ChecklistItemResultInput] | None = None


class TaskInstanceReject(CamelModel):
    notes: str = Field(min_length=1)


class TaskInstanceReschedule(CamelModel):
    due_date: date
    notes: str | None = None


class TaskInstancePublic(CamelModel):
    id: uuid.UUID
    task_type_id: uuid.UUID
    due_date: date
    status: TaskStatus
    completed_at: datetime | None
    completed_by: uuid.UUID | None
    notes: str | None
    rescheduled_by: uuid.UUID | None
    photo_url: str | None
    exception_photo_url: str | None
    started_at: datetime | None
    duration_seconds: int | None
    is_fast_submit: bool
    review_status: ReviewStatus
    reviewed_by: uuid.UUID | None
    reviewed_at: datetime | None
    review_notes: str | None
    exception_level: ExceptionLevel


class TaskInstanceMarkDoneResponse(CamelModel):
    completed: TaskInstancePublic
    # The auto-generated next occurrence, or None until a supervisor
    # approves (submit no longer spawns the next row).
    next: TaskInstancePublic | None
