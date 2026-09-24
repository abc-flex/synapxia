"""Per-initiative access resolution (Initiative Management).

Binds the shared per-resource permission engine
(:mod:`app.internal.resource_permissions`) to ``init_permissions`` — the same
rules asset grants follow: PUBLIC or scope-matched grants, MANAGE beats VIEW,
temporal validity via ``valid_from``/``valid_to``, revoke-not-delete, superuser
bypass. Module-level RBAC (``require_privilege("INITS", …)``) stays the outer
gate; these guards are the stricter inner check (routes map
``InitAccessForbidden`` to 403).
"""
from datetime import datetime
from typing import Dict, List, Optional

from sqlmodel import Session

from .models import InitPermission
from ...admin.internal.models import User
from ...internal import resource_permissions as rp
from ...internal.resource_permissions import ACCESS_MANAGE, ACCESS_VIEW  # noqa: F401

_FK = "init"


class InitAccessForbidden(Exception):
    """Caller lacks the required access on the target initiative (→ 403)."""


def not_revoked_clause(now: Optional[datetime] = None):
    """SQL predicate for "this initiative grant has not been revoked"."""
    return rp.not_revoked_clause(InitPermission, now)


def is_revoked(permission: InitPermission, now: Optional[datetime] = None) -> bool:
    """Python twin of :func:`not_revoked_clause`."""
    return rp.is_revoked(permission, now)


def inits_user_access(
    session: Session, user: User, init_ids: List[int]
) -> Dict[int, str]:
    """The user's effective level per initiative (MANAGE > VIEW); initiatives
    with no grant reaching the user are absent."""
    return rp.effective_levels(
        rp.matching_grants(session, user, InitPermission, _FK, init_ids), _FK)


def inits_user_scopes(
    session: Session, user: User, init_ids: List[int]
) -> Dict[int, List[str]]:
    """Per initiative, the sorted scope types by which a live grant reaches
    ``user`` (same rule as the asset list's privileges filter). One batched
    query over the given ids."""
    return rp.user_scopes_for(session, user, InitPermission, _FK, init_ids)


def accessible_inits(session: Session, user: User) -> Dict[int, str]:
    """Every initiative id the user can access → effective level (superuser
    bypass is the caller's responsibility)."""
    return rp.effective_levels(
        rp.matching_grants(session, user, InitPermission, _FK, None), _FK)


def user_init_access(session: Session, user: User, init_id: int) -> Optional[str]:
    """Single-initiative effective level (None = no access). Superusers get
    MANAGE."""
    if getattr(user, "is_superuser", False):
        return ACCESS_MANAGE
    return inits_user_access(session, user, [init_id]).get(init_id)


def require_init_manage(session: Session, user: User, init_id: int) -> None:
    """Per-initiative write guard: MANAGE (or superuser) required."""
    if user_init_access(session, user, init_id) != ACCESS_MANAGE:
        raise InitAccessForbidden(
            f"MANAGE permission required on initiative {init_id}.")


def require_init_view(session: Session, user: User, init_id: int) -> None:
    """Per-initiative read guard: any live grant (VIEW or MANAGE) or superuser."""
    if user_init_access(session, user, init_id) is None:
        raise InitAccessForbidden(
            f"Access to initiative {init_id} is not granted.")
