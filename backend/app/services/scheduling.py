import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.time import today_local
from app.models import TaskInstance, TaskStatus


def complete_task_instance(
    db: Session,
    task_instance: TaskInstance,
    completed_by: uuid.UUID,
    notes: str | None = None,
    photo_url: str | None = None,
) -> TaskInstance | None:
    """Mark a task instance done and, for recurring task types, create the
    next occurrence. This is the single place in the app that computes a
    next due_date -- nothing else creates a follow-on task_instance.

    The next due_date is computed from the completion date, not the original
    due_date: a late cleaning doesn't compound the lateness of every future
    occurrence, it just restarts the interval from when the work actually
    happened (matches architecture.md: "resets the next-due date").

    Returns the newly created next TaskInstance, or None if this task type
    isn't recurring (e.g. repair, which is event-driven per schema.md).
    """
    now = datetime.now(timezone.utc)
    task_instance.status = TaskStatus.done
    task_instance.completed_at = now
    task_instance.completed_by = completed_by
    if notes is not None:
        task_instance.notes = notes
    if photo_url is not None:
        task_instance.photo_url = photo_url

    interval_days = task_instance.task_type.default_interval_days
    if interval_days is None:
        return None

    next_instance = TaskInstance(
        task_type_id=task_instance.task_type_id,
        due_date=today_local() + timedelta(days=interval_days),
        status=TaskStatus.pending,
    )
    db.add(next_instance)
    return next_instance
