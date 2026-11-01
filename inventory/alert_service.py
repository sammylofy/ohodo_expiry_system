import logging
import requests
from django.conf import settings
from django.core.mail import send_mail
from .models import AlertLog, StoreProfile

logger = logging.getLogger(__name__)


def normalize_phone_number(phone: str) -> str:
    """Normalizes Nigerian phone numbers to 234xxxxxxxxxx format required by Termii."""
    if not phone:
        return ""
    cleaned = "".join(filter(str.isdigit, str(phone)))
    if cleaned.startswith("0") and len(cleaned) == 11:
        return "234" + cleaned[1:]
    if cleaned.startswith("234") and len(cleaned) == 13:
        return cleaned
    if len(cleaned) == 10:
        return "234" + cleaned
    return cleaned


def build_alert_message(product, store_name: str) -> str:
    """Constructs a clear, actionable expiry alert message for email/SMS/WhatsApp."""
    days = product.days_to_expiry
    if days < 0:
        urgency = f"EXPIRED ({abs(days)} days ago)"
        action = "Remove from shelves immediately to protect customers."
    elif days == 0:
        urgency = "EXPIRES TODAY"
        action = "Remove from shelves immediately."
    else:
        urgency = f"{product.status.upper()} ({days} days left)"
        action = "Prioritize clearance discount or return to supplier."

    return (
        f"[{store_name} Expiry Alert]\n"
        f"Status: {urgency}\n"
        f"Product: {product.name}\n"
        f"Batch: {product.batch_number}\n"
        f"Expiry Date: {product.expiry_date.strftime('%d %b %Y')}\n"
        f"Qty in Stock: {product.quantity}\n"
        f"Action: {action}"
    )


def send_email_alert(product, to_email: str, subject: str, message: str) -> bool:
    """Sends an email alert via Django send_mail and returns True if sent."""
    if not to_email:
        return False
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to_email],
            fail_silently=False,
        )
        return True
    except Exception as exc:
        logger.error("Email alert failed for %s: %s", product.name, exc)
        return False


def send_termii_message(to_phone: str, message: str, channel: str = 'generic') -> bool:
    """
    Sends SMS (channel='generic') or WhatsApp (channel='whatsapp') via Termii API.
    Returns True if HTTP 200/201 received, False otherwise.
    """
    normalized_phone = normalize_phone_number(to_phone)
    api_key = getattr(settings, 'TERMII_API_KEY', '')

    if not api_key or api_key == 'your_termii_api_key_here' or not normalized_phone:
        logger.warning("Termii API key not configured or invalid phone (%s).", normalized_phone)
        return False

    url = f"{settings.TERMII_BASE_URL.rstrip('/')}/api/sms/send"
    payload = {
        "to": normalized_phone,
        "from": settings.TERMII_SENDER_ID,
        "sms": message,
        "type": "plain",
        "channel": channel,
        "api_key": api_key,
    }

    try:
        response = requests.post(url, json=payload, timeout=12)
        if response.status_code in (200, 201):
            return True
        logger.error("Termii %s error (%s): %s", channel, response.status_code, response.text)
        return False
    except requests.RequestException as exc:
        logger.error("Termii network failure (%s): %s", channel, exc)
        return False


def send_all_alerts(product) -> dict:
    """
    Sends Email, SMS, and WhatsApp alerts for a product and creates AlertLog records.
    Returns a summary dictionary of dispatch statuses.
    """
    profile = StoreProfile.get_solo()
    message = build_alert_message(product, profile.store_name)
    subject = f"[{profile.store_name}] {product.status} Product Alert: {product.name}"

    # 1. Email Alert
    email_ok = send_email_alert(product, profile.owner_email, subject, message)
    AlertLog.objects.create(
        product=product,
        message=message,
        alert_type='Email',
        status='sent' if email_ok else 'failed'
    )

    # 2. SMS Alert via Termii ('generic')
    sms_ok = send_termii_message(profile.owner_phone, message, channel='generic')
    AlertLog.objects.create(
        product=product,
        message=message,
        alert_type='SMS',
        status='sent' if sms_ok else 'failed'
    )

    # 3. WhatsApp Alert via Termii ('whatsapp')
    wa_ok = send_termii_message(profile.owner_phone, message, channel='whatsapp')
    AlertLog.objects.create(
        product=product,
        message=message,
        alert_type='WhatsApp',
        status='sent' if wa_ok else 'failed'
    )

    return {'email': email_ok, 'sms': sms_ok, 'whatsapp': wa_ok}