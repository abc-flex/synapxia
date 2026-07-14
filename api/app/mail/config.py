"""Email configuration with multi-profile SMTP support (Phase 2)."""
import logging
from typing import Optional
from fastapi_mail import ConnectionConfig

from ..core.config import settings

logger = logging.getLogger(__name__)


def get_mail_config(profile: str = "default") -> Optional[ConnectionConfig]:
    """
    Get SMTP configuration for a mail profile.

    Profiles:
    - default: Generic system emails (welcome, notifications)
    - ops: Operations/admin emails (password reset, audits)
    - bookings: Transactional emails (booking confirmations, updates)

    Args:
        profile: Mail profile name (default, ops, bookings)

    Returns:
        ConnectionConfig if SMTP is enabled, None if disabled.
        When None, mail operations will log instead of sending.
    """
    # Mail is disabled if smtp_hostname is not set
    if not settings.smtp_hostname:
        logger.debug(f"Mail disabled; skipping {profile} profile")
        return None

    # Profile-specific sender details
    profile_map = {
        "default": {
            "from_email": settings.smtp_from_email,
            "from_name": settings.smtp_from_name,
        },
        "ops": {
            "from_email": settings.ops_email,
            "from_name": settings.ops_email_name,
        },
        "bookings": {
            "from_email": settings.bookings_email,
            "from_name": settings.bookings_email_name,
        },
    }

    # Use provided profile, fall back to default
    profile_cfg = profile_map.get(profile, profile_map["default"])

    return ConnectionConfig(
        mail_server=settings.smtp_hostname,
        mail_port=settings.smtp_port,
        mail_username=settings.smtp_username,
        mail_password=settings.smtp_password,
        mail_tls=settings.smtp_use_tls,
        mail_ssl=settings.smtp_use_ssl,
        mail_from=profile_cfg["from_email"],
        mail_from_name=profile_cfg["from_name"],
        template_folder="app/mail/templates",
    )
