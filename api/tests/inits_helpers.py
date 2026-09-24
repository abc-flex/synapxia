"""Shared fixtures-as-functions for the Initiative Management test modules.

Same style as the per-file helpers in test_lib_access_enforcement.py
(`_user`, `_override`, `_seed_privileges`, `_mk_perm` with NOW/PAST/FUTURE),
gathered once because six `test_inits_*.py` modules need the same ones.
"""
from datetime import datetime, timedelta
from types import SimpleNamespace

from app.admin.internal.models import ListItem, Privilege, User
from app.auth.routes import current_active_user
from app.inits.internal.models import (
    Criteria, Diagnostic, FavoriteInit, InitPermission, Initiative,
)
from app.main import app

NOW = datetime.utcnow()
PAST = NOW - timedelta(days=1)
FUTURE = NOW + timedelta(days=1)

OWNER = "ADMINISTRATIVE"
COLLAB = "COLLABORATOR"


def user(id=1, unit="ENG", superuser=False, profile=OWNER):
    return SimpleNamespace(
        id=id, username=f"u{id}", unit=unit, profile=profile,
        is_superuser=superuser, is_active=True,
    )


def superuser(uid=99):
    return user(id=uid, superuser=True, profile="ADMINISTRATOR")


def override(u):
    app.dependency_overrides[current_active_user] = lambda: u


def mk_user_row(session, id, username=None, profile=OWNER):
    """A real users row — needed where a service resolves actor usernames."""
    username = username or f"u{id}"
    row = User(
        id=id, username=username, email=f"{username}@x.co",
        password_hash="x", first_name="F", last_name="L",
        profile=profile, unit="ENG",
    )
    session.add(row)
    session.commit()
    return row


def seed_privileges(session, profile=OWNER, options=("INITIATIVES",), can_edit=True):
    for option in options:
        session.add(Privilege(
            profile=profile, module="INITS", option=option,
            can_edit=can_edit, is_active=True))
    session.commit()


def mk_init(session, id=None, name="Init", status="ACCEPTED", **kw):
    row = Initiative(
        id=id, name=name, status=status,
        expected_impact=kw.pop("expected_impact", "OTHER"),
        priority_level=kw.pop("priority_level", "LOW"),
        **kw,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def mk_perm(session, init, target_type="USER", target_code="1", *,
            access_level="MANAGE", valid_from=None, valid_to=None):
    p = InitPermission(
        init=init, target_type=target_type, target_code=target_code,
        access_level=access_level, valid_from=valid_from or NOW, valid_to=valid_to,
    )
    session.add(p)
    session.commit()
    session.refresh(p)
    return p


def mk_fav(session, user_id, init, active=True):
    session.add(FavoriteInit(user_id=user_id, init=init, is_active=active))
    session.commit()


def mk_list(session, list_code, values, lang="en"):
    """list_items rows; `values` is [(value, label), ...]."""
    for i, (value, label) in enumerate(values):
        session.add(ListItem(list=list_code, lang=lang, value=value,
                             label=label, sort_order=(i + 1) * 10))
    session.commit()


def seed_core_lists(session):
    """The list values Initiative Management validates against."""
    mk_list(session, "INITIATIVE_TYPE",
            [("EXPLORATION", "Exploration"), ("PROTOTYPING", "Prototyping"),
             ("IMPLEMENTATION", "Implementation")])
    mk_list(session, "EXPECTED_IMPACT", [("OTHER", "Other"), ("INNOVATION", "Innovation")])
    mk_list(session, "PRIORITY_LEVEL", [("HIGH", "High"), ("LOW", "Low")])
    mk_list(session, "RELATION_TYPE", [("USED_BY", "Used By"), ("CONTAINS", "Contains")])


def mk_criteria(session, code, name=None, list_code=None, active=True):
    row = Criteria(code=code, name=name or code, list=list_code or code,
                   is_active=active)
    session.add(row)
    session.commit()
    return row


def mk_diag(session, init, criteria, creator, reviewer=None, rationale=None):
    session.add(Diagnostic(init=init, criteria=criteria, creator_score=creator,
                           reviewer_score=reviewer, rationale=rationale))
    session.commit()


def data(resp):
    """Unwrap the global `{data, error, meta}` envelope."""
    return resp.json()["data"]
