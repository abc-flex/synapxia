"""Per-resource permission engine shared by every domain (Constitution —
"Established Domain Patterns: Per-resource permissions").

A grant table (``asset_permissions``, ``init_permissions``, …) keys a resource to a
recipient: ``target_type`` is PUBLIC, or ``(target_type, target_code)`` matches one
of the current user's scopes:

  - USER    → the user's own id (target_code stores the id as a string)
  - UNIT    → the user's business unit (``users.unit``)
  - ROLE    → a role the user holds via an active collab assignment
  - TEAM    → a team the user belongs to via an active collab assignment
  - PROJECT → a project belonging to one of the user's teams

A grant is never deleted — it is *revoked*, and revoking sets ``valid_to``. So a
single temporal check (``valid_from``/``valid_to``) decides whether it is in
effect, and there is deliberately no ``is_active`` flag on grant tables.

Every function takes the grant ``model`` and the name of its resource FK column
(``"asset"``, ``"init"``) so each domain binds the engine to its own table in a
thin wrapper (``lib.internal.permissions_service``,
``inits.internal.permissions_service``) instead of copying it.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from sqlalchemy import and_, or_
from sqlmodel import Session, select

from ..admin.internal.models import User
from ..collab.internal.models import Assignment, Project

# target_type values (TARGET_TYPE list).
SCOPE_USER = "USER"
SCOPE_ROLE = "ROLE"
SCOPE_TEAM = "TEAM"
SCOPE_UNIT = "UNIT"
SCOPE_PROJECT = "PROJECT"
SCOPE_PUBLIC = "PUBLIC"

# access_level values (ACCESS_LEVEL list).
ACCESS_VIEW = "VIEW"
ACCESS_MANAGE = "MANAGE"


def as_naive_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Normalize to naive UTC so naive (SQLite) and tz-aware (Postgres
    TIMESTAMPTZ) datetimes can be compared without
    'can't compare offset-naive and offset-aware datetimes'."""
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def is_valid_now(valid_from, valid_to, now: datetime) -> bool:
    """True if a temporal row (assignment/permission) is in effect at ``now``."""
    vf = as_naive_utc(valid_from)
    vt = as_naive_utc(valid_to)
    n = as_naive_utc(now)
    if vf is not None and vf > n:
        return False
    if vt is not None and vt <= n:
        return False
    return True


def not_revoked_clause(model: Any, now: Optional[datetime] = None):
    """SQL predicate for "this grant has not been revoked".

    A grant counts as live while ``valid_to`` is NULL or still in the future —
    the same boundary ``is_valid_now`` uses (``valid_to <= now`` → no longer in
    effect). ``valid_from`` is deliberately NOT part of this predicate: a grant
    dated to start next month is not revoked, it is merely not in effect yet, and
    it must stay visible and manageable in the permissions list until it starts.
    """
    n = now or datetime.utcnow()
    return or_(
        model.valid_to == None,  # noqa: E711
        model.valid_to > n,
    )


def is_revoked(grant: Any, now: Optional[datetime] = None) -> bool:
    """Python twin of :func:`not_revoked_clause` — True once ``valid_to`` has
    passed. Goes through ``as_naive_utc`` so a tz-aware TIMESTAMPTZ read back
    from Postgres can be compared against a naive UTC "now"."""
    vt = as_naive_utc(grant.valid_to)
    if vt is None:
        return False
    return vt <= as_naive_utc(now or datetime.utcnow())


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
    active = [a for a in assignments if is_valid_now(a.valid_from, a.valid_to, now)]

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


def matching_grants(
    session: Session,
    user: User,
    model: Any,
    fk: str,
    ids: Optional[List[int]] = None,
) -> List[Any]:
    """Grant rows in effect right now that give ``user`` access — PUBLIC rows or
    rows matching one of the user's scope pairs. Revoked grants carry a past
    ``valid_to`` and are filtered out by the same temporal check. With
    ``ids=None`` the scan is table-wide but SQL-bounded to the user's own scope
    pairs, so it returns at most the user's grant rows — not the table."""
    scopes = resolve_user_scopes(session, user)
    now = datetime.utcnow()

    scope_clauses = [model.target_type == SCOPE_PUBLIC]
    for target_type, codes in scopes.items():
        if codes:
            scope_clauses.append(and_(
                model.target_type == target_type,
                model.target_code.in_(list(codes)),
            ))

    query = select(model).where(or_(*scope_clauses))
    if ids is not None:
        if not ids:
            return []
        query = query.where(getattr(model, fk).in_(ids))

    grants = session.exec(query).all()
    return [g for g in grants if is_valid_now(g.valid_from, g.valid_to, now)]


def effective_levels(grants: List[Any], fk: str) -> Dict[int, str]:
    """Reduce matched grant rows to one effective level per resource — MANAGE
    beats everything else; any non-MANAGE grant counts as VIEW-equivalent."""
    levels: Dict[int, str] = {}
    for g in grants:
        rid = getattr(g, fk)
        level = ACCESS_MANAGE if g.access_level == ACCESS_MANAGE else ACCESS_VIEW
        if levels.get(rid) != ACCESS_MANAGE:
            levels[rid] = level
    return levels


def user_scopes_for(
    session: Session, user: User, model: Any, fk: str, ids: List[int]
) -> Dict[int, List[str]]:
    """For each resource id, the sorted scope-types by which ``user`` is granted
    access (subset of USER/ROLE/TEAM/UNIT/PROJECT/PUBLIC). One batched query over
    the given ids (no N+1); resources with no matching grant are absent."""
    if not ids:
        return {}

    scopes = resolve_user_scopes(session, user)
    now = datetime.utcnow()

    grants = session.exec(
        select(model).where(getattr(model, fk).in_(ids))
    ).all()

    matched: Dict[int, Set[str]] = {}
    for g in grants:
        if not is_valid_now(g.valid_from, g.valid_to, now):
            continue
        if g.target_type == SCOPE_PUBLIC or (
            g.target_type in scopes and g.target_code in scopes[g.target_type]
        ):
            matched.setdefault(getattr(g, fk), set()).add(g.target_type)

    return {rid: sorted(types) for rid, types in matched.items()}
