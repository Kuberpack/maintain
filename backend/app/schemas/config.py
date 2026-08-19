from app.schemas.base import CamelModel


class PublicConfig(CamelModel):
    alert_upcoming_days: int
    alert_overdue_escalate_days: int
