"""Asset permission-scope resolution (HU-LI08 / asset filters).

The resolution engine — scope matching, temporal validity, revoke-not-delete,
MANAGE-beats-VIEW — lives in :mod:`app.internal.resource_permissions` and is
shared with other domains (``init_permissions``). This module binds it to
``asset_permissions`` and keeps the asset-facing API every lib route and test
already uses.

An ``asset_permissions`` row grants access when its ``target_type`` is PUBLIC,
or when its ``(target_type, target_code)`` matches one of the current user's
scopes (USER id, UNIT, ROLE/TEAM via active assignments, PROJECT via teams).
Grants are never deleted — revoking sets ``valid_to`` — so a single temporal
check decides whether a grant is in effect. Read-only — no new table.
"""
from datetime import datetime
from typing import Dict, List, Optional, Set

from sqlmodel import Session

from .models import AssetPermission
from ...admin.internal.models import User
from ...internal import resource_permissions as rp
from ...internal.resource_permissions import (  # noqa: F401  (re-exported)
    ACCESS_MANAGE,
    ACCESS_VIEW,
    SCOPE_PROJECT,
    SCOPE_PUBLIC,
    SCOPE_ROLE,
    SCOPE_TEAM,
    SCOPE_UNIT,
    SCOPE_USER,
)

_FK = "asset"


class AssetAccessForbidden(Exception):
    """Caller lacks MANAGE on the target asset (routes map this to HTTP 403)."""


# Kept under their historical private names — tests and callers use them.
_as_naive_utc = rp.as_naive_utc
_is_valid_now = rp.is_valid_now


def not_revoked_clause(now: Optional[datetime] = None):
    """SQL predicate for "this asset grant has not been revoked" (see
    :func:`app.internal.resource_permissions.not_revoked_clause`)."""
    return rp.not_revoked_clause(AssetPermission, now)


def is_revoked(permission: AssetPermission, now: Optional[datetime] = None) -> bool:
    """Python twin of :func:`not_revoked_clause`."""
    return rp.is_revoked(permission, now)


def resolve_user_scopes(session: Session, user: User) -> Dict[str, Set[str]]:
    """The current user's scope identifiers, keyed by scope-type."""
    return rp.resolve_user_scopes(session, user)


def assets_user_access(
    session: Session, user: User, asset_ids: List[int]
) -> Dict[int, str]:
    """The user's effective access level per asset (MANAGE > VIEW); assets with
    no matching grant are absent from the result."""
    return rp.effective_levels(
        rp.matching_grants(session, user, AssetPermission, _FK, asset_ids), _FK)


def accessible_assets(session: Session, user: User) -> Dict[int, str]:
    """Every asset id the user can access → effective level. Drives the repo's
    caller-scoped listing: an asset with no grant reaching the user is hidden
    (HU-LI08 — superuser bypass is the caller's responsibility)."""
    return rp.effective_levels(
        rp.matching_grants(session, user, AssetPermission, _FK, None), _FK)


def user_asset_access(session: Session, user: User, asset_id: int) -> Optional[str]:
    """Single-asset effective level (None = no access)."""
    return assets_user_access(session, user, [asset_id]).get(asset_id)


def require_asset_manage(session: Session, user: User, asset_id: int) -> None:
    """Per-asset write guard: the caller must hold MANAGE on the asset (or be a
    superuser — mirroring ``require_privilege``'s bypass). Raises
    ``AssetAccessForbidden``; routes map it to 403."""
    if getattr(user, "is_superuser", False):
        return
    if user_asset_access(session, user, asset_id) != ACCESS_MANAGE:
        raise AssetAccessForbidden(
            f"MANAGE permission required on asset {asset_id}.")


def assets_user_scopes(
    session: Session, user: User, asset_ids: List[int]
) -> Dict[int, List[str]]:
    """For each asset id, the sorted scope-types by which ``user`` is granted access
    (a subset of USER/ROLE/TEAM/UNIT/PROJECT/PUBLIC). One batched query over the
    given assets (no N+1)."""
    return rp.user_scopes_for(session, user, AssetPermission, _FK, asset_ids)
