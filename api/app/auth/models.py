"""
Auth-specific ORM models.

Currently contains only the refresh-token row used by fastapi-users'
``DatabaseStrategy``. Defined on SQLModel's metadata so its FK to ``users.id``
resolves against the same registry SQLModel uses for the rest of the schema.
"""
from fastapi_users_db_sqlalchemy.access_token import SQLAlchemyBaseAccessTokenTable
from sqlalchemy import Column, ForeignKey, Integer
from sqlalchemy.orm import DeclarativeBase
from sqlmodel import SQLModel


class Base(DeclarativeBase):
    """Plain SQLAlchemy declarative base, but pointed at SQLModel's metadata
    so foreign keys to SQLModel-defined tables (e.g. ``users.id``) resolve."""

    metadata = SQLModel.metadata


class RefreshToken(SQLAlchemyBaseAccessTokenTable[int], Base):
    """
    Refresh token row.

    Inherits ``token`` (PK, str) and ``created_at`` (datetime) from
    ``SQLAlchemyBaseAccessTokenTable``. We override ``user_id`` to make the
    FK target explicit and enable cascade-delete.
    """

    __tablename__ = "refresh_tokens"

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
