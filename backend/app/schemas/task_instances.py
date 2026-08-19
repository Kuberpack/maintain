import uuid
from datetime import date, datetime

from app.models import TaskStatus
from app.schemas.base import CamelModel


class TaskInstanceCreate(CamelModel):
    task_type_id: uuid.UUID
    due_date: date
    notes: str | None = None
    # status is never client-settable: it always starts pending, and only
    # changes via mark-done, reschedule, or the daily overdue job.


class TaskInstanceMarkDone(CamelModel):
    notes: str | None = None
    photo_url: str | None = None


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


class TaskInstanceMarkDoneResponse(CamelModel):
    completed: TaskInstancePublic
    # The auto-generated next occurrence, or None for a non-recurring
    # (e.g. repair) task type -- see app.services.scheduling.
    next: TaskInstancePublic | None
