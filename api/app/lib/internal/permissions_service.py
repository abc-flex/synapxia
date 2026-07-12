"""Asset permission-scope resolution (HU-LI / asset filters).

The asset list's "Privileges/Permisos" filter needs, per asset, *which scope-types
grant the current user access*. An ``asset_permissions`` row grants access when its
``target_type`` is PUBLIC, or when its ``(target_type, target_code)`` matches one of
the current user's scopes:

  - USER    → the user's own id (target_code stores the id as a string)
  - UNIT    → the user's business unit (``users.unit``)
  - ROLE    → a role the user holds via an active collab assignment
  - TEAM    → a team the user belongs to via an active collab assignment
  - PROJECT → a project belonging to one of the user's teams

All collab relationships (assignments, projects) and the permissions themselves are
gated by ``is_active`` + temporal validity (``valid_from``/``valid_to``). Read-only —
no new table.
"""
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set

from sqlalchemy import and_, or_
from sqlmodel import Session, select

from .models import AssetPermission
from ...admin.internal.models import User
from ...collab.internal.models import Assignment, Project

# asset_permissions.target_type values (TARGET_TYPE list).
SCOPE_USER = "USER"
SCOPE_ROLE = "ROLE"
SCOPE_TEAM = "TEAM"
SCOPE_UNIT = "UNIT"
SCOPE_PROJECT = "PROJECT"
SCOPE_PUBLIC = "PUBLIC"

# asset_permissions.access_level values (ACCESS_LEVEL list).
ACCESS_VIEW = "VIEW"
ACCESS_MANAGE = "MANAGE"


class AssetAccessForbidden(Exception):
    """Caller lacks MANAGE on the target asset (routes map this to HTTP 403)."""


def _as_naive_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Normalize to naive UTC so naive (SQLite) and tz-aware (Postgres
    TIMESTAMPTZ) datetimes can be compared without
    'can't compare offset-naive and offset-aware datetimes'."""
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _is_valid_now(valid_from, valid_to, now: datetime) -> bool:
    """True if a temporal row (assignment/permission) is in effect at ``now``."""
    vf = _as_naive_utc(valid_from)
    vt = _as_naive_utc(valid_to)
    n = _as_naive_utc(now)
    if vf is not None and vf > n:
        return False
    if vt is not None and vt <= n:
        return False
    return True


def resolve_user_scopes(session: Session, user: User) -> Dict[str, Set[str]]:
    """The current user's scope identifiers, keyed by scope-type.

    USER/UNIT come straight off the user; ROLE/TEAM from active assignments;
    PROJECT from active projects of those teams. PUBLIC is implicit (always
    granted) so it is not included here.
    """
    now = datetime.utcnow()

    assignments = session.exec(
        select(Assignment).where(
            Assignment.user_id == user.id,
            Assignment.is_active == True,  # noqa: E712
        )
    ).all()
    active = [a for a in assignments if _is_valid_now(a.valid_from, a.valid_to, now)]

    roles = {a.role for a in active if a.role}
    teams = {a.team for a in active if a.team}

    projects: Set[str] = set()
    if teams:
        rows = session.exec(
            select(Project.code).where(
                Project.team.in_(list(teams)),
                Project.is_active == True,  # noqa: E712
            )
        ).all()
        projects = {code for code in rows if code}

    return {
        SCOPE_USER: {str(user.id)},
        SCOPE_UNIT: {user.unit} if getattr(user, "unit", None) else set(),
        SCOPE_ROLE: roles,
        SCOPE_TEAM: teams,
        SCOPE_PROJECT: projects,
    }


def _matching_perms(
    session: Session, user: User, asset_ids: Optional[List[int]] = None
) -> List[AssetPermission]:
    """Active, temporally-valid AssetPermission rows that grant ``user`` access
    (PUBLIC rows or rows matching one of the user's scope pairs). With
    ``asset_ids=None`` the scan is repo-wide but SQL-bounded to the user's own
    scope pairs, so it returns at most the user's grant rows — not the table."""
    scopes = resolve_user_scopes(session, user)
    now = datetime.utcnow()

    scope_clauses = [AssetPermission.target_type == SCOPE_PUBLIC]
    for target_type, codes in scopes.items():
        if codes:
            scope_clauses.append(and_(
                AssetPermission.target_type == target_type,
                AssetPermission.target_code.in_(list(codes)),  # type: ignore[attr-defined]
            ))

    query = select(AssetPermission).where(
        AssetPermission.is_active == True,  # noqa: E712
        or_(*scope_clauses),
    )
    if asset_ids is not None:
        if not asset_ids:
            return []
        query = query.where(AssetPermission.asset.in_(asset_ids))  # type: ignore[attr-defined]

    perms = session.exec(query).all()
    return [p for p in perms if _is_valid_now(p.valid_from, p.valid_to, now)]


def _effective_levels(perms: List[AssetPermission]) -> Dict[int, str]:
    """Reduce matched grant rows to one effective level per asset — MANAGE
    beats everything else; any non-MANAGE grant counts as VIEW-equivalent."""
    levels: Dict[int, str] = {}
    for p in perms:
        level = ACCESS_MANAGE if p.access_level == ACCESS_MANAGE else ACCESS_VIEW
        if levels.get(p.asset) != ACCESS_MANAGE:
            levels[p.asset] = level
    return levels


def assets_user_access(
    session: Session, user: User, asset_ids: List[int]
) -> Dict[int, str]:
    """The user's effective access level per asset (MANAGE > VIEW); assets with
    no matching grant are absent from the result."""
    return _effective_levels(_matching_perms(session, user, asset_ids))


def accessible_assets(session: Session, user: User) -> Dict[int, str]:
    """Every asset id the user can access → effective level. Drives the repo's
    caller-scoped listing: an asset with no grant reaching the user is hidden
    (HU-LI08 — superuser bypass is the caller's responsibility)."""
    return _effective_levels(_matching_perms(session, user, None))


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
    (a subset of USER/ROLE/TEAM/UNIT/PROJECT/PUBLIC). Empty list when the user has no
    matching active permission. One batched query over the given assets (no N+1)."""
    if not asset_ids:
        return {}

    scopes = resolve_user_scopes(session, user)
    now = datetime.utcnow()

    perms = session.exec(
        select(AssetPermission).where(
            AssetPermission.asset.in_(asset_ids),
            AssetPermission.is_active == True,  # noqa: E712
        )
    ).all()

    matched: Dict[int, Set[str]] = {}
    for p in perms:
        if not _is_valid_now(p.valid_from, p.valid_to, now):
            continue
        granted = False
        if p.target_type == SCOPE_PUBLIC:
            granted = True
        elif p.target_type in scopes and p.target_code in scopes[p.target_type]:
            granted = True
        if granted:
            matched.setdefault(p.asset, set()).add(p.target_type)

    return {asset_id: sorted(types) for asset_id, types in matched.items()}
