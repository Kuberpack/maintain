import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_roles
from app.core.utils import commit_or_409, get_or_404
from app.database import get_db
from app.models import ChecklistItemResult, TaskInstance, TaskStatus, TaskType, User, UserRole
from app.schemas.checklists import ChecklistItemResultPublic
from app.schemas.task_instances import (
    TaskInstanceCreate,
    TaskInstanceMarkDone,
    TaskInstanceMarkDoneResponse,
    TaskInstancePublic,
    TaskInstanceReschedule,
)
from app.services.scheduling import complete_task_instance
from app.services.scheduling import reopen_task_instance as reopen_task_instance_service

router = APIRouter(prefix="/task-instances", tags=["task_instances"])

# Doing the work (mark-done) is operator+supervisor; managing the schedule
# (manual create, reschedule) is supervisor only; management is read-only.
_do_work_roles = require_roles(UserRole.operator, UserRole.supervisor)
_manage_roles = require_roles(UserRole.supervisor)


@router.get("", response_model=list[TaskInstancePublic])
def list_task_instances(
    machine_id: uuid.UUID | None = Query(default=None, alias="machineId"),
    status: TaskStatus | None = None,
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
) -> list[TaskInstance]:
    query = db.query(TaskInstance)
    if machine_id is not None:
        query = query.join(TaskType).filter(TaskType.machine_id == machine_id)
    if status is not None:
        query = query.filter(TaskInstance.status == status)
    return query.order_by(TaskInstance.due_date).all()


@router.get("/{task_instance_id}", response_model=TaskInstancePublic)
def get_task_instance(
    task_instance_id: uuid.UUID, db: Session = Depends(get_db), _user=Depends(get_current_user)
) -> TaskInstance:
    return get_or_404(db, TaskInstance, task_instance_id, "Task instance not found")


@router.get("/{task_instance_id}/checklist-results", response_model=list[ChecklistItemResultPublic])
def list_task_instance_checklist_results(
    task_instance_id: uuid.UUID, db: Session = Depends(get_db), _user=Depends(get_current_user)
) -> list[ChecklistItemResult]:
    get_or_404(db, TaskInstance, task_instance_id, "Task instance not found")
    return (
        db.query(ChecklistItemResult)
        .filter(ChecklistItemResult.task_instance_id == task_instance_id)
        .all()
    )


@router.post("", response_model=TaskInstancePublic, status_code=201)
def create_task_instance(
    payload: TaskInstanceCreate, db: Session = Depends(get_db), _user=Depends(_manage_roles)
) -> TaskInstance:
    get_or_404(db, TaskType, payload.task_type_id, "Task type not found")
    task_instance = TaskInstance(**payload.model_dump())
    db.add(task_instance)
    db.commit()
    db.refresh(task_instance)
    return task_instance


@router.patch("/{task_instance_id}/mark-done", response_model=TaskInstanceMarkDoneResponse)
def mark_task_instance_done(
    task_instance_id: uuid.UUID,
    payload: TaskInstanceMarkDone,
    db: Session = Depends(get_db),
    current_user: User = Depends(_do_work_roles),
) -> TaskInstanceMarkDoneResponse:
    task_instance = get_or_404(db, TaskInstance, task_instance_id, "Task instance not found")
    next_instance = complete_task_instance(
        db,
        task_instance,
        current_user.id,
        notes=payload.notes,
        photo_url=payload.photo_url,
        results=payload.results,
    )
    db.commit()
    db.refresh(task_instance)
    if next_instance is not None:
        db.refresh(next_instance)
    return TaskInstanceMarkDoneResponse(completed=task_instance, next=next_instance)


@router.patch("/{task_instance_id}/reopen", response_model=TaskInstancePublic)
def reopen_task_instance(
    task_instance_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(_do_work_roles),
) -> TaskInstance:
    task_instance = get_or_404(db, TaskInstance, task_instance_id, "Task instance not found")
    reopen_task_instance_service(db, task_instance)
    db.commit()
    db.refresh(task_instance)
    return task_instance


@router.patch("/{task_instance_id}/reschedule", response_model=TaskInstancePublic)
def reschedule_task_instance(
    task_instance_id: uuid.UUID,
    payload: TaskInstanceReschedule,
    db: Session = Depends(get_db),
    current_user: User = Depends(_manage_roles),
) -> TaskInstance:
    task_instance = get_or_404(db, TaskInstance, task_instance_id, "Task instance not found")
    task_instance.due_date = payload.due_date
    task_instance.rescheduled_by = current_user.id
    task_instance.status = TaskStatus.pending
    if payload.notes is not None:
        task_instance.notes = payload.notes
    db.commit()
    db.refresh(task_instance)
    return task_instance


@router.delete("/{task_instance_id}", status_code=204)
def delete_task_instance(
    task_instance_id: uuid.UUID, db: Session = Depends(get_db), _user=Depends(_manage_roles)
) -> None:
    task_instance = get_or_404(db, TaskInstance, task_instance_id, "Task instance not found")
    db.delete(task_instance)
    commit_or_409(db, "Cannot delete this task instance")
