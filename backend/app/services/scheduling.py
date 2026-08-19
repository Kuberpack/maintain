import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
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


def reopen_task_instance(db: Session, task_instance: TaskInstance) -> TaskInstance:
    """Undo a mark-done -- the inverse of complete_task_instance() above.

    The schema has no explicit link from a completed instance to the next
    occurrence it may have spawned, so this infers it: any other instance of
    the same task_type with a due_date that isn't provably earlier (i.e.
    >=, not >: same-day completions can tie -- e.g. mark done, undo, mark
    done again all in one day yields two occurrences due on the same date).
    If every such instance is still untouched (pending, never completed or
    rescheduled), it only exists because this completion spawned it, so
    it's removed along with the undo. If any of them has been acted on,
    undoing this completion would leave that downstream activity dangling
    with no due-date ancestor, so the whole reopen is refused instead -- the
    caller has to reopen (and thereby unwind) the later ones first.
    """
    if task_instance.status != TaskStatus.done:
        raise HTTPException(status.HTTP_409_CONFLICT, "Task instance is not marked done")

    later_instances = (
        db.query(TaskInstance)
        .filter(
            TaskInstance.task_type_id == task_instance.task_type_id,
            TaskInstance.due_date >= task_instance.due_date,
            TaskInstance.id != task_instance.id,
        )
        .all()
    )
    for later in later_instances:
        if later.status != TaskStatus.pending or later.completed_at is not None or later.rescheduled_by is not None:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Cannot reopen: a later occurrence of this task has already been completed or rescheduled",
            )

    for later in later_instances:
        db.delete(later)

    task_instance.status = TaskStatus.pending
    task_instance.completed_at = None
    task_instance.completed_by = None
    task_instance.notes = None
    task_instance.photo_url = None
    return task_instance
