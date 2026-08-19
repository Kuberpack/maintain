from fastapi import APIRouter, Depends

from app.config import get_settings
from app.core.deps import get_current_user
from app.schemas.config import PublicConfig

router = APIRouter(prefix="/config", tags=["config"])


@router.get("", response_model=PublicConfig)
def get_public_config(_user=Depends(get_current_user)) -> PublicConfig:
    settings = get_settings()
    return PublicConfig(
        alert_upcoming_days=settings.alert_upcoming_days,
        alert_overdue_escalate_days=settings.alert_overdue_escalate_days,
    )
