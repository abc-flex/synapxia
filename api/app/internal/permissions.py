"""
Role-Based Access Control (RBAC) Service

Implements privilege enforcement by checking user profile against the privilege matrix.
Used as a FastAPI dependency decorator to gate endpoints by module/option/edit permissions.
"""

import logging
from typing import Optional
from fastapi import HTTPException, Depends
from sqlmodel import Session, select

from ..admin.internal.models import User, Privilege
from .dependencies import get_db_session
from ..auth.routes import current_active_user

logger = logging.getLogger(__name__)


async def check_privilege(
    module: str,
    option: str,
    can_edit: bool = False,
    current_user: User = Depends(current_active_user),
    session: Session = Depends(get_db_session),
) -> User:
    """
    Verify user has required privilege for module/option access.

    **Superuser bypass:** Users with is_superuser=True bypass all checks.

    **Parameters:**
    - `module`: Module code (e.g., 'ADMIN', 'TAXO', 'LIB', 'COLLAB')
    - `option`: Option code within module (e.g., 'USERS', 'ASSETS', 'TEAMS')
    - `can_edit`: If True, require edit permission; if False, read-only is acceptable
    - `current_user`: Authenticated user (injected via current_active_user dependency)
    - `session`: Database session (injected via get_db_session dependency)

    **Returns:** Authenticated user if privilege check passes

    **Raises:**
    - HTTPException 403: User lacks required privilege or profile inactive
    - HTTPException 401: User not authenticated (handled by current_active_user)

    **Usage in route:**
    ```python
    @router.post("/")
    def create_item(
        data: ItemCreate,
        current_user: User = Depends(lambda: check_privilege("TAXO", "CATEGORIES", can_edit=True)),
        session: Session = Depends(get_db_session),
    ):
        # current_user verified + has TAXO/CATEGORIES edit permission
    ```
    """
    # Superuser bypass — short-circuit privilege check
    if current_user.is_superuser:
        logger.debug(f"✓ Superuser {current_user.username} bypassed privilege check for {module}/{option}")
        return current_user

    # Fetch privilege record
    privilege = session.exec(
        select(Privilege).where(
            Privilege.profile == current_user.profile,
            Privilege.module == module,
            Privilege.option == option,
            Privilege.is_active == True,
        )
    ).first()

    if not privilege:
        logger.warning(
            f"✗ {current_user.username} (profile={current_user.profile}) denied access to {module}/{option} "
            f"(privilege not found or inactive)"
        )
        raise HTTPException(
            status_code=403,
            detail=f"Access denied to {module}/{option}. Check your profile privileges.",
        )

    # Check edit permission if required
    if can_edit and not privilege.can_edit:
        logger.warning(
            f"✗ {current_user.username} (profile={current_user.profile}) attempted write to read-only {module}/{option}"
        )
        raise HTTPException(
            status_code=403,
            detail=f"Write access denied to {module}/{option}. You have read-only access.",
        )

    logger.debug(f"✓ {current_user.username} granted access to {module}/{option} (edit={privilege.can_edit})")
    return current_user


def require_privilege(module: str, option: str, can_edit: bool = False):
    """
    Dependency factory for gating endpoints by privilege.

    Wraps check_privilege to create a reusable dependency callable.

    **Usage in route:**
    ```python
    @router.post("/")
    def create_user(
        data: UserCreate,
        _: bool = Depends(require_privilege("ADMIN", "USERS", can_edit=True)),
        session: Session = Depends(get_db_session),
    ):
        # Endpoint is now gated by privilege
    ```

    **Parameters:**
    - `module`: Module code
    - `option`: Option code
    - `can_edit`: Require edit permission (default: False)

    **Returns:** FastAPI dependency callable that raises 403 if privilege denied
    """
    async def _check():
        # This will be called by FastAPI's dependency injection
        # and will raise HTTPException(403) if privilege denied
        await check_privilege(module, option, can_edit)
        return True

    return _check


__all__ = ["check_privilege", "require_privilege"]
