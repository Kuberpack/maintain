import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.time import today_local
from app.models import (
    ChecklistItem,
    ChecklistItemResult,
    ChecklistItemStatus,
    ExceptionLevel,
    ReviewStatus,
    TaskInstance,
    TaskStatus,
)
from app.schemas.checklists import ChecklistItemResultInput

FAST_SUBMIT_SECONDS = 180
FAST_SUBMIT_MIN_ITEMS = 10


def apply_checklist_results(
    db: Session,
    task_instance: TaskInstance,
    results: list[ChecklistItemResultInput] | None,
) -> list[ChecklistItemResult]:
    """Require a result for every checklist item on the task type, if any exist.

    Out-of-range numeric readings are bumped to at least attention so a fake
    "everything OK" with impossible numbers still shows as an exception.
    """
    items = (
        db.query(ChecklistItem)
        .filter(ChecklistItem.task_type_id == task_instance.task_type_id)
        .order_by(ChecklistItem.sort_order)
        .all()
    )
    if not items:
        return []

    if not results:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Checklist results are required for this preventive task",
        )

    items_by_id = {item.id: item for item in items}
    seen: set[uuid.UUID] = set()
    stored: list[ChecklistItemResult] = []
    for result in results:
        if result.checklist_item_id in seen:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "Duplicate checklist item result",
            )
        seen.add(result.checklist_item_id)
        item = items_by_id.get(result.checklist_item_id)
        if item is None:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "Checklist result does not belong to this task type",
            )
        if item.requires_value and result.numeric_value is None:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                f"A numeric reading is required: {item.description}",
            )
        item_status = _status_for_range(item, result)
        stored.append(
            ChecklistItemResult(
                task_instance_id=task_instance.id,
                checklist_item_id=result.checklist_item_id,
                item_status=item_status,
                numeric_value=result.numeric_value,
                notes=result.notes,
            )
        )

    missing = [item.description for item in items if item.id not in seen]
    if missing:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Every checklist item needs a status before this task can be marked done",
        )

    db.query(ChecklistItemResult).filter(ChecklistItemResult.task_instance_id == task_instance.id).delete(
        synchronize_session=False
    )
    for row in stored:
        db.add(row)
    return stored


def _status_for_range(item: ChecklistItem, result: ChecklistItemResultInput) -> ChecklistItemStatus:
    item_status = result.item_status
    if result.numeric_value is None:
        return item_status
    if item.min_value is None and item.max_value is None:
        return item_status
    out_of_range = False
    if item.min_value is not None and result.numeric_value < item.min_value:
        out_of_range = True
    if item.max_value is not None and result.numeric_value > item.max_value:
        out_of_range = True
    if not out_of_range:
        return item_status
    if item_status == ChecklistItemStatus.critical:
        return ChecklistItemStatus.critical
    return ChecklistItemStatus.attention


def _exception_level(results: list[ChecklistItemResult]) -> ExceptionLevel:
    if any(r.item_status == ChecklistItemStatus.critical for r in results):
        return ExceptionLevel.critical
    if any(r.item_status == ChecklistItemStatus.attention for r in results):
        return ExceptionLevel.attention
    return ExceptionLevel.none


def _clear_submission(db: Session, task_instance: TaskInstance) -> None:
    db.query(ChecklistItemResult).filter(ChecklistItemResult.task_instance_id == task_instance.id).delete(
        synchronize_session=False
    )
    task_instance.completed_at = None
    task_instance.completed_by = None
    task_instance.notes = None
    task_instance.photo_url = None
    task_instance.exception_photo_url = None
    task_instance.started_at = None
    task_instance.duration_seconds = None
    task_instance.is_fast_submit = False
    task_instance.exception_level = ExceptionLevel.none


def _restore_schedule_status(task_instance: TaskInstance) -> None:
    if task_instance.due_date < today_local():
        task_instance.status = TaskStatus.overdue
    else:
        task_instance.status = TaskStatus.pending


def submit_task_instance(
    db: Session,
    task_instance: TaskInstance,
    completed_by: uuid.UUID,
    notes: str | None = None,
    photo_url: str | None = None,
    exception_photo_url: str | None = None,
    started_at: datetime | None = None,
    results: list[ChecklistItemResultInput] | None = None,
) -> TaskInstance:
    """Operator submits work for supervisor review. Does not mark the task
    done and does not spawn the next occurrence — that happens on approve.
    """
    if task_instance.status == TaskStatus.done:
        raise HTTPException(status.HTTP_409_CONFLICT, "Task instance is already approved")
    if task_instance.review_status == ReviewStatus.awaiting_review:
        raise HTTPException(status.HTTP_409_CONFLICT, "Already waiting for supervisor review")

    if not photo_url:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "A photo of the machine is required",
        )

    stored = apply_checklist_results(db, task_instance, results)
    level = _exception_level(stored)
    if level != ExceptionLevel.none and not exception_photo_url:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "A second photo is required because something was marked Attention or Critical",
        )

    now = datetime.now(timezone.utc)
    duration: int | None = None
    is_fast = False
    if started_at is not None:
        started = started_at if started_at.tzinfo else started_at.replace(tzinfo=timezone.utc)
        duration = max(0, int((now - started).total_seconds()))
        is_fast = duration < FAST_SUBMIT_SECONDS and len(stored) >= FAST_SUBMIT_MIN_ITEMS

    task_instance.completed_at = now
    task_instance.completed_by = completed_by
    if notes is not None:
        task_instance.notes = notes
    task_instance.photo_url = photo_url
    task_instance.exception_photo_url = exception_photo_url
    task_instance.started_at = started_at
    task_instance.duration_seconds = duration
    task_instance.is_fast_submit = is_fast
    task_instance.review_status = ReviewStatus.awaiting_review
    task_instance.reviewed_by = None
    task_instance.reviewed_at = None
    task_instance.review_notes = None
    task_instance.exception_level = level
    return task_instance


def approve_task_instance(
    db: Session,
    task_instance: TaskInstance,
    reviewed_by: uuid.UUID,
) -> TaskInstance | None:
    """Supervisor accepts the submission. Marks done and, for recurring
    types, creates the next occurrence from today's local date.
    """
    if task_instance.review_status != ReviewStatus.awaiting_review:
        raise HTTPException(status.HTTP_409_CONFLICT, "Task instance is not waiting for review")

    now = datetime.now(timezone.utc)
    task_instance.status = TaskStatus.done
    task_instance.review_status = ReviewStatus.approved
    task_instance.reviewed_by = reviewed_by
    task_instance.reviewed_at = now
    task_instance.review_notes = None

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


def reject_task_instance(
    db: Session,
    task_instance: TaskInstance,
    reviewed_by: uuid.UUID,
    notes: str,
) -> TaskInstance:
    """Send the work back. Clears proof and checklist so the operator must
    redo it; keeps the reject reason visible until they submit again.
    """
    if task_instance.review_status != ReviewStatus.awaiting_review:
        raise HTTPException(status.HTTP_409_CONFLICT, "Task instance is not waiting for review")

    _clear_submission(db, task_instance)
    _restore_schedule_status(task_instance)
    task_instance.review_status = ReviewStatus.rejected
    task_instance.reviewed_by = reviewed_by
    task_instance.reviewed_at = datetime.now(timezone.utc)
    task_instance.review_notes = notes
    return task_instance


def reopen_task_instance(db: Session, task_instance: TaskInstance) -> TaskInstance:
    """Undo an approved completion — the inverse of approve_task_instance().

    The schema has no explicit link from a completed instance to the next
    occurrence it may have spawned, so this infers it: any other instance of
    the same task_type with a due_date that isn't provably earlier (i.e.
    >=, not >: same-day completions can tie). If every such instance is still
    untouched, it only exists because this approval spawned it, so it's
    removed. If any of them has been acted on, the reopen is refused.
    """
    if task_instance.status != TaskStatus.done or task_instance.review_status != ReviewStatus.approved:
        raise HTTPException(status.HTTP_409_CONFLICT, "Task instance is not approved")

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

    _clear_submission(db, task_instance)
    _restore_schedule_status(task_instance)
    task_instance.review_status = ReviewStatus.none
    task_instance.reviewed_by = None
    task_instance.reviewed_at = None
    task_instance.review_notes = None
    return task_instance
