"""Usage tracking (HU-LI07) — Constitution III.

Copying a copyable characteristic records an ``actions`` row of type USAGE.
Three properties matter and are asserted here:

  * every copy is its own event (no per-user dedup) — the count answers
    "how many times has this asset been used?", not "how many people used it";
  * USAGE rows never reach the asset history timeline (they would bury the
    asset's real lifecycle under high-frequency, low-signal noise);
  * the actor is always the authenticated caller — the body carries no user id,
    so usage cannot be attributed to somebody else.
"""

from types import SimpleNamespace

from sqlmodel import select

from app.main import app
from app.auth.routes import current_active_user
from app.lib.internal import actions_service as svc
from app.lib.internal.models import Action, Asset


def _superuser(uid=1, username="root"):
    return SimpleNamespace(id=uid, username=username, profile="ADMINISTRATOR",
                           unit="HQ", is_superuser=True, is_active=True)


def _override(user=None):
    app.dependency_overrides[current_active_user] = lambda: user or _superuser()


def _mk_asset(session, name="A", status="PUBLISHED"):
    a = Asset(name=name, status=status)
    session.add(a)
    session.commit()
    session.refresh(a)
    return a


def _usage_rows(session, asset_id):
    return session.exec(
        select(Action)
        .where(Action.asset == asset_id, Action.type == "USAGE")
        .order_by(Action.id)
    ).all()


# --- Service -----------------------------------------------------------------

def test_record_usage_writes_a_usage_action(session):
    asset = _mk_asset(session)
    action = svc.record_usage(session, user_id=7, asset_id=asset.id,
                              feature="PROMPT_TEMPLATE")
    assert action.type == "USAGE"
    assert action.user_id == 7
    assert action.content == "PROMPT_TEMPLATE"


def test_feature_is_normalized_and_optional(session):
    asset = _mk_asset(session)
    assert svc.record_usage(
        session, 1, asset.id, feature="  prompt_template ").content == "PROMPT_TEMPLATE"
    # A usage trigger that isn't feature-scoped records a bare event.
    assert svc.record_usage(session, 1, asset.id, feature=None).content is None
    assert svc.record_usage(session, 1, asset.id, feature="   ").content is None


def test_workflow_status_stays_null(session):
    """USAGE is an interaction, not a workflow step.

    ``_latest_threads`` (My Asset Requests / the bell) filters on a non-NULL
    ``workflow_status``; a HANDLED usage row would leak telemetry into a
    surface that is supposed to list work.
    """
    asset = _mk_asset(session)
    assert svc.record_usage(session, 1, asset.id).workflow_status is None


def test_every_copy_is_its_own_event(session):
    asset = _mk_asset(session)
    for _ in range(3):
        svc.record_usage(session, 1, asset.id, "TOOLS")  # same user, same feature
    assert svc.count_usage(session, asset.id) == 3


def test_count_is_scoped_to_the_asset(session):
    a, b = _mk_asset(session, "A"), _mk_asset(session, "B")
    svc.record_usage(session, 1, a.id)
    svc.record_usage(session, 1, a.id)
    svc.record_usage(session, 1, b.id)
    assert svc.count_usage(session, a.id) == 2
    assert svc.count_usage(session, b.id) == 1


def test_count_ignores_logically_deleted_rows(session):
    asset = _mk_asset(session)
    keep = svc.record_usage(session, 1, asset.id)
    drop = svc.record_usage(session, 1, asset.id)
    drop.is_active = False
    session.add(drop)
    session.commit()
    assert svc.count_usage(session, asset.id) == 1
    assert keep.is_active is True


def test_count_is_zero_for_an_unused_asset(session):
    assert svc.count_usage(session, _mk_asset(session).id) == 0


# --- History exclusion -------------------------------------------------------

def test_usage_never_appears_in_the_history_timeline(session):
    asset = _mk_asset(session)
    svc.record_usage(session, 1, asset.id, "TOOLS")
    svc.add_comment(session, 1, asset.id, "a comment")

    types = {e["type"] for e in svc.get_asset_history(session, asset.id)}
    assert "USAGE" not in types
    assert {"COMMENT", "CREATED"} <= types


def test_history_of_a_heavily_used_asset_is_not_drowned(session):
    asset = _mk_asset(session)
    for _ in range(50):
        svc.record_usage(session, 1, asset.id)
    entries = svc.get_asset_history(session, asset.id)
    # Only the synthetic CREATED marker survives.
    assert [e["type"] for e in entries] == ["CREATED"]


def test_usage_is_the_only_excluded_type(session):
    assert svc.HISTORY_EXCLUDED_TYPES == (svc.TYPE_USAGE,)


# --- Routes ------------------------------------------------------------------

def test_post_usage_records_and_returns_the_new_count(session, client):
    _override()
    asset = _mk_asset(session)

    r = client.post("/api/actions/usage",
                    json={"asset": asset.id, "feature": "SERVER_CONFIG"})
    assert r.status_code == 201
    assert r.json()["data"] == {"asset": asset.id, "count": 1}

    r = client.post("/api/actions/usage", json={"asset": asset.id})
    assert r.json()["data"]["count"] == 2


def test_usage_is_attributed_to_the_caller_not_the_body(session, client):
    """The body has no user_id field, so a forged one is simply ignored."""
    _override(_superuser(uid=42, username="consumer"))
    asset = _mk_asset(session)

    r = client.post("/api/actions/usage",
                    json={"asset": asset.id, "user_id": 999})
    assert r.status_code == 201
    assert [row.user_id for row in _usage_rows(session, asset.id)] == [42]


def test_post_usage_on_a_missing_asset_is_400(session, client):
    _override()
    r = client.post("/api/actions/usage", json={"asset": 99999})
    assert r.status_code == 400


def test_get_usage_tally(session, client):
    _override()
    asset = _mk_asset(session)
    svc.record_usage(session, 1, asset.id)
    svc.record_usage(session, 1, asset.id)

    r = client.get(f"/api/actions/usage/asset/{asset.id}")
    assert r.status_code == 200
    assert r.json()["data"] == {"asset": asset.id, "count": 2}


def test_get_usage_tally_of_an_unused_asset_is_zero(session, client):
    _override()
    asset = _mk_asset(session)
    r = client.get(f"/api/actions/usage/asset/{asset.id}")
    assert r.json()["data"]["count"] == 0


def test_get_usage_tally_on_a_missing_asset_is_400(session, client):
    _override()
    assert client.get("/api/actions/usage/asset/99999").status_code == 400


def test_usage_route_is_not_parsed_as_an_action_id(session, client):
    """`/usage` must be registered before the composite `/{id}` getter."""
    _override()
    asset = _mk_asset(session)
    r = client.get(f"/api/actions/usage/asset/{asset.id}")
    assert r.status_code == 200  # not a 422 from int(id) parsing


def test_history_endpoint_hides_usage(session, client):
    _override()
    asset = _mk_asset(session)
    client.post("/api/actions/usage", json={"asset": asset.id})

    r = client.get(f"/api/actions/history/asset/{asset.id}")
    assert r.status_code == 200
    assert all(e["type"] != "USAGE" for e in r.json()["data"])
