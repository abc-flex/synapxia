"""Asset history tests (HU-LI10) — Constitution Principle II/III.

History is the read-side of the Asset Action Service: ``get_asset_history``
aggregates every active ``actions`` row for an asset (votes, comments,
questions, answers, workflow actions) plus a synthetic CREATED marker from the
asset row, newest first — no new table, no writes.

Two layers, like the foro/votes suites:
1. Service logic against the in-memory SQLite ``session`` fixture (explicit
   ``created_at`` values make ordering deterministic).
2. Route contract: auth-gated + advertised in OpenAPI.
"""

from datetime import datetime, timedelta
from types import SimpleNamespace

from app.main import app
from app.auth.routes import current_active_user
from app.lib.internal import actions_service as svc
from app.lib.internal.models import Asset, Action
from app.admin.internal.models import User


T0 = datetime(2026, 1, 1, 12, 0, 0)


def _mk_asset(session, name="Asset", created_at=T0, is_active=True):
    asset = Asset(name=name, status="PUBLISHED", is_active=is_active, created_at=created_at)
    session.add(asset)
    session.commit()
    session.refresh(asset)
    return asset


def _mk_action(session, asset_id, user_id, type, created_at,
               content=None, workflow_status=None, is_active=True):
    a = Action(
        asset=asset_id, user_id=user_id, type=type, content=content,
        workflow_status=workflow_status, is_active=is_active, created_at=created_at,
    )
    session.add(a)
    session.commit()
    session.refresh(a)
    return a


def _mk_user(session, id, username):
    u = User(
        id=id, username=username, email=f"{username}@x.co",
        password_hash="x", first_name="F", last_name="L",
        profile="ADMINISTRATOR", unit="HQ",
    )
    session.add(u)
    session.commit()
    return u


def _superuser():
    return SimpleNamespace(
        id=1, username="tester", profile="ADMINISTRATOR",
        is_superuser=True, is_active=True,
    )


# --- Service logic ---------------------------------------------------------

def test_history_newest_first_with_created_marker(session):
    asset = _mk_asset(session, created_at=T0)
    _mk_action(session, asset.id, 1, svc.TYPE_COMMENT, T0 + timedelta(minutes=1), content="hi")
    _mk_action(session, asset.id, 1, svc.TYPE_VOTE, T0 + timedelta(minutes=2), content="POSITIVE")

    hist = svc.get_asset_history(session, asset.id)
    # newest first: VOTE (t+2), COMMENT (t+1), then the synthetic CREATED (t0).
    assert [e["type"] for e in hist] == [svc.TYPE_VOTE, svc.TYPE_COMMENT, "CREATED"]
    assert hist[-1]["id"] is None  # synthetic marker has no action id


def test_history_includes_all_interaction_types(session):
    asset = _mk_asset(session, created_at=T0)
    _mk_action(session, asset.id, 1, svc.TYPE_VOTE, T0 + timedelta(minutes=1), content="NEGATIVE")
    _mk_action(session, asset.id, 1, svc.TYPE_COMMENT, T0 + timedelta(minutes=2), content="c")
    q = _mk_action(session, asset.id, 1, svc.TYPE_QUESTION, T0 + timedelta(minutes=3), content="q?")
    _mk_action(session, asset.id, 1, svc.TYPE_ANSWER, T0 + timedelta(minutes=4), content="a")

    types = {e["type"] for e in svc.get_asset_history(session, asset.id)}
    assert {svc.TYPE_VOTE, svc.TYPE_COMMENT, svc.TYPE_QUESTION, svc.TYPE_ANSWER, "CREATED"} <= types


def test_history_vote_summary_and_content(session):
    asset = _mk_asset(session, created_at=T0)
    _mk_action(session, asset.id, 1, svc.TYPE_VOTE, T0 + timedelta(minutes=1), content="POSITIVE")
    _mk_action(session, asset.id, 1, svc.TYPE_COMMENT, T0 + timedelta(minutes=2), content="nice")

    by_type = {e["type"]: e for e in svc.get_asset_history(session, asset.id)}
    # Vote: derived summary, no content leaked.
    assert by_type[svc.TYPE_VOTE]["summary"] == "upvoted"
    assert by_type[svc.TYPE_VOTE]["content"] is None
    # Comment: content preserved.
    assert by_type[svc.TYPE_COMMENT]["content"] == "nice"


def test_history_resolves_actor_username(session):
    asset = _mk_asset(session, created_at=T0)
    _mk_user(session, 5, "alice")
    _mk_action(session, asset.id, 5, svc.TYPE_COMMENT, T0 + timedelta(minutes=1), content="hey")

    hist = svc.get_asset_history(session, asset.id)
    comment = next(e for e in hist if e["type"] == svc.TYPE_COMMENT)
    assert comment["actor"] == "alice"


def test_history_excludes_inactive_actions(session):
    asset = _mk_asset(session, created_at=T0)
    _mk_action(session, asset.id, 1, svc.TYPE_COMMENT, T0 + timedelta(minutes=1),
               content="gone", is_active=False)
    _mk_action(session, asset.id, 1, svc.TYPE_COMMENT, T0 + timedelta(minutes=2), content="kept")

    contents = [e["content"] for e in svc.get_asset_history(session, asset.id)]
    assert "kept" in contents and "gone" not in contents


def test_history_empty_asset_has_only_created_marker(session):
    asset = _mk_asset(session, created_at=T0)
    hist = svc.get_asset_history(session, asset.id)
    assert len(hist) == 1
    assert hist[0]["type"] == "CREATED" and hist[0]["id"] is None


def test_history_carries_workflow_status(session):
    asset = _mk_asset(session, created_at=T0)
    _mk_action(session, asset.id, 1, "REVIEW", T0 + timedelta(minutes=1),
               workflow_status="ASSIGNED")
    review = next(e for e in svc.get_asset_history(session, asset.id) if e["type"] == "REVIEW")
    assert review["workflow_status"] == "ASSIGNED"
    assert review["summary"] == "reviewed the asset"


# --- Route contract --------------------------------------------------------

def test_history_requires_auth(client):
    assert client.get("/api/actions/history/asset/1").status_code in (401, 403)


def test_history_route_in_openapi(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/actions/history/asset/{asset_id}" in paths


def test_history_route_returns_timeline(session, client):
    asset = _mk_asset(session, created_at=T0)
    _mk_action(session, asset.id, 1, svc.TYPE_COMMENT, T0 + timedelta(minutes=1), content="hi")
    app.dependency_overrides[current_active_user] = _superuser

    r = client.get(f"/api/actions/history/asset/{asset.id}")
    assert r.status_code == 200
    body = r.json()
    assert [e["type"] for e in body] == [svc.TYPE_COMMENT, "CREATED"]


def test_history_route_unknown_asset_returns_400(session, client):
    app.dependency_overrides[current_active_user] = _superuser
    r = client.get("/api/actions/history/asset/999999")
    assert r.status_code == 400
