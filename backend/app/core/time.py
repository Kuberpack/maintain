from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.config import get_settings


def today_local() -> date:
    """Today's calendar date in the plant's local timezone (Sonipat/IST by
    default), not the server's. due_date is a local business-day concept --
    using UTC's calendar date here would be wrong for part of every day
    (IST is UTC+5:30, so UTC and IST disagree on "today" between 00:00 and
    05:30 IST). Per CLAUDE.md: timestamps stay UTC, but this is a date."""
    tz = ZoneInfo(get_settings().local_timezone)
    return datetime.now(tz).date()
