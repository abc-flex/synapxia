"""
Role-Based Access Control (RBAC) Service.

Sits ON TOP of fastapi-users authentication: fastapi-users decodes the JWT
and yields the User; this module decides whether that user is allowed to
touch a given (module, option) with read or write intent, by consulting
the ``privileges`` table.

Usage in a route:

    @router.post("/")
    def create_user(
        data: UserCreate,
        current_user: User = Depends(require_privilege("ADMIN", "USERS", can_edit=True)),
        session: Session = Depends(get_db_session),
    ):
        ...
"""

import logging
from typing import Callable

from fastapi import Depends, HTTPException
from sqlmodel import Session, select

from ..admin.internal.models import Privilege, User
from ..auth.routes import current_active_user
from .dependencies import get_db_session

logger = logging.getLogger(__name__)


def has_privilege(session: Session, user: User, module: str, option: str, can_edit: bool = False) -> bool:
    """
    Non-raising check: does ``user`` have (module, option) access — with
    write intent if ``can_edit``? Superusers always do.

    Use this (instead of ``require_privilege``) when a route needs to accept
    ANY of several options — e.g. a category-scoped read route that should
    open to whoever holds a privilege on that specific category option,
    without requiring the broader management-module option. See
    ``require_privilege``'s docstring for the single-option, Depends-based case.
    """
    if user.is_superuser:
        return True

    privilege = session.exec(
        select(Privilege).where(
            Privilege.profile == user.profile,
            Privilege.module == module,
            Privilege.option == option,
            Privilege.is_active == True,  # noqa: E712 — SQLModel equality
        )
    ).first()

    if not privilege:
        return False
    if can_edit and not privilege.can_edit:
        return False
    return True


def check_privilege(session: Session, user: User, module: str, option: str, can_edit: bool = False) -> None:
    """Raises HTTPException(403) unless ``has_privilege(...)`` is True."""
    if has_privilege(session, user, module, option, can_edit):
        logger.debug(f"✓ {user.username} granted access to {module}/{option}")
        return

    logger.warning(
        f"✗ {user.username} (profile={user.profile}) denied access to {module}/{option} "
        f"(can_edit={can_edit})"
    )
    raise HTTPException(
        status_code=403,
        detail=f"Access denied to {module}/{option}. Check your profile privileges.",
    )


def has_any_privilege(
    session: Session, user: User, module: str, options: list[str], can_edit: bool = False
) -> bool:
    """Non-raising check: does ``user`` have (module, option) access for ANY of
    the given options — the multi-option counterpart to ``has_privilege``, for
    routes reachable via more than one entry-point option (e.g. a catalog-scoped
    read that should open to the asset-management option OR that specific
    category's own option). Superusers always do."""
    if user.is_superuser:
        return True
    return any(has_privilege(session, user, module, option, can_edit) for option in options)


def check_any_privilege(
    session: Session, user: User, module: str, options: list[str], can_edit: bool = False
) -> None:
    """Raises HTTPException(403) unless ``has_any_privilege(...)`` is True."""
    if has_any_privilege(session, user, module, options, can_edit):
        return
    logger.warning(
        f"✗ {user.username} (profile={user.profile}) denied access to "
        f"{module}/{{{'|'.join(options)}}} (can_edit={can_edit})"
    )
    raise HTTPException(
        status_code=403,
        detail=f"Access denied to {module}/{{{'|'.join(options)}}}. Check your profile privileges.",
    )


def require_privilege(module: str, option: str, can_edit: bool = False) -> Callable:
    """
    Dependency factory: returns an async callable suitable for
    ``Depends(require_privilege("MODULE", "OPTION", can_edit=True))``.

    The inner ``_check`` is the actual FastAPI dependency. It declares
    its own ``Depends`` for the authenticated user and DB session so
    FastAPI's DI resolves them at request time. ``module``, ``option``,
    and ``can_edit`` are captured by closure.

    Superusers bypass the privilege table entirely.

    Raises HTTPException(403) if the user's profile lacks the required
    (module, option) row, or if write was requested and the row is
    read-only. For an "any of several options" check instead of this
    single fixed one, use ``has_privilege``/``check_privilege`` directly
    in the route body (module/option can't depend on the request's own
    path params inside a ``Depends`` factory — those aren't resolved yet
    when the dependency is registered).
    """

    async def _check(
        current_user: User = Depends(current_active_user),
        session: Session = Depends(get_db_session),
    ) -> User:
        check_privilege(session, current_user, module, option, can_edit)
        return current_user

    return _check


__all__ = [
    "require_privilege", "has_privilege", "check_privilege",
    "has_any_privilege", "check_any_privilege",
]
