import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.models import TaskStatus


class TaskInstanceCreate(BaseModel):
    task_type_id: uuid.UUID
    due_date: date
    notes: str | None = None
    # status is never client-settable: it always starts pending, and only
    # changes via mark-done, reschedule, or the daily overdue job.


class TaskInstanceMarkDone(BaseModel):
    notes: str | None = None
    photo_url: str | None = None


class TaskInstanceReschedule(BaseModel):
    due_date: date
    notes: str | None = None


class TaskInstancePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    task_type_id: uuid.UUID
    due_date: date
    status: TaskStatus
    completed_at: datetime | None
    completed_by: uuid.UUID | None
    notes: str | None
    rescheduled_by: uuid.UUID | None
    photo_url: str | None


class TaskInstanceMarkDoneResponse(BaseModel):
    completed: TaskInstancePublic
    # The auto-generated next occurrence, or None for a non-recurring
    # (e.g. repair) task type -- see app.services.scheduling.
    next: TaskInstancePublic | None
