import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import Machine, TaskInstance, TaskType, User, UserRole


def assigned_machine(db: Session, user: User) -> Machine | None:
    if user.role != UserRole.operator:
        return None
    return db.query(Machine).filter(Machine.operator_id == user.id).one_or_none()


def require_machine_access(db: Session, user: User, machine_id: uuid.UUID) -> Machine:
    machine = db.get(Machine, machine_id)
    if machine is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Machine not found")
    if user.role == UserRole.operator and machine.operator_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This machine is assigned to another operator")
    return machine


def require_task_type_access(db: Session, user: User, task_type: TaskType) -> None:
    require_machine_access(db, user, task_type.machine_id)


def require_task_instance_access(db: Session, user: User, instance: TaskInstance) -> None:
    task_type = instance.task_type
    if task_type is None:
        task_type = db.get(TaskType, instance.task_type_id)
    if task_type is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task type not found")
    require_machine_access(db, user, task_type.machine_id)


def validate_operator_id(db: Session, operator_id: uuid.UUID | None) -> None:
    if operator_id is None:
        return
    user = db.get(User, operator_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Operator not found")
    if user.role != UserRole.operator:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Assigned user must be an operator")
