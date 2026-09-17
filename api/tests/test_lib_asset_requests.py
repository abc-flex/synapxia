"""Asset-requests page tests — Constitution Principle II/III.

`GET /api/actions/requests` backs the "My Asset Requests" page: everything the
caller has taken part in, whether they owe the next action or are waiting on
somebody else, split into in-motion and closed views.

The two invariants worth defending here are easy to break and expensive to get
wrong:

* **INV-1 / one row per asset.** Grouping is by ASSET, not by (asset, type). An
  asset a user proposed AND whose outcome they were later sent must appear once.
  Two rows would reintroduce, inside this very page, the duplicate-list problem
  the redesign exists to remove.
* **Derivation order.** "Does the caller owe something?" is evaluated BEFORE the
  asset's own status. Were it the other way round, a PUBLISHED asset whose
  notice the caller has not acknowledged would read as closed and the user would
  never learn the outcome.
"""

from datetime import datetime, timedelta
from types import SimpleNamespace

from app.main import app
from app.auth.routes import current_active_user
from app.lib.internal import actions_service as svc
from app.lib.internal.models import Asset, Action


T0 = datetime(2026, 1, 1, 12, 0, 0)
PENDING = svc.WORKFLOW_PENDING
HANDLED = svc.WORKFLOW_HANDLED
SELF = svc.AWAITED_SELF
OTHER = svc.AWAITED_OTHER


def _mk_asset(session, name="Asset", status="PROPOSED", category="PROMPTS"):
    asset = Asset(name=name, status=status, category=category)
    session.add(asset)
    session.commit()
    session.refresh(asset)
    return asset


def _mk_action(session, asset_id, user_id, type, status, created_at):
    a = Action(asset=asset_id, user_id=user_id, type=type,
               workflow_status=status, created_at=created_at)
    session.add(a)
    session.commit()
    session.refresh(a)
    return a


def _user(uid=1):
    return SimpleNamespace(id=uid, username="tester", profile="ADMINISTRATOR",
                           is_superuser=True, is_active=True)


def _only(session, uid=1, state=PENDING):
    rows = svc.list_participations(session, uid, state=state)
    assert len(rows) == 1, f"expected exactly one row, got {len(rows)}"
    return rows[0]


# --- The seven worked cases from data-model.md -----------------------------

def test_review_assigned_to_me_is_pending_on_self(session):
    asset = _mk_asset(session, status="PROPOSED")
    a = _mk_action(session, asset.id, 1, svc.TYPE_REVIEW, PENDING, T0)

    row = _only(session)
    assert row["state"] == PENDING and row["awaited_party"] == SELF
    assert row["pending_action_id"] == a.id
    assert row["pending_action_type"] == "REVIEW"
    assert row["roles"] == ["REVIEWER"]


def test_i_proposed_and_reviewer_has_not_decided_is_pending_on_other(session):
    asset = _mk_asset(session, status="PROPOSED")
    _mk_action(session, asset.id, 1, "PROPOSAL", HANDLED, T0)
    _mk_action(session, asset.id, 2, svc.TYPE_REVIEW, PENDING, T0)

    row = _only(session)
    assert row["state"] == PENDING and row["awaited_party"] == OTHER
    assert row["pending_action_id"] is None
    assert row["roles"] == ["PROPOSER"]


def test_changes_requested_and_not_resubmitted_is_pending_on_self(session):
    asset = _mk_asset(session, status="FEEDBACK")
    _mk_action(session, asset.id, 1, "PROPOSAL", HANDLED, T0)
    _mk_action(session, asset.id, 1, svc.TYPE_MODIFICATION, PENDING,
               T0 + timedelta(minutes=1))

    row = _only(session)
    assert row["state"] == PENDING and row["awaited_party"] == SELF
    assert row["pending_action_type"] == "MODIFICATION"


def test_published_but_unacknowledged_is_still_pending_on_self(session):
    """The derivation-order case. The asset is terminal, but the caller has not
    read the outcome, so it must NOT fall into the closed view."""
    asset = _mk_asset(session, status="PUBLISHED")
    _mk_action(session, asset.id, 1, "PROPOSAL", HANDLED, T0)
    _mk_action(session, asset.id, 1, svc.TYPE_PUBLICATION, PENDING,
               T0 + timedelta(minutes=1))

    row = _only(session)
    assert row["state"] == PENDING and row["awaited_party"] == SELF
    assert row["pending_action_type"] == "PUBLICATION"
    assert svc.list_participations(session, 1, state=HANDLED) == []


def test_published_and_acknowledged_is_handled(session):
    asset = _mk_asset(session, status="PUBLISHED")
    _mk_action(session, asset.id, 1, "PROPOSAL", HANDLED, T0)
    _mk_action(session, asset.id, 1, svc.TYPE_PUBLICATION, PENDING,
               T0 + timedelta(minutes=1))
    _mk_action(session, asset.id, 1, svc.TYPE_PUBLICATION, HANDLED,
               T0 + timedelta(minutes=2))

    assert svc.list_participations(session, 1, state=PENDING) == []
    row = _only(session, state=HANDLED)
    assert row["awaited_party"] is None
    assert row["asset_status"] == "PUBLISHED"


def test_published_where_i_was_the_reviewer_is_handled(session):
    """No outcome notice is raised for the reviewer, so nothing is owed."""
    asset = _mk_asset(session, status="PUBLISHED")
    _mk_action(session, asset.id, 1, svc.TYPE_REVIEW, HANDLED, T0)

    row = _only(session, state=HANDLED)
    assert row["awaited_party"] is None and row["roles"] == ["REVIEWER"]


def test_stalled_proposal_stays_visible_as_awaiting_other(session):
    """Proposed long ago, never reviewed — must not silently disappear."""
    asset = _mk_asset(session, status="PROPOSED")
    _mk_action(session, asset.id, 1, "PROPOSAL", HANDLED, T0)

    row = _only(session)
    assert row["state"] == PENDING and row["awaited_party"] == OTHER


# --- INV-1: one entry per asset --------------------------------------------

def test_proposal_plus_outcome_collapse_into_one_entry(session):
    asset = _mk_asset(session, status="PUBLISHED")
    _mk_action(session, asset.id, 1, "PROPOSAL", HANDLED, T0)
    _mk_action(session, asset.id, 1, svc.TYPE_PUBLICATION, HANDLED,
               T0 + timedelta(minutes=1))

    rows = svc.list_participations(session, 1, state=HANDLED)
    assert len(rows) == 1
    assert rows[0]["asset"] == asset.id


def test_dual_role_on_same_asset_yields_one_entry(session):
    """An administrative user may propose and review the same asset."""
    asset = _mk_asset(session, status="PUBLISHED")
    _mk_action(session, asset.id, 1, "PROPOSAL", HANDLED, T0)
    _mk_action(session, asset.id, 1, svc.TYPE_REVIEW, HANDLED,
               T0 + timedelta(minutes=1))

    row = _only(session, state=HANDLED)
    assert sorted(row["roles"]) == ["PROPOSER", "REVIEWER"]


def test_entries_are_scoped_to_the_caller(session):
    asset = _mk_asset(session, status="PROPOSED")
    _mk_action(session, asset.id, 2, svc.TYPE_REVIEW, PENDING, T0)

    assert svc.list_participations(session, 1, state=PENDING) == []
    assert len(svc.list_participations(session, 2, state=PENDING)) == 1


def test_votes_and_comments_do_not_create_entries(session):
    """The page covers proposing and reviewing, not every asset ever touched."""
    asset = _mk_asset(session, status="PUBLISHED")
    _mk_action(session, asset.id, 1, svc.TYPE_VOTE, None, T0)
    _mk_action(session, asset.id, 1, svc.TYPE_COMMENT, None, T0)

    assert svc.list_participations(session, 1, state=PENDING) == []
    assert svc.list_participations(session, 1, state=HANDLED) == []


# --- Ordering and pagination ------------------------------------------------

def test_newest_change_first(session):
    older = _mk_asset(session, "Older", status="PROPOSED")
    newer = _mk_asset(session, "Newer", status="PROPOSED")
    _mk_action(session, older.id, 1, svc.TYPE_REVIEW, PENDING, T0)
    _mk_action(session, newer.id, 1, svc.TYPE_REVIEW, PENDING,
               T0 + timedelta(hours=1))

    rows = svc.list_participations(session, 1, state=PENDING)
    assert [r["asset_name"] for r in rows] == ["Newer", "Older"]


def test_pagination_bounds_entries_not_rows(session):
    for n in range(5):
        a = _mk_asset(session, f"A{n}", status="PROPOSED")
        # Two rows per asset — pagination must count the ONE entry they collapse
        # into, not the underlying rows.
        _mk_action(session, a.id, 1, "PROPOSAL", HANDLED, T0 + timedelta(minutes=n))
        _mk_action(session, a.id, 1, svc.TYPE_MODIFICATION, PENDING,
                   T0 + timedelta(minutes=n))

    assert len(svc.list_participations(session, 1, state=PENDING, limit=2)) == 2
    assert len(svc.list_participations(session, 1, state=PENDING, skip=4, limit=10)) == 1


# --- Route contract ---------------------------------------------------------

def test_requests_route_returns_caller_entries(session, client):
    asset = _mk_asset(session, "Mine", status="PROPOSED")
    _mk_action(session, asset.id, 1, svc.TYPE_REVIEW, PENDING, T0)
    app.dependency_overrides[current_active_user] = lambda: _user(1)

    r = client.get("/api/actions/requests")
    assert r.status_code == 200
    body = r.json()["data"]
    assert len(body) == 1
    assert body[0]["asset_name"] == "Mine"
    assert body[0]["awaited_party"] == SELF
    assert body[0]["state"] == PENDING


def test_requests_route_state_filter(session, client):
    open_asset = _mk_asset(session, "Open", status="PROPOSED")
    done_asset = _mk_asset(session, "Done", status="PUBLISHED")
    _mk_action(session, open_asset.id, 1, svc.TYPE_REVIEW, PENDING, T0)
    _mk_action(session, done_asset.id, 1, svc.TYPE_REVIEW, HANDLED, T0)
    app.dependency_overrides[current_active_user] = lambda: _user(1)

    pending = client.get("/api/actions/requests?state=PENDING").json()["data"]
    handled = client.get("/api/actions/requests?state=HANDLED").json()["data"]
    assert [r["asset_name"] for r in pending] == ["Open"]
    assert [r["asset_name"] for r in handled] == ["Done"]


def test_requests_route_accepts_pagination_params(session, client):
    app.dependency_overrides[current_active_user] = lambda: _user(1)

    r = client.get("/api/actions/requests?skip=0&limit=10")
    assert r.status_code == 200
