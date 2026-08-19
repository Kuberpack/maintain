import logging

from app.models import User

logger = logging.getLogger("alerts")


def send_whatsapp_alert(user: User, message: str) -> None:
    """Stub: no WhatsApp BSP is wired up yet (Gupshup/Twilio/Interakt --
    not chosen). Replace this body with a real API call once one is; the
    call site (notify_user, below) doesn't need to change."""
    logger.info("Would send WhatsApp to %s (%s): %s", user.name, user.whatsapp_number, message)


def send_email_alert(user: User, subject: str, message: str) -> None:
    """Stub: no SMTP is configured yet. Replace this body with a real send
    once credentials exist; the call site doesn't need to change."""
    logger.info("Would send email to %s (%s): %s -- %s", user.name, user.email, subject, message)


def notify_user(user: User, subject: str, message: str) -> None:
    """Send via every channel this user has a destination for -- architecture.md
    specifies WhatsApp *and* email, not a choice between them."""
    if user.whatsapp_number:
        send_whatsapp_alert(user, message)
    if user.email:
        send_email_alert(user, subject, message)
