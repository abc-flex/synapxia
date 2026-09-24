"""Initiative History + Discussion reads — `/api/collaborations/*/init/{id}`."""
from datetime import timedelta

from app.inits.internal.models import Collaboration
from tests.inits_helpers import (
    NOW, data, mk_init, mk_perm, mk_user_row, override, seed_privileges, user,
)


def _collab(session, init, user_id, type_, *, ws=None, content=None, parent=None,
            at=None, active=True):
    c = Collaboration(init=init, user_id=user_id, type=type_, workflow_status=ws,
                      content=content, parent=parent, created_at=at or NOW,
                      is_active=active)
    session.add(c)
    session.commit()
    session.refresh(c)
    return c


def _setup(session, grant=True):
    seed_privileges(session, can_edit=False)
    init = mk_init(session, created_at=NOW - timedelta(days=10))
    if grant:
        mk_perm(session, init.id, "USER", "1", access_level="VIEW")
    mk_user_row(session, 1, "owner")
    mk_user_row(session, 2, "reviewer")
    return init


def test_history_newest_first_with_created_marker(client, session):
    init = _setup(session)
    _collab(session, init.id, 1, "ACTIVATION", ws="HANDLED", at=NOW - timedelta(days=9))
    _collab(session, init.id, 2, "DIAGNOSIS", ws="HANDLED", at=NOW - timedelta(days=5))
    _collab(session, init.id, 1, "KICKOFF", ws="HANDLED", at=NOW - timedelta(days=1))
    _collab(session, init.id, 2, "COMMENT", content="nice", at=NOW - timedelta(days=2))
    _collab(session, init.id, 2, "COMMENT", content="gone", active=False)
    override(user(1))

    rows = data(client.get(f"/api/collaborations/history/init/{init.id}"))
    assert [r["type"] for r in rows] == ["KICKOFF", "COMMENT", "DIAGNOSIS", "ACTIVATION", "CREATED"]
    assert rows[0]["actor"] == "owner" and rows[0]["summary"] == "kicked off the initiative"
    assert rows[1]["content"] == "nice"
    assert rows[2]["content"] is None
    assert rows[-1]["id"] is None and rows[-1]["actor"] is None


def test_history_pagination(client, session):
    init = _setup(session)
    for d in range(3):
        _collab(session, init.id, 1, "COMMENT", content=str(d), at=NOW - timedelta(days=d))
    override(user(1))
    rows = data(client.get(f"/api/collaborations/history/init/{init.id}",
                           params={"skip": 1, "limit": 2}))
    assert [r["content"] for r in rows] == ["1", "2"]


def test_discussion_threads_oldest_first(client, session):
    init = _setup(session)
    q = _collab(session, init.id, 2, "QUESTION", content="Q?", at=NOW - timedelta(days=3))
    _collab(session, init.id, 1, "ANSWER", content="A.", parent=q.id, at=NOW - timedelta(days=2))
    _collab(session, init.id, 2, "COMMENT", content="C", at=NOW - timedelta(days=1))
    _collab(session, init.id, 1, "KICKOFF", ws="HANDLED")
    override(user(1))

    rows = data(client.get(f"/api/collaborations/discussion/init/{init.id}"))
    assert [(r["type"], r["author"]) for r in rows] == [
        ("QUESTION", "reviewer"), ("ANSWER", "owner"), ("COMMENT", "reviewer")]
    assert rows[1]["parent"] == q.id and rows[1]["init"] == init.id


def test_reads_require_view_and_existing_initiative(client, session):
    init = _setup(session, grant=False)
    override(user(1))
    for path in ("history", "discussion"):
        assert client.get(f"/api/collaborations/{path}/init/{init.id}").status_code == 403
        assert client.get(f"/api/collaborations/{path}/init/999").status_code == 404
