"""Process Management — status lifecycle (specs/009-process-management, FR-008)."""
import pytest

from app.workflows.internal import status_service as ss
from tests.proc_helpers import BASE, data, mk_process, setup

ALLOWED = [("DRAFT", "REVIEW"), ("REVIEW", "PUBLISHED"), ("REVIEW", "DRAFT"),
           ("PUBLISHED", "DEPRECATED")]
REFUSED = [("DRAFT", "PUBLISHED"), ("DRAFT", "DEPRECATED"), ("REVIEW", "DEPRECATED"),
           ("PUBLISHED", "DRAFT"), ("PUBLISHED", "REVIEW"), ("DEPRECATED", "PUBLISHED"),
           ("DEPRECATED", "DRAFT"), ("DEPRECATED", "REVIEW")]


# ── Service ─────────────────────────────────────────────────────────────────

def test_create_status_is_always_draft():
    assert ss.validate_create_status(None) == "DRAFT"
    assert ss.validate_create_status("draft") == "DRAFT"
    with pytest.raises(ss.StatusTransitionForbidden):
        ss.validate_create_status("PUBLISHED")


@pytest.mark.parametrize("current,new", ALLOWED)
def test_allowed_moves(current, new):
    assert ss.validate_transition(current, new) is True


@pytest.mark.parametrize("current,new", REFUSED)
def test_refused_moves(current, new):
    with pytest.raises(ss.StatusTransitionForbidden):
        ss.validate_transition(current, new)


def test_unchanged_or_blank_is_not_a_move():
    assert ss.validate_transition("PUBLISHED", "PUBLISHED") is False
    assert ss.validate_transition("PUBLISHED", None) is False


def test_allowed_statuses_for():
    assert ss.allowed_statuses_for("DRAFT") == ["DRAFT", "REVIEW"]
    assert ss.allowed_statuses_for("REVIEW") == ["REVIEW", "PUBLISHED", "DRAFT"]
    assert ss.allowed_statuses_for("PUBLISHED") == ["PUBLISHED", "DEPRECATED"]
    assert ss.allowed_statuses_for("DEPRECATED") == ["DEPRECATED"]


# ── API ─────────────────────────────────────────────────────────────────────

def test_create_with_non_draft_status_refused(client, session):
    setup(session)
    body = {"code": "X1", "name": "X", "type": "PRIMARY"}
    assert client.post(f"{BASE}/", json={**body, "status": "PUBLISHED"}).status_code == 400
    assert client.post(f"{BASE}/", json={**body, "status": "DRAFT"}).status_code == 201


@pytest.mark.parametrize("current,new", ALLOWED)
def test_api_allowed_moves(client, session, current, new):
    setup(session)
    mk_process(session, "P", status=current)
    r = client.put(f"{BASE}/P", json={"status": new})
    assert r.status_code == 200, r.text
    assert data(r)["status"] == new


@pytest.mark.parametrize("current,new", REFUSED)
def test_api_refused_moves_leave_status(client, session, current, new):
    setup(session)
    mk_process(session, "P", status=current)
    assert client.put(f"{BASE}/P", json={"status": new}).status_code == 400
    assert data(client.get(f"{BASE}/P"))["status"] == current
