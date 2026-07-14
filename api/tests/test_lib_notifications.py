"""Notification tests (HU-LI11) — Constitution Principle II/III.

Workflow notifications are ``actions`` of type REVIEW/MODIFICATION/PUBLICATION/
REJECTION directed at a user, whose lifecycle is tracked by INSERTING successive
rows with workflow_status ASSIGNED → NOTIFIED → FINISHED (matching the seed). A
notification is the latest row of a (asset, type) thread whose status is still
ASSIGNED or NOTIFIED. This is the read + transition side only (the generating
review workflow is out of scope).

Two layers, like the history/foro suites:
1. Service logic against the in-memory SQLite ``session`` fixture (explicit
   ``created_at`` makes "latest row" deterministic).
2. Route contract: auth-gated, in OpenAPI, per-user isolation enforced.
"""

from datetime import datetime, timedelta
from types import SimpleNamespace

from app.main import app
from app.auth.routes import current_active_user
from app.lib.internal import actions_service as svc
from app.lib.internal.models import Asset, Action
from app.admin.internal.models import User


T0 = datetime(2026, 1, 1, 12, 0, 0)


def _mk_asset(session, name="Asset"):
    asset = Asset(name=name, status="PROPOSED")
    session.add(asset)
    session.commit()
    session.refresh(asset)
    return asset


def _mk_action(session, asset_id, user_id, type, status, created_at, is_active=True):
    a = Action(
        asset=asset_id, user_id=user_id, type=type,
        workflow_status=status, is_active=is_active, created_at=created_at,
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


def _user(uid=1):
    return SimpleNamespace(
        id=uid, username="tester", profile="ADMINISTRATOR",
        is_superuser=True, is_active=True,
    )


# --- Service logic ---------------------------------------------------------

def test_assigned_thread_is_unread_notification(session):
    asset = _mk_asset(session, "A")
    _mk_action(session, asset.id, 1, svc.TYPE_REVIEW, "ASSIGNED", T0)

    items = svc.list_notifications(session, 1)
    assert len(items) == 1
    assert items[0]["type"] == "REVIEW"
    assert items[0]["workflow_status"] == "ASSIGNED"
    assert items[0]["unread"] is True
    assert items[0]["asset_name"] == "A"


def test_latest_status_wins_notified_not_unread(session):
    asset = _mk_asset(session)
    a = _mk_action(session, asset.id, 1, svc.TYPE_REVIEW, "ASSIGNED", T0)
    _mk_action(session, asset.id, 1, svc.TYPE_REVIEW, "NOTIFIED", T0 + timedelta(minutes=1))

    items = svc.list_notifications(session, 1)
    assert len(items) == 1
    assert items[0]["workflow_status"] == "NOTIFIED"
    assert items[0]["unread"] is False
    # The latest row's id is surfaced (not the original ASSIGNED row).
    assert items[0]["id"] != a.id


def test_finished_thread_is_excluded(session):
    asset = _mk_asset(session)
    _mk_action(session, asset.id, 1, svc.TYPE_REVIEW, "ASSIGNED", T0)
    _mk_action(session, asset.id, 1, svc.TYPE_REVIEW, "NOTIFIED", T0 + timedelta(minutes=1))
    _mk_action(session, asset.id, 1, svc.TYPE_REVIEW, "FINISHED", T0 + timedelta(minutes=2))

    assert svc.list_notifications(session, 1) == []


def test_type_filtering_excludes_non_workflow_actions(session):
    asset = _mk_asset(session)
    # A vote/comment carry no workflow status and must never be a notification.
    _mk_action(session, asset.id, 1, svc.TYPE_VOTE, None, T0)
    _mk_action(session, asset.id, 1, svc.TYPE_COMMENT, None, T0 + timedelta(minutes=1))
    # A PROPOSAL is FINISHED and not a notification type.
    _mk_action(session, asset.id, 1, "PROPOSAL", "FINISHED", T0 + timedelta(minutes=2))

    assert svc.list_notifications(session, 1) == []


def test_per_user_isolation(session):
    asset = _mk_asset(session)
    _mk_action(session, asset.id, 1, svc.TYPE_REVIEW, "ASSIGNED", T0)
    _mk_action(session, asset.id, 2, svc.TYPE_PUBLICATION, "ASSIGNED", T0 + timedelta(minutes=1))

    u1 = svc.list_notifications(session, 1)
    u2 = svc.list_notifications(session, 2)
    assert [i["type"] for i in u1] == ["REVIEW"]
    assert [i["type"] for i in u2] == ["PUBLICATION"]


def test_distinct_types_on_same_asset_are_separate_threads(session):
    asset = _mk_asset(session)
    _mk_action(session, asset.id, 1, svc.TYPE_REVIEW, "ASSIGNED", T0)
    _mk_action(session, asset.id, 1, svc.TYPE_MODIFICATION, "ASSIGNED", T0 + timedelta(minutes=1))

    types = {i["type"] for i in svc.list_notifications(session, 1)}
    assert types == {"REVIEW", "MODIFICATION"}


def test_mark_notified_inserts_notified_and_unbolds(session):
    asset = _mk_asset(session)
    a = _mk_action(session, asset.id, 1, svc.TYPE_REVIEW, "ASSIGNED", T0)

    svc.mark_notified(session, a)
    items = svc.list_notifications(session, 1)
    assert len(items) == 1  # still one thread, now NOTIFIED
    assert items[0]["workflow_status"] == "NOTIFIED"
    assert items[0]["unread"] is False


def test_mark_notified_is_noop_when_not_assigned(session):
    asset = _mk_asset(session)
    a = _mk_action(session, asset.id, 1, svc.TYPE_REVIEW, "NOTIFIED", T0)
    result = svc.mark_notified(session, a)
    assert result is a  # unchanged
    # Only the original row exists — no extra NOTIFIED inserted.
    assert len(svc.list_notifications(session, 1)) == 1


def test_dismiss_inserts_finished_and_removes(session):
    # PUBLICATION/REJECTION are informational — no further action is expected,
    # so they remain dismissible.
    asset = _mk_asset(session)
    a = _mk_action(session, asset.id, 1, svc.TYPE_PUBLICATION, "NOTIFIED", T0)

    svc.dismiss_notification(session, a)
    assert svc.list_notifications(session, 1) == []


def test_dismiss_review_is_rejected(session):
    # REVIEW must be resolved via review_asset(), not dismissed — dismissing it
    # would insert the same FINISHED row review_asset() uses to mean "already
    # decided", permanently blocking the reviewer from acting on it.
    asset = _mk_asset(session)
    a = _mk_action(session, asset.id, 1, svc.TYPE_REVIEW, "NOTIFIED", T0)

    try:
        svc.dismiss_notification(session, a)
        assert False, "expected NotificationNotDismissible"
    except svc.NotificationNotDismissible:
        pass
    # The assignment must still be open (ASSIGNED/NOTIFIED), not FINISHED.
    items = svc.list_notifications(session, 1)
    assert len(items) == 1
    assert items[0]["workflow_status"] == "NOTIFIED"


def test_dismiss_modification_is_rejected(session):
    asset = _mk_asset(session)
    a = _mk_action(session, asset.id, 1, svc.TYPE_MODIFICATION, "NOTIFIED", T0)

    try:
        svc.dismiss_notification(session, a)
        assert False, "expected NotificationNotDismissible"
    except svc.NotificationNotDismissible:
        pass
    assert len(svc.list_notifications(session, 1)) == 1


def test_list_review_requests_scoped_to_review_type(session):
    asset = _mk_asset(session)
    _mk_action(session, asset.id, 1, svc.TYPE_REVIEW, "ASSIGNED", T0)
    _mk_action(session, asset.id, 1, svc.TYPE_MODIFICATION, "ASSIGNED", T0 + timedelta(minutes=1))

    items = svc.list_review_requests(session, 1)
    assert [i["type"] for i in items] == ["REVIEW"]


def test_list_pending_modifications_scoped_to_modification_type(session):
    asset = _mk_asset(session)
    _mk_action(session, asset.id, 1, svc.TYPE_REVIEW, "ASSIGNED", T0)
    _mk_action(session, asset.id, 1, svc.TYPE_MODIFICATION, "ASSIGNED", T0 + timedelta(minutes=1))

    items = svc.list_pending_modifications(session, 1)
    assert [i["type"] for i in items] == ["MODIFICATION"]


# --- Route contract --------------------------------------------------------

def test_notifications_require_auth(client):
    assert client.get("/api/actions/notifications").status_code in (401, 403)


def test_notification_routes_in_openapi(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/actions/notifications" in paths
    assert "/api/actions/notifications/{id}/notified" in paths
    assert "/api/actions/notifications/{id}/dismiss" in paths
    assert "/api/actions/reviews" in paths
    assert "/api/actions/modifications" in paths


def test_get_notifications_returns_current_user_only(session, client):
    asset = _mk_asset(session)
    _mk_action(session, asset.id, 1, svc.TYPE_REVIEW, "ASSIGNED", T0)
    _mk_action(session, asset.id, 2, svc.TYPE_PUBLICATION, "ASSIGNED", T0)
    app.dependency_overrides[current_active_user] = lambda: _user(1)

    r = client.get("/api/actions/notifications")
    assert r.status_code == 200
    body = r.json()["data"]
    assert len(body) == 1 and body[0]["type"] == "REVIEW"


def test_notified_route_transitions(session, client):
    asset = _mk_asset(session)
    a = _mk_action(session, asset.id, 1, svc.TYPE_REVIEW, "ASSIGNED", T0)
    app.dependency_overrides[current_active_user] = lambda: _user(1)

    r = client.post(f"/api/actions/notifications/{a.id}/notified")
    assert r.status_code == 200
    assert r.json()["data"]["workflow_status"] == "NOTIFIED"
    # The thread is now seen (not unread).
    items = client.get("/api/actions/notifications").json()["data"]
    assert items[0]["unread"] is False


def test_dismiss_route_removes_from_list(session, client):
    asset = _mk_asset(session)
    a = _mk_action(session, asset.id, 1, svc.TYPE_PUBLICATION, "NOTIFIED", T0)
    app.dependency_overrides[current_active_user] = lambda: _user(1)

    r = client.post(f"/api/actions/notifications/{a.id}/dismiss")
    assert r.status_code == 200
    assert r.json()["data"]["workflow_status"] == "FINISHED"
    assert client.get("/api/actions/notifications").json()["data"] == []


def test_dismiss_route_rejects_review_with_400(session, client):
    asset = _mk_asset(session)
    a = _mk_action(session, asset.id, 1, svc.TYPE_REVIEW, "NOTIFIED", T0)
    app.dependency_overrides[current_active_user] = lambda: _user(1)

    r = client.post(f"/api/actions/notifications/{a.id}/dismiss")
    assert r.status_code == 400
    # The assignment must still be reachable, not silently closed.
    items = client.get("/api/actions/notifications").json()["data"]
    assert len(items) == 1 and items[0]["type"] == "REVIEW"


def test_dismiss_route_rejects_modification_with_400(session, client):
    asset = _mk_asset(session)
    a = _mk_action(session, asset.id, 1, svc.TYPE_MODIFICATION, "NOTIFIED", T0)
    app.dependency_overrides[current_active_user] = lambda: _user(1)

    r = client.post(f"/api/actions/notifications/{a.id}/dismiss")
    assert r.status_code == 400


def test_cannot_transition_another_users_notification(session, client):
    asset = _mk_asset(session)
    other = _mk_action(session, asset.id, 2, svc.TYPE_REVIEW, "ASSIGNED", T0)
    app.dependency_overrides[current_active_user] = lambda: _user(1)

    assert client.post(f"/api/actions/notifications/{other.id}/notified").status_code == 404
    assert client.post(f"/api/actions/notifications/{other.id}/dismiss").status_code == 404


def test_reviews_route_returns_only_review_type(session, client):
    asset = _mk_asset(session)
    _mk_action(session, asset.id, 1, svc.TYPE_REVIEW, "ASSIGNED", T0)
    _mk_action(session, asset.id, 1, svc.TYPE_MODIFICATION, "ASSIGNED", T0 + timedelta(minutes=1))
    app.dependency_overrides[current_active_user] = lambda: _user(1)

    r = client.get("/api/actions/reviews")
    assert r.status_code == 200
    body = r.json()["data"]
    assert len(body) == 1 and body[0]["type"] == "REVIEW"


def test_modifications_route_returns_only_modification_type(session, client):
    asset = _mk_asset(session)
    _mk_action(session, asset.id, 1, svc.TYPE_REVIEW, "ASSIGNED", T0)
    _mk_action(session, asset.id, 1, svc.TYPE_MODIFICATION, "ASSIGNED", T0 + timedelta(minutes=1))
    app.dependency_overrides[current_active_user] = lambda: _user(1)

    r = client.get("/api/actions/modifications")
    assert r.status_code == 200
    body = r.json()["data"]
    assert len(body) == 1 and body[0]["type"] == "MODIFICATION"


def test_reviews_and_modifications_require_auth(client):
    assert client.get("/api/actions/reviews").status_code in (401, 403)
    assert client.get("/api/actions/modifications").status_code in (401, 403)
