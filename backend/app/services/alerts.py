import logging
import smtplib
from email.message import EmailMessage
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.config import get_settings
from app.models import User

logger = logging.getLogger("alerts")


def send_whatsapp_alert(user: User, message: str) -> None:
    if not user.whatsapp_number:
        return
    settings = get_settings()
    to_number = user.whatsapp_number.strip()
    if settings.twilio_account_sid and settings.twilio_auth_token and settings.twilio_whatsapp_from:
        _send_twilio(settings, to_number, message)
        return
    if settings.whatsapp_api_url and settings.whatsapp_api_token:
        _send_http_whatsapp(settings, to_number, message)
        return
    logger.info("Would send WhatsApp to %s (%s): %s", user.name, user.whatsapp_number, message)


def send_email_alert(user: User, subject: str, message: str) -> None:
    if not user.email:
        return
    settings = get_settings()
    if not settings.smtp_host or not settings.smtp_from:
        logger.info("Would send email to %s (%s): %s -- %s", user.name, user.email, subject, message)
        return
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from
    msg["To"] = user.email
    msg.set_content(message)
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
            if settings.smtp_starttls:
                smtp.starttls()
            if settings.smtp_user and settings.smtp_password:
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(msg)
        logger.info("Sent email to %s (%s): %s", user.name, user.email, subject)
    except OSError:
        logger.exception("SMTP send failed for %s", user.email)


def notify_user(user: User, subject: str, message: str) -> None:
    """Send via every channel this user has a destination for -- architecture.md
    specifies WhatsApp *and* email, not a choice between them."""
    if user.whatsapp_number:
        send_whatsapp_alert(user, message)
    if user.email:
        send_email_alert(user, subject, message)


def _send_twilio(settings, to_number: str, message: str) -> None:
    sid = settings.twilio_account_sid
    url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
    body = urlencode(
        {
            "From": f"whatsapp:{settings.twilio_whatsapp_from}",
            "To": f"whatsapp:{_with_plus(to_number)}",
            "Body": message,
        }
    ).encode()
    request = Request(url, data=body, method="POST")
    import base64

    token = base64.b64encode(f"{sid}:{settings.twilio_auth_token}".encode()).decode()
    request.add_header("Authorization", f"Basic {token}")
    request.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urlopen(request, timeout=20) as response:
            response.read()
        logger.info("Sent Twilio WhatsApp to %s", to_number)
    except OSError:
        logger.exception("Twilio WhatsApp send failed for %s", to_number)


def _send_http_whatsapp(settings, to_number: str, message: str) -> None:
    import json

    payload = json.dumps(
        {
            "to": _with_plus(to_number),
            "from": settings.whatsapp_from,
            "text": message,
        }
    ).encode()
    request = Request(settings.whatsapp_api_url, data=payload, method="POST")
    request.add_header("Authorization", f"Bearer {settings.whatsapp_api_token}")
    request.add_header("Content-Type", "application/json")
    try:
        with urlopen(request, timeout=20) as response:
            response.read()
        logger.info("Sent WhatsApp HTTP to %s", to_number)
    except OSError:
        logger.exception("WhatsApp HTTP send failed for %s", to_number)


def _with_plus(number: str) -> str:
    digits = number.strip()
    if digits.startswith("+"):
        return digits
    if digits.startswith("00"):
        return "+" + digits[2:]
    if len(digits) == 10:
        return "+91" + digits
    return "+" + digits
