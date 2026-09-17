"""Notification feed tests — Constitution Principle II/III.

The feed is the caller's attention list: exactly the requests still awaiting
THEM. Workflow assignments are ``actions`` of type REVIEW/MODIFICATION/
PUBLICATION/REJECTION directed at a user, whose lifecycle is tracked by
INSERTING successive rows. There are two states — PENDING while the recipient
still owes an action, HANDLED once they do not.

There is deliberately no "seen/notified" state. Viewing an item is read state,
not work state; it now lives in the client and is never recorded here. The tests
below pin that down, because it is the invariant the whole redesign rests on.

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


def _mk_asset(session, name="Asset", status="PROPOSED"):
    asset = Asset(name=name, status=status)
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

def test_pending_thread_is_in_the_feed(session):
    asset = _mk_asset(session, "A")
    _mk_action(session, asset.id, 1, svc.TYPE_REVIEW, svc.WORKFLOW_PENDING, T0)

    feed = svc.list_notifications(session, 1)
    assert feed["total"] == 1
    assert feed["items"][0]["type"] == "REVIEW"
    assert feed["items"][0]["asset_name"] == "A"


def test_feed_has_no_unread_axis(session):
    """Every entry is pending on the caller, so a read/unread flag would be
    meaningless. Its absence is the contract, not an oversight."""
    asset = _mk_asset(session)
    _mk_action(session, asset.id, 1, svc.TYPE_REVIEW, svc.WORKFLOW_PENDING, T0)

    item = svc.list_notifications(session, 1)["items"][0]
    assert "unread" not in item
    assert "workflow_status" not in item


def test_handled_thread_is_excluded(session):
    asset = _mk_asset(session)
    _mk_action(session, asset.id, 1, svc.TYPE_REVIEW, svc.WORKFLOW_PENDING, T0)
    _mk_action(session, asset.id, 1, svc.TYPE_REVIEW, svc.WORKFLOW_HANDLED,
               T0 + timedelta(minutes=1))

    assert svc.list_notifications(session, 1)["total"] == 0


def test_latest_row_wins(session):
    """A thread's state is its newest row — transitions insert, never update."""
    asset = _mk_asset(session)
    first = _mk_action(session, asset.id, 1, svc.TYPE_REVIEW,
                       svc.WORKFLOW_HANDLED, T0)
    latest = _mk_action(session, asset.id, 1, svc.TYPE_REVIEW,
                        svc.WORKFLOW_PENDING, T0 + timedelta(minutes=1))

    item = svc.list_notifications(session, 1)["items"][0]
    assert item["id"] == latest.id != first.id


def test_type_filtering_excludes_non_workflow_actions(session):
    asset = _mk_asset(session)
    # A vote/comment carry no workflow status and must never reach the feed.
    _mk_action(session, asset.id, 1, svc.TYPE_VOTE, None, T0)
    _mk_action(session, asset.id, 1, svc.TYPE_COMMENT, None, T0 + timedelta(minutes=1))
    # A PROPOSAL is born HANDLED and is never owed by anyone.
    _mk_action(session, asset.id, 1, "PROPOSAL", svc.WORKFLOW_HANDLED,
               T0 + timedelta(minutes=2))

    assert svc.list_notifications(session, 1)["total"] == 0


def test_per_user_isolation(session):
    asset = _mk_asset(session)
    _mk_action(session, asset.id, 1, svc.TYPE_REVIEW, svc.WORKFLOW_PENDING, T0)
    _mk_action(session, asset.id, 2, svc.TYPE_PUBLICATION, svc.WORKFLOW_PENDING, T0)

    assert svc.list_notifications(session, 1)["total"] == 1
    assert svc.list_notifications(session, 2)["total"] == 1
    assert svc.list_notifications(session, 3)["total"] == 0


def test_waiting_on_someone_else_is_not_in_the_feed(session):
    """An asset the caller proposed is still moving, but nothing is being asked
    of them — it belongs on the requests page, never in the attention feed."""
    asset = _mk_asset(session, "Mine", status="PROPOSED")
    _mk_action(session, asset.id, 1, "PROPOSAL", svc.WORKFLOW_HANDLED, T0)
    # The review is assigned to somebody else.
    _mk_action(session, asset.id, 2, svc.TYPE_REVIEW, svc.WORKFLOW_PENDING, T0)

    assert svc.list_notifications(session, 1)["total"] == 0
    # ...but the proposer still sees it on the page, marked as awaiting another.
    page = svc.list_participations(session, 1, state=svc.WORKFLOW_PENDING)
    assert len(page) == 1 and page[0]["awaited_party"] == svc.AWAITED_OTHER


def test_feed_is_a_strict_subset_of_the_page(session):
    """INV-2: the indicator can never contain something the page does not."""
    asset_a = _mk_asset(session, "A", status="PROPOSED")
    asset_b = _mk_asset(session, "B", status="PUBLISHED")
    _mk_action(session, asset_a.id, 1, svc.TYPE_REVIEW, svc.WORKFLOW_PENDING, T0)
    _mk_action(session, asset_b.id, 1, svc.TYPE_PUBLICATION, svc.WORKFLOW_PENDING, T0)

    feed = svc.list_notifications(session, 1, limit=50)
    page = svc.list_participations(session, 1, state=svc.WORKFLOW_PENDING, limit=50)
    owed = {p["pending_action_id"] for p in page
            if p["awaited_party"] == svc.AWAITED_SELF}

    assert {i["id"] for i in feed["items"]} <= owed


def test_limit_caps_items_but_not_total(session):
    asset_ids = []
    for n in range(4):
        a = _mk_asset(session, f"A{n}")
        _mk_action(session, a.id, 1, svc.TYPE_REVIEW, svc.WORKFLOW_PENDING,
                   T0 + timedelta(minutes=n))
        asset_ids.append(a.id)

    feed = svc.list_notifications(session, 1, limit=2)
    assert len(feed["items"]) == 2
    assert feed["total"] == 4


# --- Acknowledgement -------------------------------------------------------

def test_acknowledge_inserts_handled_and_clears_the_feed(session):
    asset = _mk_asset(session, status="PUBLISHED")
    a = _mk_action(session, asset.id, 1, svc.TYPE_PUBLICATION,
                   svc.WORKFLOW_PENDING, T0)

    row = svc.acknowledge_notification(session, a)
    assert row.workflow_status == svc.WORKFLOW_HANDLED
    assert svc.list_notifications(session, 1)["total"] == 0


def test_acknowledge_rejects_review(session):
    """A review is resolved by deciding it. Acknowledging would write the same
    terminal row review_asset() uses for 'already decided', consuming the
    reviewer's turn without the work being done."""
    asset = _mk_asset(session)
    a = _mk_action(session, asset.id, 1, svc.TYPE_REVIEW, svc.WORKFLOW_PENDING, T0)

    try:
        svc.acknowledge_notification(session, a)
        raise AssertionError("expected NotificationNotAcknowledgeable")
    except svc.NotificationNotAcknowledgeable:
        pass
    # Still reachable, not silently closed.
    assert svc.list_notifications(session, 1)["total"] == 1


def test_acknowledge_rejects_modification(session):
    asset = _mk_asset(session)
    a = _mk_action(session, asset.id, 1, svc.TYPE_MODIFICATION,
                   svc.WORKFLOW_PENDING, T0)

    try:
        svc.acknowledge_notification(session, a)
        raise AssertionError("expected NotificationNotAcknowledgeable")
    except svc.NotificationNotAcknowledgeable:
        pass
    assert svc.list_notifications(session, 1)["total"] == 1


def test_acknowledge_is_idempotent(session):
    asset = _mk_asset(session, status="PUBLISHED")
    a = _mk_action(session, asset.id, 1, svc.TYPE_REJECTION,
                   svc.WORKFLOW_HANDLED, T0)

    assert svc.acknowledge_notification(session, a) is a


# --- Route contract --------------------------------------------------------

def test_notification_routes_in_openapi():
    paths = app.openapi()["paths"]
    assert "/api/actions/notifications" in paths
    assert "/api/actions/notifications/{id}/acknowledge" in paths
    assert "/api/actions/requests" in paths


def test_retired_routes_are_gone():
    """The endpoints this redesign removed must not linger: `notified` recorded
    read state (FR-002/FR-003), and reviews/modifications were partial
    duplicates of the unified requests page (FR-027)."""
    paths = app.openapi()["paths"]
    assert "/api/actions/notifications/{id}/notified" not in paths
    assert "/api/actions/reviews" not in paths
    assert "/api/actions/modifications" not in paths
    assert "/api/actions/notifications/{id}/dismiss" not in paths


def test_get_notifications_returns_current_user_only(session, client):
    asset = _mk_asset(session)
    _mk_action(session, asset.id, 1, svc.TYPE_REVIEW, svc.WORKFLOW_PENDING, T0)
    _mk_action(session, asset.id, 2, svc.TYPE_PUBLICATION, svc.WORKFLOW_PENDING, T0)
    app.dependency_overrides[current_active_user] = lambda: _user(1)

    r = client.get("/api/actions/notifications")
    assert r.status_code == 200
    body = r.json()["data"]
    assert body["total"] == 1
    assert len(body["items"]) == 1 and body["items"][0]["type"] == "REVIEW"


def test_acknowledge_route_removes_from_feed(session, client):
    asset = _mk_asset(session, status="PUBLISHED")
    a = _mk_action(session, asset.id, 1, svc.TYPE_PUBLICATION,
                   svc.WORKFLOW_PENDING, T0)
    app.dependency_overrides[current_active_user] = lambda: _user(1)

    r = client.post(f"/api/actions/notifications/{a.id}/acknowledge")
    assert r.status_code == 200
    assert r.json()["data"]["workflow_status"] == svc.WORKFLOW_HANDLED
    assert client.get("/api/actions/notifications").json()["data"]["total"] == 0


def test_acknowledge_route_rejects_review_with_400(session, client):
    asset = _mk_asset(session)
    a = _mk_action(session, asset.id, 1, svc.TYPE_REVIEW, svc.WORKFLOW_PENDING, T0)
    app.dependency_overrides[current_active_user] = lambda: _user(1)

    r = client.post(f"/api/actions/notifications/{a.id}/acknowledge")
    assert r.status_code == 400
    # The assignment must still be reachable, not silently closed.
    body = client.get("/api/actions/notifications").json()["data"]
    assert body["total"] == 1 and body["items"][0]["type"] == "REVIEW"


def test_acknowledge_route_rejects_modification_with_400(session, client):
    asset = _mk_asset(session)
    a = _mk_action(session, asset.id, 1, svc.TYPE_MODIFICATION,
                   svc.WORKFLOW_PENDING, T0)
    app.dependency_overrides[current_active_user] = lambda: _user(1)

    r = client.post(f"/api/actions/notifications/{a.id}/acknowledge")
    assert r.status_code == 400
    assert client.get("/api/actions/notifications").json()["data"]["total"] == 1


def test_acknowledge_route_404_for_unknown_id(session, client):
    app.dependency_overrides[current_active_user] = lambda: _user(1)

    r = client.post("/api/actions/notifications/999999/acknowledge")
    assert r.status_code == 404
