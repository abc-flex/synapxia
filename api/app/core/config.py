"""
Application configuration using pydantic-settings (Phase 2).

Centralizes environment variable management for JWT, mail, and other services.
Constitution IV: all env vars are explicit and documented here.
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings from environment variables."""

    # ==================== JWT Configuration ====================
    jwt_secret: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    jwt_lifetime_seconds: int = int(os.getenv("JWT_LIFETIME_SECONDS", "3600"))  # 60 min
    jwt_algorithm: str = "HS256"

    # ==================== SMTP Configuration (Multi-profile) ====================
    # When smtp_hostname is unset/empty, mail is disabled and send operations log instead
    smtp_hostname: Optional[str] = os.getenv("SMTP_HOSTNAME")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_username: Optional[str] = os.getenv("SMTP_USERNAME")
    smtp_password: Optional[str] = os.getenv("SMTP_PASSWORD")
    smtp_use_tls: bool = os.getenv("SMTP_USE_TLS", "true").lower() in ("true", "1")
    smtp_use_ssl: bool = os.getenv("SMTP_USE_SSL", "false").lower() in ("true", "1")

    # Default profile: generic system emails
    smtp_from_email: str = os.getenv("SMTP_FROM_EMAIL", "noreply@synapxia.local")
    smtp_from_name: str = os.getenv("SMTP_FROM_NAME", "SynapxIA")

    # Ops profile: operations/admin emails (e.g., password reset requests)
    ops_email: str = os.getenv("OPS_EMAIL", "ops@synapxia.local")
    ops_email_name: str = os.getenv("OPS_EMAIL_NAME", "SynapxIA Operations")

    # Bookings profile: transactional/booking emails
    bookings_email: str = os.getenv("BOOKINGS_EMAIL", "bookings@synapxia.local")
    bookings_email_name: str = os.getenv("BOOKINGS_EMAIL_NAME", "SynapxIA Bookings")

    # ==================== Application ====================
    app_env: str = os.getenv("APP_ENV", "development")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
