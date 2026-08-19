from datetime import date

from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.time import today_local
from app.models import TaskInstance, TaskStatus, User, UserRole
from app.services.alerts import notify_user


def run_daily_check(db: Session) -> None:
    """Flip newly-overdue task instances to status=overdue, then alert:
    upcoming items -> supervisors; overdue items -> supervisors, escalating
    to management once alert_overdue_escalate_days have passed.

    Runs once a day. Every currently-upcoming/overdue item is included on
    every run -- there's no per-item de-dup or "already alerted" tracking,
    so a still-overdue item gets re-alerted daily until resolved (that's
    the point of "escalation"), but that also means no rate-limiting once
    a real provider replaces the stub. Fine for a stub; worth revisiting
    once repetition has a real-world cost.
    """
    settings = get_settings()
    today = today_local()

    pending = db.query(TaskInstance).filter(TaskInstance.status == TaskStatus.pending).all()

    newly_overdue_ids: set = set()
    for instance in pending:
        if (instance.due_date - today).days < 0:
            instance.status = TaskStatus.overdue
            newly_overdue_ids.add(instance.id)
    db.commit()

    upcoming = [
        ti
        for ti in pending
        if ti.id not in newly_overdue_ids and 0 <= (ti.due_date - today).days <= settings.alert_upcoming_days
    ]
    overdue = db.query(TaskInstance).filter(TaskInstance.status == TaskStatus.overdue).all()

    if not upcoming and not overdue:
        return

    supervisors = db.query(User).filter(User.role == UserRole.supervisor).all()
    management = db.query(User).filter(User.role == UserRole.management).all()

    for instance in upcoming:
        message = _describe(instance, today)
        for user in supervisors:
            notify_user(user, "Task due soon", message)

    for instance in overdue:
        days_overdue = (today - instance.due_date).days
        escalate = days_overdue >= settings.alert_overdue_escalate_days
        subject = "Task overdue (escalated)" if escalate else "Task overdue"
        message = _describe(instance, today)
        for user in supervisors + (management if escalate else []):
            notify_user(user, subject, message)


def _describe(instance: TaskInstance, today: date) -> str:
    task_type = instance.task_type
    machine = task_type.machine
    days = (instance.due_date - today).days
    if days < 0:
        timing = f"{-days}d overdue"
    elif days == 0:
        timing = "due today"
    else:
        timing = f"due in {days}d"
    return f"{machine.name}: {task_type.description} ({timing}, due {instance.due_date})"
