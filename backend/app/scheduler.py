import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import get_settings
from app.database import SessionLocal
from app.services.daily_check import run_daily_check
from app.services.scheduling import ensure_daily_instances

logger = logging.getLogger("scheduler")

# Single-process assumption: fine for this project's single-container
# deployment model. Running multiple backend workers would start one
# scheduler per worker and duplicate the daily run.
scheduler = BackgroundScheduler()


def _ensure_daily_instances_job() -> None:
    db = SessionLocal()
    try:
        created = ensure_daily_instances(db)
        logger.info("Created %d daily task instance(s) for today", len(created))
    except Exception:
        logger.exception("Creating today's daily task instances failed")
    finally:
        db.close()


def catch_up_daily_instances() -> None:
    """Same work as the 08:00 job, run once at boot. A deploy or restart later
    in the day shouldn't cost operators their daily checks."""
    _ensure_daily_instances_job()


def _run_daily_check_job() -> None:
    db = SessionLocal()
    try:
        run_daily_check(db)
    except Exception:
        logger.exception("Daily status check failed")
    finally:
        db.close()


def start_scheduler() -> None:
    settings = get_settings()
    # 08:00 -- put today's work on every operator's screen. Runs before the
    # alert job so the 08:30 message counts today's newly created tasks.
    scheduler.add_job(
        _ensure_daily_instances_job,
        CronTrigger(
            hour=settings.daily_task_hour,
            minute=settings.daily_task_minute,
            timezone=settings.local_timezone,
        ),
        id="ensure_daily_instances",
        replace_existing=True,
    )
    # 08:30 -- flip overdue, then alert operators and supervisors.
    scheduler.add_job(
        _run_daily_check_job,
        CronTrigger(
            hour=settings.daily_check_hour,
            minute=settings.daily_check_minute,
            timezone=settings.local_timezone,
        ),
        id="daily_status_check",
        replace_existing=True,
    )
    scheduler.start()


def stop_scheduler() -> None:
    scheduler.shutdown(wait=False)
