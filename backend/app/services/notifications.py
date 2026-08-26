"""Immediate (not daily) alerts for submit / reject / repair."""

import uuid
from sqlalchemy.orm import Session

from app.models import ExceptionLevel, TaskInstance, User, UserRole
from app.services.alerts import notify_user


def _supervisors(db: Session) -> list[User]:
    return db.query(User).filter(User.role.in_((UserRole.supervisor, UserRole.admin))).all()


def _operators(db: Session) -> list[User]:
    return db.query(User).filter(User.role == UserRole.operator).all()


def _describe_task(instance: TaskInstance) -> str:
    task_type = instance.task_type
    machine = task_type.machine
    return f"{machine.name}: {task_type.description}"


def notify_submission(db: Session, instance: TaskInstance) -> None:
    label = _describe_task(instance)
    if instance.exception_level == ExceptionLevel.critical:
        subject = "Critical check — review now"
        message = f"CRITICAL on {label}. Open Review in the dashboard."
    elif instance.exception_level == ExceptionLevel.attention:
        subject = "Attention check — waiting for review"
        message = f"Attention flagged on {label}. Waiting for your review."
    else:
        subject = "Work waiting for review"
        message = f"{label} was submitted and is waiting for review."
    for user in _supervisors(db):
        notify_user(user, subject, message)


def notify_rejection(db: Session, instance: TaskInstance, operator_id: uuid.UUID | None) -> None:
    label = _describe_task(instance)
    reason = instance.review_notes or "redo this check"
    message = f"Supervisor rejected {label}. Reason: {reason}"
    user = db.get(User, operator_id) if operator_id is not None else None
    if user is not None:
        notify_user(user, "Check rejected — please redo", message)
        return
    for operator in _operators(db):
        notify_user(operator, "Check rejected — please redo", message)


def notify_new_repair(
    db: Session,
    machine_name: str,
    issue: str,
    impact: str | None = None,
    reported_by_name: str | None = None,
) -> None:
    parts = [f"New repair on {machine_name}: {issue}"]
    if impact:
        parts.append(f"Will cause: {impact}")
    if reported_by_name:
        parts.append(f"Reported by {reported_by_name}")
    message = ". ".join(parts)
    for user in _supervisors(db):
        notify_user(user, "New repair reported", message)


def notify_part_replacement(
    db: Session,
    machine_name: str,
    part_name: str,
    replaced_by_name: str | None = None,
    notes: str | None = None,
) -> None:
    """Operators log part swaps themselves, so the supervisor finds out from
    this message rather than from being asked for permission first."""
    parts = [f"Part replaced on {machine_name}: {part_name}"]
    if notes:
        parts.append(notes)
    if replaced_by_name:
        parts.append(f"Logged by {replaced_by_name}")
    message = ". ".join(parts)
    for user in _supervisors(db):
        notify_user(user, "Part replacement logged", message)
