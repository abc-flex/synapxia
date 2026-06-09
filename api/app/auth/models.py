"""
Auth-specific ORM models.

Currently contains only the refresh-token row used by fastapi-users'
``DatabaseStrategy``. Kept separate from ``app/admin/internal/models.py``
so it doesn't pollute the admin domain.
"""
from fastapi_users_db_sqlalchemy.access_token import SQLAlchemyBaseAccessTokenTable
from sqlalchemy import Column, ForeignKey, Integer
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Plain SQLAlchemy declarative base — separate from SQLModel's metadata
    so create-all/migrations don't try to re-create the SQLModel tables."""


class RefreshToken(SQLAlchemyBaseAccessTokenTable[int], Base):
    """
    Refresh token row.

    Inherits ``token`` (PK, str), ``created_at`` (datetime), ``user_id`` (FK
    placeholder) from ``SQLAlchemyBaseAccessTokenTable``. We override
    ``user_id`` to make the FK target explicit (the base class only typed
    it generically).
    """

    __tablename__ = "refresh_tokens"

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
