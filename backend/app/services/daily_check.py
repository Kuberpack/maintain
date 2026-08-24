from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.time import today_local
from app.models import ReviewStatus, TaskInstance, TaskStatus, User, UserRole
from app.services.alerts import notify_user


def run_daily_check(db: Session) -> None:
    """Flip newly-overdue task instances to status=overdue, then alert.

    Skips items waiting for supervisor review so a submitted-on-time check
    does not become overdue overnight. Operators get a morning digest of
    leftover work; supervisors get upcoming/overdue plus stale reviews.
    """
    settings = get_settings()
    today = today_local()

    pending = (
        db.query(TaskInstance)
        .filter(
            TaskInstance.status == TaskStatus.pending,
            TaskInstance.review_status != ReviewStatus.awaiting_review,
        )
        .all()
    )

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
    overdue = (
        db.query(TaskInstance)
        .filter(
            TaskInstance.status == TaskStatus.overdue,
            TaskInstance.review_status != ReviewStatus.awaiting_review,
        )
        .all()
    )
    awaiting = db.query(TaskInstance).filter(TaskInstance.review_status == ReviewStatus.awaiting_review).all()

    supervisors = db.query(User).filter(User.role.in_((UserRole.supervisor, UserRole.admin))).all()
    management = db.query(User).filter(User.role == UserRole.management).all()

    due_today_or_late = [
        ti
        for ti in pending + overdue
        if ti.id in newly_overdue_ids or (ti.due_date - today).days <= 0
    ]
    if due_today_or_late:
        overdue_count = sum(1 for ti in due_today_or_late if (ti.due_date - today).days < 0)
        today_count = len(due_today_or_late) - overdue_count
        supervisor_digest = (
            f"{today_count} due today, {overdue_count} overdue, "
            f"{len(awaiting)} waiting for review."
        )
        for user in supervisors:
            notify_user(user, "Morning maintenance summary", supervisor_digest)
        for user, items in _instances_by_operator(due_today_or_late).items():
            late_n = sum(1 for ti in items if (ti.due_date - today).days < 0)
            today_n = len(items) - late_n
            digest = (
                f"Aaj ka kaam: {today_n} due today, {late_n} overdue. "
                "Open the dashboard and finish leftover checks."
            )
            notify_user(user, "Today's machine checks", digest)

    for instance in upcoming:
        message = _describe(instance, today)
        for user in supervisors:
            notify_user(user, "Task due soon", message)

    for instance in overdue:
        days_overdue = (today - instance.due_date).days
        escalate = days_overdue >= settings.alert_overdue_escalate_days
        subject = f"Task overdue — still open, day {days_overdue}"
        message = _describe(instance, today)
        recipients = list(supervisors)
        assigned = _operator_for_instance(instance)
        if assigned is not None:
            recipients.append(assigned)
        if escalate:
            recipients.extend(management)
        for user in recipients:
            notify_user(user, subject, message)

    stale_after = timedelta(hours=settings.alert_unreviewed_hours)
    now = datetime.now(timezone.utc)
    for instance in awaiting:
        submitted = instance.completed_at
        if submitted is None:
            continue
        if submitted.tzinfo is None:
            submitted = submitted.replace(tzinfo=timezone.utc)
        if now - submitted < stale_after:
            continue
        hours = int((now - submitted).total_seconds() // 3600)
        message = f"{_describe(instance, today)} — submitted {hours}h ago, still unreviewed."
        for user in supervisors:
            notify_user(user, "Unreviewed work is waiting", message)
        if hours >= 24:
            for user in management:
                notify_user(user, "Supervisor has not reviewed work", message)


def _operator_for_instance(instance: TaskInstance) -> User | None:
    machine = instance.task_type.machine
    return machine.operator


def _instances_by_operator(instances: list[TaskInstance]) -> dict[User, list[TaskInstance]]:
    grouped: dict[User, list[TaskInstance]] = {}
    for instance in instances:
        operator = _operator_for_instance(instance)
        if operator is None:
            continue
        grouped.setdefault(operator, []).append(instance)
    return grouped


def _describe(instance: TaskInstance, today: date) -> str:
    task_type = instance.task_type
    machine = task_type.machine
    days = (instance.due_date - today).days
    if days < 0:
        timing = f"{-days}d overdue (still open, day {-days})"
    elif days == 0:
        timing = "due today"
    else:
        timing = f"due in {days}d"
    return f"{machine.name}: {task_type.description} ({timing}, due {instance.due_date})"
