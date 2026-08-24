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

    alert_upcoming_days: int = 3
    alert_overdue_escalate_days: int = 1
    alert_unreviewed_hours: int = 8

    local_timezone: str = "Asia/Kolkata"
    daily_check_hour: int = 7

    uploads_dir: str = "uploads"
    max_upload_size_mb: int = 8

    # Optional S3-compatible object storage. If s3_bucket is set, photos go
    # there instead of local disk (Railway disks are ephemeral).
    s3_bucket: str | None = None
    s3_endpoint_url: str | None = None
    s3_access_key: str | None = None
    s3_secret_key: str | None = None
    s3_region: str = "auto"

    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from: str | None = None
    smtp_starttls: bool = True

    # WhatsApp: set twilio_* for Twilio, or whatsapp_api_url + token for a
    # generic HTTP BSP (Gupshup/Interakt-style). Unset = log-only stub.
    twilio_account_sid: str | None = None
    twilio_auth_token: str | None = None
    twilio_whatsapp_from: str | None = None
    whatsapp_api_url: str | None = None
    whatsapp_api_token: str | None = None
    whatsapp_from: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
