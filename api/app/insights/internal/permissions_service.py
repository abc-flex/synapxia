"""Per-dashboard access resolution (Dashboard Management).

Binds the shared per-resource permission engine
(:mod:`app.internal.resource_permissions`) to ``dashboard_permissions`` — the
same rules asset and initiative grants follow: PUBLIC or scope-matched grants,
MANAGE beats VIEW, temporal validity via ``valid_from``/``valid_to``,
revoke-not-delete, superuser bypass. Module-level RBAC
(``require_privilege("ANA", "DASHBOARDS", …)``) stays the outer gate; these
guards are the stricter inner check (routes map ``DashboardAccessForbidden``
to 403).
"""
from datetime import datetime
from typing import Dict, List, Optional

from sqlmodel import Session

from .models import DashboardPermission
from ...admin.internal.models import User
from ...internal import resource_permissions as rp
from ...internal.resource_permissions import ACCESS_MANAGE, ACCESS_VIEW  # noqa: F401

_FK = "dashboard"


class DashboardAccessForbidden(Exception):
    """Caller lacks the required access on the target dashboard (→ 403)."""


def not_revoked_clause(now: Optional[datetime] = None):
    """SQL predicate for "this dashboard grant has not been revoked"."""
    return rp.not_revoked_clause(DashboardPermission, now)


def is_revoked(permission: DashboardPermission, now: Optional[datetime] = None) -> bool:
    """Python twin of :func:`not_revoked_clause`."""
    return rp.is_revoked(permission, now)


def dashboards_user_access(
    session: Session, user: User, dashboard_ids: List[int]
) -> Dict[int, str]:
    """The user's effective level per dashboard (MANAGE > VIEW); dashboards
    with no grant reaching the user are absent."""
    return rp.effective_levels(
        rp.matching_grants(session, user, DashboardPermission, _FK, dashboard_ids), _FK)


def dashboards_user_scopes(
    session: Session, user: User, dashboard_ids: List[int]
) -> Dict[int, List[str]]:
    """Per dashboard, the sorted scope types by which a live grant reaches
    ``user`` (drives the privileges filter). One batched query."""
    return rp.user_scopes_for(session, user, DashboardPermission, _FK, dashboard_ids)


def dashboard_matching_grants(
    session: Session, user: User, dashboard_id: int
) -> List[DashboardPermission]:
    """The caller's live grants on one dashboard — the rows that give access.
    Grant-bound parameters apply only when their bound grant is among them."""
    return rp.matching_grants(session, user, DashboardPermission, _FK, [dashboard_id])


def accessible_dashboards(session: Session, user: User) -> Dict[int, str]:
    """Every dashboard id the user can access → effective level (superuser
    bypass is the caller's responsibility)."""
    return rp.effective_levels(
        rp.matching_grants(session, user, DashboardPermission, _FK, None), _FK)


def user_dashboard_access(session: Session, user: User, dashboard_id: int) -> Optional[str]:
    """Single-dashboard effective level (None = no access). Superusers get
    MANAGE."""
    if getattr(user, "is_superuser", False):
        return ACCESS_MANAGE
    return dashboards_user_access(session, user, [dashboard_id]).get(dashboard_id)


def require_dashboard_manage(session: Session, user: User, dashboard_id: int) -> None:
    """Per-dashboard write guard: MANAGE (or superuser) required."""
    if user_dashboard_access(session, user, dashboard_id) != ACCESS_MANAGE:
        raise DashboardAccessForbidden(
            f"MANAGE permission required on dashboard {dashboard_id}.")


def require_dashboard_view(session: Session, user: User, dashboard_id: int) -> None:
    """Per-dashboard read guard: any live grant (VIEW or MANAGE) or superuser."""
    if user_dashboard_access(session, user, dashboard_id) is None:
        raise DashboardAccessForbidden(
            f"Access to dashboard {dashboard_id} is not granted.")
