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
from datetime import datetime
from typing import Dict, List, Set

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


def _is_valid_now(valid_from, valid_to, now: datetime) -> bool:
    """True if a temporal row (assignment/permission) is in effect at ``now``."""
    if valid_from is not None and valid_from > now:
        return False
    if valid_to is not None and valid_to <= now:
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
