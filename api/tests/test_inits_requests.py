"""Initiative requests / notifications / single-collaboration read
(specs/005-explore-initiatives, contract #10–#13)."""
from tests.inits_helpers import (
    data, mk_collab, mk_init, mk_user_row, override, superuser, user,
)


# ── GET /api/collaborations/{id} ────────────────────────────────────────────

def test_owner_reads_own_collaboration_with_initiative(session, client):
    mk_user_row(session, 1)
    init = mk_init(session, name="Alpha", status="ACTIVATED")
    row = mk_collab(session, init.id, 1, "DIAGNOSIS", "PENDING")
    override(user(1))
    resp = client.get(f"/api/collaborations/{row.id}")
    assert resp.status_code == 200
    body = data(resp)
    assert body["type"] == "DIAGNOSIS" and body["actor_name"] == "u1"
    assert body["initiative"]["name"] == "Alpha"


def test_foreign_collaboration_is_404(session, client):
    mk_user_row(session, 1)
    init = mk_init(session, status="ACTIVATED")
    row = mk_collab(session, init.id, 1, "DIAGNOSIS", "PENDING")
    override(user(2))
    assert client.get(f"/api/collaborations/{row.id}").status_code == 404


def test_superuser_reads_any_collaboration(session, client):
    mk_user_row(session, 1)
    init = mk_init(session, status="ACTIVATED")
    row = mk_collab(session, init.id, 1, "DIAGNOSIS", "PENDING")
    override(superuser())
    assert client.get(f"/api/collaborations/{row.id}").status_code == 200


def test_missing_collaboration_is_404(session, client):
    override(user(1))
    assert client.get("/api/collaborations/9999").status_code == 404


# ── Derivation (contract #10) and feed (#11) ────────────────────────────────

from datetime import timedelta  # noqa: E402

from tests.inits_helpers import NOW  # noqa: E402


def _at(minutes):
    # In the past: rows written by the API itself are stamped "now" and must
    # sort after the fixtures, as they would in real use.
    return NOW - timedelta(hours=1) + timedelta(minutes=minutes)


def _requests(client, state="PENDING", **params):
    resp = client.get("/api/collaborations/requests", params={"state": state, **params})
    assert resp.status_code == 200, resp.text
    return data(resp)


def test_newest_row_of_a_thread_wins(session, client):
    init = mk_init(session, status="ACTIVATED")
    mk_collab(session, init.id, 2, "DIAGNOSIS", "PENDING", created_at=_at(1))
    mk_collab(session, init.id, 2, "DIAGNOSIS", "HANDLED", created_at=_at(2))
    init.status = "ACCEPTED"
    session.add(init)
    session.commit()
    override(user(2))
    assert _requests(client) == []
    handled = _requests(client, "HANDLED")
    assert len(handled) == 1 and handled[0]["roles"] == ["REVIEWER"]


def test_self_other_handled_derivation(session, client):
    # Reviewer owes the diagnosis → SELF; proposer waits → OTHER.
    init = mk_init(session, name="Loop", status="ACTIVATED")
    mk_collab(session, init.id, 1, "ACTIVATION", "HANDLED", created_at=_at(1))
    diag = mk_collab(session, init.id, 2, "DIAGNOSIS", "PENDING", created_at=_at(2))

    override(user(2))
    row = _requests(client)[0]
    assert (row["awaited_party"], row["pending_collab_id"], row["pending_collab_type"]) == (
        "SELF", diag.id, "DIAGNOSIS")

    override(user(1))
    row = _requests(client)[0]
    assert (row["state"], row["awaited_party"], row["pending_collab_id"]) == ("PENDING", "OTHER", None)
    assert row["roles"] == ["PROPOSER"] and row["init_name"] == "Loop"


def test_owed_is_evaluated_before_status(session, client):
    # ACCEPTED (terminal status) but the acceptance notice is unacknowledged.
    init = mk_init(session, status="ACCEPTED")
    mk_collab(session, init.id, 1, "ACTIVATION", "HANDLED", created_at=_at(1))
    notice = mk_collab(session, init.id, 1, "ACCEPTANCE", "PENDING", created_at=_at(2))
    override(user(1))
    row = _requests(client)[0]
    assert (row["state"], row["awaited_party"], row["pending_collab_id"]) == ("PENDING", "SELF", notice.id)


def test_one_row_per_initiative_across_roles(session, client):
    init = mk_init(session, status="ACTIVATED")  # an admin reviewing their own
    mk_collab(session, init.id, 1, "ACTIVATION", "HANDLED", created_at=_at(1))
    mk_collab(session, init.id, 1, "DIAGNOSIS", "PENDING", created_at=_at(2))
    override(user(1))
    rows = _requests(client)
    assert len(rows) == 1 and set(rows[0]["roles"]) == {"PROPOSER", "REVIEWER"}


def test_log_and_community_rows_never_open_a_thread(session, client):
    init = mk_init(session, status="DELIVERED")
    for t, wf in (("KICKOFF", "HANDLED"), ("DELIVERY", "HANDLED"), ("ARCHIVING", "HANDLED"),
                  ("DELIVERY", "PENDING"), ("VOTE", None), ("COMMENT", None),
                  ("QUESTION", None), ("ANSWER", None)):
        mk_collab(session, init.id, 1, t, wf)
    override(user(1))
    assert _requests(client) == [] and _requests(client, "HANDLED") == []
    assert data(client.get("/api/collaborations/notifications"))["total"] == 0


def test_feed_is_self_only_newest_first_and_capped(session, client):
    for i in range(3):
        init = mk_init(session, name=f"owed{i}", status="ACTIVATED")
        mk_collab(session, init.id, 2, "DIAGNOSIS", "PENDING", created_at=_at(i))
    waiting = mk_init(session, name="waiting", status="ACTIVATED")
    mk_collab(session, waiting.id, 2, "ACTIVATION", "HANDLED", created_at=_at(10))
    override(user(2))
    feed = data(client.get("/api/collaborations/notifications", params={"limit": 2}))
    assert feed["total"] == 3
    assert [i["init_name"] for i in feed["items"]] == ["owed2", "owed1"]
    assert all(i["type"] == "DIAGNOSIS" for i in feed["items"])
    # Strict subset of the requests list.
    pending_ids = {r["pending_collab_id"] for r in _requests(client)}
    assert {i["id"] for i in feed["items"]} <= pending_ids


def test_feed_is_isolated_per_user(session, client):
    init = mk_init(session, status="ACTIVATED")
    mk_collab(session, init.id, 2, "DIAGNOSIS", "PENDING")
    override(user(3))
    assert data(client.get("/api/collaborations/notifications")) == {"items": [], "total": 0}


def test_requests_pagination(session, client):
    for i in range(3):
        init = mk_init(session, name=f"i{i}", status="ACTIVATED")
        mk_collab(session, init.id, 2, "DIAGNOSIS", "PENDING", created_at=_at(i))
    override(user(2))
    assert [r["init_name"] for r in _requests(client, skip=1, limit=1)] == ["i1"]


# ── Acknowledge (contract #12) ─────────────────────────────────────────────

def test_acknowledge_outcome_leaves_the_feed(session, client):
    init = mk_init(session, status="ACCEPTED")
    mk_collab(session, init.id, 1, "ACTIVATION", "HANDLED", created_at=_at(1))
    notice = mk_collab(session, init.id, 1, "ACCEPTANCE", "PENDING", created_at=_at(2))
    override(user(1))
    resp = client.post(f"/api/collaborations/notifications/{notice.id}/acknowledge")
    assert resp.status_code == 200 and data(resp)["workflow_status"] == "HANDLED"
    assert data(client.get("/api/collaborations/notifications"))["total"] == 0
    assert _requests(client, "HANDLED")[0]["init"] == init.id
    # Idempotent: acknowledging again does not add another row.
    again = client.post(f"/api/collaborations/notifications/{notice.id}/acknowledge")
    assert again.status_code == 200
    from app.inits.internal.models import Collaboration
    from sqlmodel import select
    handled = session.exec(select(Collaboration).where(
        Collaboration.type == "ACCEPTANCE", Collaboration.workflow_status == "HANDLED")).all()
    assert len(handled) == 1


def test_acknowledge_refuses_work_items_and_foreign_rows(session, client):
    init = mk_init(session, status="ACTIVATED")
    diag = mk_collab(session, init.id, 2, "DIAGNOSIS", "PENDING")
    notice = mk_collab(session, init.id, 1, "REJECTION", "PENDING")
    comment = mk_collab(session, init.id, 2, "COMMENT", None, content="hi")
    override(user(2))
    assert client.post(f"/api/collaborations/notifications/{diag.id}/acknowledge").status_code == 400
    assert client.post(f"/api/collaborations/notifications/{notice.id}/acknowledge").status_code == 404
    assert client.post(f"/api/collaborations/notifications/{comment.id}/acknowledge").status_code == 404
    assert client.post("/api/collaborations/notifications/9999/acknowledge").status_code == 404


def test_collaboration_detail_reports_current_thread_status(session, client):
    init = mk_init(session, status="ACCEPTED")
    notice = mk_collab(session, init.id, 1, "ACCEPTANCE", "PENDING", created_at=_at(1))
    override(user(1))
    assert data(client.get(f"/api/collaborations/{notice.id}"))["current_status"] == "PENDING"
    client.post(f"/api/collaborations/notifications/{notice.id}/acknowledge")
    assert data(client.get(f"/api/collaborations/{notice.id}"))["current_status"] == "HANDLED"


def test_collaboration_detail_is_limited_to_workflow_rows(session, client):
    init = mk_init(session, status="ACCEPTED")
    comment = mk_collab(session, init.id, 1, "COMMENT", None, content="hi")
    override(user(1))
    assert client.get(f"/api/collaborations/{comment.id}").status_code == 404
