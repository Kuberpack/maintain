import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import get_settings
from app.database import SessionLocal
from app.services.daily_check import run_daily_check

logger = logging.getLogger("scheduler")

# Single-process assumption: fine for this project's single-container
# deployment model. Running multiple backend workers would start one
# scheduler per worker and duplicate the daily run.
scheduler = BackgroundScheduler()


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
    scheduler.add_job(
        _run_daily_check_job,
        CronTrigger(hour=settings.daily_check_hour, minute=0, timezone=settings.local_timezone),
        id="daily_status_check",
        replace_existing=True,
    )
    scheduler.start()


def stop_scheduler() -> None:
    scheduler.shutdown(wait=False)
