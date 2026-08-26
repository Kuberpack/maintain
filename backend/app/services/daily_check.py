from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.time import today_local
from app.models import Machine, ReviewStatus, TaskInstance, TaskStatus, User, UserRole
from app.services.alerts import notify_user
from app.services.notifications import supervisors_for_machine


def run_daily_check(db: Session) -> None:
    """Flip newly-overdue task instances to status=overdue, then alert.

    Skips items waiting for supervisor review so a submitted-on-time check
    does not become overdue overnight. Operators get a morning digest of
    leftover work; dedicated supervisors get their units; incharge
    supervisors (no dedicated machines) and admins get the plant-wide view.
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

    management = db.query(User).filter(User.role == UserRole.management).all()

    due_today_or_late = [
        ti
        for ti in pending + overdue
        if ti.id in newly_overdue_ids or (ti.due_date - today).days <= 0
    ]
    if due_today_or_late:
        for user, items in _digest_by_supervisor(db, due_today_or_late).items():
            overdue_count = sum(1 for ti in items if (ti.due_date - today).days < 0)
            today_count = len(items) - overdue_count
            awaiting_n = sum(1 for ti in awaiting if _machine(ti) and _should_alert_supervisor(db, user, _machine(ti)))
            digest = (
                f"{today_count} due today, {overdue_count} overdue, "
                f"{awaiting_n} waiting for review."
            )
            notify_user(user, "Morning maintenance summary", digest)
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
        for user in supervisors_for_machine(db, _machine(instance)):
            notify_user(user, "Task due soon", message)

    for instance in overdue:
        days_overdue = (today - instance.due_date).days
        escalate = days_overdue >= settings.alert_overdue_escalate_days
        subject = f"Task overdue — still open, day {days_overdue}"
        message = _describe(instance, today)
        recipients = list(supervisors_for_machine(db, _machine(instance)))
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
        for user in supervisors_for_machine(db, _machine(instance)):
            notify_user(user, "Unreviewed work is waiting", message)
        if hours >= 24:
            for user in management:
                notify_user(user, "Supervisor has not reviewed work", message)


def _machine(instance: TaskInstance) -> Machine | None:
    task_type = instance.task_type
    if task_type is None:
        return None
    return task_type.machine


def _operator_for_instance(instance: TaskInstance) -> User | None:
    machine = _machine(instance)
    if machine is None:
        return None
    return machine.operator


def _instances_by_operator(instances: list[TaskInstance]) -> dict[User, list[TaskInstance]]:
    grouped: dict[User, list[TaskInstance]] = {}
    for instance in instances:
        operator = _operator_for_instance(instance)
        if operator is None:
            continue
        grouped.setdefault(operator, []).append(instance)
    return grouped


def _incharge_and_admins(db: Session) -> list[User]:
    """Admins plus supervisors who are not dedicated to any machine (Pawan)."""
    dedicated_ids = {
        row[0]
        for row in db.query(Machine.supervisor_id).filter(Machine.supervisor_id.isnot(None)).distinct().all()
    }
    out: list[User] = []
    for user in db.query(User).filter(User.role.in_((UserRole.supervisor, UserRole.admin))).all():
        if user.role == UserRole.admin or user.id not in dedicated_ids:
            out.append(user)
    return out


def _should_alert_supervisor(db: Session, user: User, machine: Machine) -> bool:
    ids = {u.id for u in supervisors_for_machine(db, machine)}
    ids.update(u.id for u in _incharge_and_admins(db))
    return user.id in ids


def _digest_by_supervisor(db: Session, instances: list[TaskInstance]) -> dict[User, list[TaskInstance]]:
    grouped: dict[User, list[TaskInstance]] = {}
    incharge = _incharge_and_admins(db)
    for instance in instances:
        machine = _machine(instance)
        recipients = {u.id: u for u in supervisors_for_machine(db, machine)}
        for user in incharge:
            recipients[user.id] = user
        for user in recipients.values():
            grouped.setdefault(user, []).append(instance)
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
