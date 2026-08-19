from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+psycopg2://maintain:maintain@localhost:5432/maintain"

    jwt_secret: str = "change-me-in-.env"
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 60 * 24 * 7  # 7 days; shared devices, workers stay logged in

    cors_origins: list[str] = ["http://localhost:5173"]

    # Alert thresholds, in days. Positive due_in_days = upcoming warning;
    # negative (days overdue) = escalation. Placeholders until tuned for real usage.
    alert_upcoming_days: int = 3
    alert_overdue_escalate_days: int = 1

    local_timezone: str = "Asia/Kolkata"

    # Local-disk storage for mark-done proof-of-completion photos. Real
    # cloud storage is an open question (todo.md Phase 5); this is enough
    # for the current single-server deployment model.
    uploads_dir: str = "uploads"
    max_upload_size_mb: int = 8


@lru_cache
def get_settings() -> Settings:
    return Settings()
