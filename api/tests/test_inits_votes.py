"""Initiative votes (HU-IN04) — specs/005-explore-initiatives US3."""
from sqlmodel import select

from app.inits.internal.models import Collaboration
from tests.inits_helpers import (
    COLLAB, data, mk_init, mk_perm, override, seed_privileges, user,
)


def _world(session, can_edit=True):
    init = mk_init(session, name="Voted", status="ACCEPTED")
    mk_perm(session, init.id, "PUBLIC", "ALL", access_level="VIEW")
    seed_privileges(session, profile=COLLAB, options=("EXPLORE",), can_edit=can_edit)
    return init


def _vote(client, init_id, content):
    return client.put(f"/api/collaborations/votes/init/{init_id}", json={"content": content})


def test_vote_toggle_switch_and_clear(session, client):
    init = _world(session)
    override(user(1, profile=COLLAB))

    body = data(_vote(client, init.id, "POSITIVE"))
    assert (body["positive"], body["negative"], body["my_vote"], body["score"]) == (1, 0, "POSITIVE", 1)

    body = data(_vote(client, init.id, "NEGATIVE"))  # switch
    assert (body["positive"], body["negative"], body["my_vote"]) == (0, 1, "NEGATIVE")

    body = data(_vote(client, init.id, "NEGATIVE"))  # same again → withdrawn
    assert (body["positive"], body["negative"], body["my_vote"]) == (0, 0, None)

    _vote(client, init.id, "POSITIVE")
    resp = client.delete(f"/api/collaborations/votes/init/{init.id}")
    assert resp.status_code == 200 and data(resp)["my_vote"] is None
    assert client.delete(f"/api/collaborations/votes/init/{init.id}").status_code == 404


def test_one_active_vote_per_user_and_null_workflow_status(session, client):
    init = _world(session)
    override(user(1, profile=COLLAB))
    for v in ("POSITIVE", "NEGATIVE", "POSITIVE"):
        _vote(client, init.id, v)
    active = session.exec(select(Collaboration).where(
        Collaboration.type == "VOTE", Collaboration.is_active == True)).all()  # noqa: E712
    assert len(active) == 1 and active[0].user_id == 1
    assert all(r.workflow_status is None for r in session.exec(select(Collaboration)).all())


def test_tally_counts_everyone_with_my_vote_per_caller(session, client):
    init = _world(session)
    for uid, v in ((1, "POSITIVE"), (2, "POSITIVE"), (3, "NEGATIVE")):
        override(user(uid, profile=COLLAB))
        _vote(client, init.id, v)
    override(user(3, profile=COLLAB))
    body = data(client.get(f"/api/collaborations/votes/init/{init.id}"))
    assert (body["positive"], body["negative"], body["score"], body["my_vote"]) == (2, 1, 1, "NEGATIVE")


def test_voter_is_the_session_user(session, client):
    init = _world(session)
    override(user(7, profile=COLLAB))
    client.put(f"/api/collaborations/votes/init/{init.id}",
               json={"content": "POSITIVE", "user_id": 99})
    row = session.exec(select(Collaboration).where(Collaboration.type == "VOTE")).one()
    assert row.user_id == 7


def test_invalid_content_is_400(session, client):
    init = _world(session)
    override(user(1, profile=COLLAB))
    assert _vote(client, init.id, "MAYBE").status_code == 400


def test_no_view_access_is_403(session, client):
    init = mk_init(session, status="ACCEPTED")  # no grant
    seed_privileges(session, profile=COLLAB, options=("EXPLORE",), can_edit=True)
    override(user(1, profile=COLLAB))
    assert _vote(client, init.id, "POSITIVE").status_code == 403
    assert client.get(f"/api/collaborations/votes/init/{init.id}").status_code == 403


def test_read_only_privilege_cannot_vote(session, client):
    init = _world(session, can_edit=False)
    override(user(1, profile=COLLAB))
    assert _vote(client, init.id, "POSITIVE").status_code == 403
    assert client.get(f"/api/collaborations/votes/init/{init.id}").status_code == 200
