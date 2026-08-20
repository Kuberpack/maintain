from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+psycopg2://maintain:maintain@localhost:5432/maintain"

    @field_validator("database_url")
    @classmethod
    def _normalize_database_url(cls, v: str) -> str:
        """Hosting providers (Railway, formerly Heroku) commonly hand out
        DATABASE_URL as `postgres://...` or a driver-less `postgresql://...`
        rather than this app's explicit `postgresql+psycopg2://...`.
        SQLAlchemy 2.x rejects the old `postgres://` scheme outright, and
        while a driver-less `postgresql://` happens to default to psycopg2
        today, that's an implicit SQLAlchemy behavior this app shouldn't
        depend on silently. Normalize both to the explicit scheme this app
        actually uses -- everything after the scheme (host, port, db name,
        query params like sslmode) is left untouched either way."""
        if v.startswith("postgres://"):
            v = "postgresql://" + v[len("postgres://") :]
        if v.startswith("postgresql://"):
            v = "postgresql+psycopg2://" + v[len("postgresql://") :]
        return v

    jwt_secret: str = "change-me-in-.env"
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 60 * 24 * 7  # 7 days; shared devices, workers stay logged in

    cors_origins: list[str] = ["http://localhost:5173"]

    # Alert thresholds, in days. Positive due_in_days = upcoming warning;
    # negative (days overdue) = escalation. Placeholders until tuned for real usage.
    alert_upcoming_days: int = 3
    alert_overdue_escalate_days: int = 1

    local_timezone: str = "Asia/Kolkata"

    # Local hour (in local_timezone) the daily status-check/alert job runs.
    daily_check_hour: int = 7

    # Local-disk storage for mark-done proof-of-completion photos. Real
    # cloud storage is an open question (todo.md Phase 5); this is enough
    # for the current single-server deployment model.
    uploads_dir: str = "uploads"
    max_upload_size_mb: int = 8


@lru_cache
def get_settings() -> Settings:
    return Settings()
