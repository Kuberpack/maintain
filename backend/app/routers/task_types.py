import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_roles
from app.core.utils import commit_or_409, get_or_404
from app.database import get_db
from app.models import ChecklistItem, Machine, TaskCategory, TaskType, UserRole
from app.schemas.checklists import ChecklistItemPublic
from app.schemas.task_types import TaskTypeCreate, TaskTypePublic, TaskTypeUpdate

router = APIRouter(prefix="/task-types", tags=["task_types"])

# Management is explicitly read-only (architecture.md); only supervisor writes.
_write_roles = require_roles(UserRole.supervisor)


@router.get("", response_model=list[TaskTypePublic])
def list_task_types(
    machine_id: uuid.UUID | None = Query(default=None, alias="machineId"),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
) -> list[TaskType]:
    query = db.query(TaskType)
    if machine_id is not None:
        query = query.filter(TaskType.machine_id == machine_id)
    return query.all()


@router.get("/{task_type_id}", response_model=TaskTypePublic)
def get_task_type(
    task_type_id: uuid.UUID, db: Session = Depends(get_db), _user=Depends(get_current_user)
) -> TaskType:
    return get_or_404(db, TaskType, task_type_id, "Task type not found")


@router.get("/{task_type_id}/checklist-items", response_model=list[ChecklistItemPublic])
def list_checklist_items(
    task_type_id: uuid.UUID, db: Session = Depends(get_db), _user=Depends(get_current_user)
) -> list[ChecklistItem]:
    get_or_404(db, TaskType, task_type_id, "Task type not found")
    return (
        db.query(ChecklistItem)
        .filter(ChecklistItem.task_type_id == task_type_id)
        .order_by(ChecklistItem.sort_order)
        .all()
    )


@router.post("", response_model=TaskTypePublic, status_code=201)
def create_task_type(
    payload: TaskTypeCreate, db: Session = Depends(get_db), _user=Depends(_write_roles)
) -> TaskType:
    get_or_404(db, Machine, payload.machine_id, "Machine not found")
    task_type = TaskType(**payload.model_dump())
    db.add(task_type)
    db.commit()
    db.refresh(task_type)
    return task_type


@router.patch("/{task_type_id}", response_model=TaskTypePublic)
def update_task_type(
    task_type_id: uuid.UUID,
    payload: TaskTypeUpdate,
    db: Session = Depends(get_db),
    _user=Depends(_write_roles),
) -> TaskType:
    task_type = get_or_404(db, TaskType, task_type_id, "Task type not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(task_type, field, value)

    if task_type.category == TaskCategory.repair and task_type.default_interval_days is not None:
        db.rollback()
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "defaultIntervalDays must be omitted for repair (event-driven, not scheduled)",
        )
    if task_type.category != TaskCategory.repair and task_type.default_interval_days is None:
        db.rollback()
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "defaultIntervalDays is required for non-repair task types",
        )

    db.commit()
    db.refresh(task_type)
    return task_type


@router.delete("/{task_type_id}", status_code=204)
def delete_task_type(
    task_type_id: uuid.UUID, db: Session = Depends(get_db), _user=Depends(_write_roles)
) -> None:
    task_type = get_or_404(db, TaskType, task_type_id, "Task type not found")
    db.delete(task_type)
    commit_or_409(db, "Cannot delete this task type")
