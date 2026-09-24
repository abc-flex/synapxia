"""Per-initiative access resolution (T012) — the shared engine bound to
`init_permissions` must behave exactly like the asset side."""
import pytest

from app.collab.internal.models import Assignment, Project
from app.inits.internal import permissions_service as svc
from tests.inits_helpers import FUTURE, NOW, PAST, mk_init, mk_perm, superuser, user


def _assign(session, user_id, *, role="MEMBER", team=None):
    session.add(Assignment(user_id=user_id, role=role, team=team,
                           is_active=True, valid_from=NOW))
    session.commit()


def test_manage_beats_view(session):
    i = mk_init(session)
    mk_perm(session, i.id, "USER", "1", access_level="VIEW")
    mk_perm(session, i.id, "USER", "1", access_level="MANAGE")
    assert svc.user_init_access(session, user(1), i.id) == "MANAGE"


def test_future_start_grants_nothing_yet(session):
    i = mk_init(session)
    mk_perm(session, i.id, "USER", "1", valid_from=FUTURE)
    assert svc.user_init_access(session, user(1), i.id) is None


def test_revoked_grant_grants_nothing(session):
    i = mk_init(session)
    mk_perm(session, i.id, "USER", "1", valid_from=PAST, valid_to=PAST)
    assert svc.user_init_access(session, user(1), i.id) is None


def test_public_grants_view_to_anyone(session):
    i = mk_init(session)
    mk_perm(session, i.id, "PUBLIC", "ALL", access_level="VIEW")
    assert svc.user_init_access(session, user(42), i.id) == "VIEW"


@pytest.mark.parametrize("target_type,target_code,setup", [
    ("UNIT", "ENG", None),
    ("ROLE", "TL", "role"),
    ("TEAM", "CORE", "team"),
    ("PROJECT", "P1", "project"),
])
def test_scope_matching(session, target_type, target_code, setup):
    i = mk_init(session)
    if setup == "role":
        _assign(session, 1, role="TL", team="X")
    elif setup in ("team", "project"):
        _assign(session, 1, team="CORE")
    if setup == "project":
        session.add(Project(code="P1", name="P1", team="CORE", status="ACTIVE"))
        session.commit()
    mk_perm(session, i.id, target_type, target_code, access_level="MANAGE")
    assert svc.user_init_access(session, user(1, unit="ENG"), i.id) == "MANAGE"


def test_accessible_inits_lists_only_granted(session):
    a, b = mk_init(session, name="A"), mk_init(session, name="B")
    mk_perm(session, a.id, "USER", "1", access_level="VIEW")
    assert svc.accessible_inits(session, user(1)) == {a.id: "VIEW"}
    assert b.id not in svc.accessible_inits(session, user(1))


def test_guards(session):
    i = mk_init(session)
    mk_perm(session, i.id, "USER", "1", access_level="VIEW")
    svc.require_init_view(session, user(1), i.id)
    with pytest.raises(svc.InitAccessForbidden):
        svc.require_init_manage(session, user(1), i.id)
    with pytest.raises(svc.InitAccessForbidden):
        svc.require_init_view(session, user(2), i.id)


def test_superuser_bypasses_both_guards(session):
    i = mk_init(session)
    svc.require_init_manage(session, superuser(), i.id)
    svc.require_init_view(session, superuser(), i.id)
    assert svc.user_init_access(session, superuser(), i.id) == "MANAGE"
