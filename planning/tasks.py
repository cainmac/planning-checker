import logging

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def send_planning_alert_email(address: str, borough_label: str, recipient_email: str):
    """
    Simple helper to send a planning alert confirmation email.
    No Celery, just a normal function call.
    """
    subject = "Planning alert set up"
    message = (
        f"A planning alert has been set up for '{address}' "
        f"({borough_label})."
    )

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            fail_silently=False,
        )
    except Exception as exc:
        # Don't crash the page if email fails — just log it
        logger.exception("Error sending planning alert email: %r", exc)
