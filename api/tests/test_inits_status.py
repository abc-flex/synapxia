"""Initiative owner status moves (US3) — policy + `PUT /api/initiatives/{id}`.

Allowed from Initiative Management: ACCEPTED → IN_PROGRESS / DELIVERED /
ARCHIVED, IN_PROGRESS → DELIVERED / ARCHIVED, DELIVERED → ARCHIVED. Each writes
exactly one HANDLED collaboration (KICKOFF / DELIVERY / ARCHIVING) by the actor
in the same transaction; everything else is refused with 400 and writes nothing.
"""
import itertools

import pytest
from sqlmodel import select

from app.inits.internal import status_service as svc
from app.inits.internal.models import Collaboration, Initiative
from tests.inits_helpers import data, mk_init, mk_perm, override, seed_core_lists, seed_privileges, user

STATUSES = ["ACTIVATED", "FEEDBACK", "ACCEPTED", "REJECTED", "IN_PROGRESS", "DELIVERED", "ARCHIVED"]
ALLOWED = {
    ("ACCEPTED", "IN_PROGRESS"): "KICKOFF",
    ("ACCEPTED", "DELIVERED"): "DELIVERY",
    ("ACCEPTED", "ARCHIVED"): "ARCHIVING",
    ("IN_PROGRESS", "DELIVERED"): "DELIVERY",
    ("IN_PROGRESS", "ARCHIVED"): "ARCHIVING",
    ("DELIVERED", "ARCHIVED"): "ARCHIVING",
}
PAIRS = [(a, b) for a, b in itertools.product(STATUSES, STATUSES) if a != b]


# --- Pure policy -------------------------------------------------------------

@pytest.mark.parametrize("current,new", PAIRS)
def test_full_transition_matrix(current, new):
    if (current, new) in ALLOWED:
        assert svc.validate_transition(current, new) == ALLOWED[(current, new)]
    else:
        with pytest.raises(svc.StatusTransitionForbidden):
            svc.validate_transition(current, new)


@pytest.mark.parametrize("new", [None, "", "  ", "ACCEPTED", "accepted", "3-ACCEPTED"])
def test_unchanged_or_blank_is_not_a_transition(new):
    assert svc.validate_transition("ACCEPTED", new) is None


def test_tolerates_prefix_and_case():
    assert svc.validate_transition("3-accepted", "in_progress") == "KICKOFF"


def test_allowed_statuses_for():
    assert svc.allowed_statuses_for("ACCEPTED") == ["ACCEPTED", "IN_PROGRESS", "DELIVERED", "ARCHIVED"]
    assert svc.allowed_statuses_for("IN_PROGRESS") == ["IN_PROGRESS", "DELIVERED", "ARCHIVED"]
    assert svc.allowed_statuses_for("DELIVERED") == ["DELIVERED", "ARCHIVED"]
    for locked in ("ACTIVATED", "FEEDBACK", "REJECTED", "ARCHIVED", "WHATEVER"):
        assert svc.allowed_statuses_for(locked) == [locked]


# --- HTTP ---------------------------------------------------------------------

def _setup(session, status):
    seed_privileges(session)
    seed_core_lists(session)
    init = mk_init(session, status=status)
    mk_perm(session, init.id, "USER", "7", access_level="MANAGE")
    override(user(7))
    return init


def _collabs(session, init_id):
    return session.exec(select(Collaboration).where(Collaboration.init == init_id)).all()


@pytest.mark.parametrize("current,new", list(ALLOWED))
def test_allowed_move_writes_one_handled_collaboration(client, session, current, new):
    init = _setup(session, current)
    r = client.put(f"/api/initiatives/{init.id}", json={"status": new})
    assert r.status_code == 200
    body = data(r)
    assert body["status"] == new
    assert body["allowed_statuses"] == svc.allowed_statuses_for(new)

    rows = _collabs(session, init.id)
    assert len(rows) == 1
    c = rows[0]
    assert (c.type, c.workflow_status, c.user_id, c.content) == (
        ALLOWED[(current, new)], "HANDLED", 7, None)


@pytest.mark.parametrize("current,new", [p for p in PAIRS if p not in ALLOWED])
def test_refused_move_writes_nothing(client, session, current, new):
    init = _setup(session, current)
    r = client.put(f"/api/initiatives/{init.id}", json={"status": new, "name": "Changed"})
    assert r.status_code == 400
    session.expire_all()
    row = session.get(Initiative, init.id)
    assert row.status == current and row.name == "Init"
    assert _collabs(session, init.id) == []


def test_core_edit_without_status_change_writes_nothing(client, session):
    init = _setup(session, "IN_PROGRESS")
    r = client.put(f"/api/initiatives/{init.id}", json={"description": "d", "status": "IN_PROGRESS"})
    assert r.status_code == 200
    assert _collabs(session, init.id) == []


def test_moves_never_create_pending_rows(client, session):
    init = _setup(session, "ACCEPTED")
    for new in ("IN_PROGRESS", "DELIVERED", "ARCHIVED"):
        assert client.put(f"/api/initiatives/{init.id}", json={"status": new}).status_code == 200
    rows = _collabs(session, init.id)
    assert [c.type for c in rows] == ["KICKOFF", "DELIVERY", "ARCHIVING"]
    assert {c.workflow_status for c in rows} == {"HANDLED"}


def test_with_access_exposes_allowed_statuses(client, session):
    _setup(session, "DELIVERED")
    rows = data(client.get("/api/initiatives/with-access"))
    assert rows[0]["allowed_statuses"] == ["DELIVERED", "ARCHIVED"]
