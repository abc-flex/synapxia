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
    read-only.
    """

    async def _check(
        current_user: User = Depends(current_active_user),
        session: Session = Depends(get_db_session),
    ) -> User:
        # Superuser bypass
        if current_user.is_superuser:
            logger.debug(
                f"✓ Superuser {current_user.username} bypassed privilege check for {module}/{option}"
            )
            return current_user

        privilege = session.exec(
            select(Privilege).where(
                Privilege.profile == current_user.profile,
                Privilege.module == module,
                Privilege.option == option,
                Privilege.is_active == True,  # noqa: E712 — SQLModel equality
            )
        ).first()

        if not privilege:
            logger.warning(
                f"✗ {current_user.username} (profile={current_user.profile}) "
                f"denied access to {module}/{option} (privilege not found or inactive)"
            )
            raise HTTPException(
                status_code=403,
                detail=f"Access denied to {module}/{option}. Check your profile privileges.",
            )

        if can_edit and not privilege.can_edit:
            logger.warning(
                f"✗ {current_user.username} (profile={current_user.profile}) "
                f"attempted write to read-only {module}/{option}"
            )
            raise HTTPException(
                status_code=403,
                detail=f"Write access denied to {module}/{option}. You have read-only access.",
            )

        logger.debug(
            f"✓ {current_user.username} granted access to {module}/{option} "
            f"(edit={privilege.can_edit})"
        )
        return current_user

    return _check


__all__ = ["require_privilege"]
