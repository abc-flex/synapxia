"""Email sending service with multi-profile support (Phase 2)."""
import logging
from typing import List, Optional
from fastapi_mail import FastMail, MessageSchema, MessageType

from .config import get_mail_config

logger = logging.getLogger(__name__)


async def send_message(
    profile: str = "default",
    subject: str = "",
    recipients: List[str] = None,
    template_name: str = "",
    context: Optional[dict] = None,
) -> bool:
    """
    Send an email using Jinja2 template.

    Mail is send-only (no inbox/tracking). If SMTP is disabled, logs instead of sending.

    Args:
        profile: SMTP profile (default, ops, bookings)
        subject: Email subject line
        recipients: List of recipient email addresses
        template_name: Jinja2 template filename (e.g., "welcome.html")
        context: Template variables dict

    Returns:
        True if sent successfully, False if mail is disabled or failed.

    Example:
        await send_message(
            profile="ops",
            subject="Reset your password",
            recipients=["user@example.com"],
            template_name="password_reset.html",
            context={"reset_link": "https://..."}
        )
    """
    if not recipients:
        recipients = []
    if not context:
        context = {}

    # Get mail config for this profile
    config = get_mail_config(profile)
    if config is None:
        # Mail disabled; log instead of sending
        logger.info(
            f"Mail disabled; would send {template_name} to {recipients} "
            f"(subject: {subject}, profile: {profile})"
        )
        return False

    try:
        fastmail = FastMail(config)
        message = MessageSchema(
            subject=subject,
            recipients=recipients,
            template_body=context,
            subtype=MessageType.html,
        )
        await fastmail.send_message(message, template_name=template_name)
        logger.info(f"Email sent: {template_name} to {recipients}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email {template_name}: {e}")
        return False
