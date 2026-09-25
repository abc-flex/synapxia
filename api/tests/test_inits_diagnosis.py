"""Diagnosis of the Initiative (HU-IN15) — specs/005-explore-initiatives US6."""
import pytest
from sqlmodel import select

from app.inits.internal import propose_service
from app.inits.internal.models import (
    Collaboration, Diagnostic, Initiative, InitiativeProposeRequest,
)
from tests.inits_helpers import (
    COLLAB, data, mk_user_row, override, seed_core_lists, seed_criteria_with_scale,
    user,
)

PROPOSER = 10
REVIEWER = 20


def _proposed(session):
    seed_core_lists(session)
    seed_criteria_with_scale(session, codes=("C1", "C2"))
    mk_user_row(session, PROPOSER, "prop", profile=COLLAB)
    mk_user_row(session, REVIEWER, "rev", profile="REVIEWER")
    init = propose_service.propose_initiative(
        session, user(PROPOSER, profile=COLLAB),
        InitiativeProposeRequest(
            name="Loop", expected_impact="OTHER", priority_level="LOW",
            reviewer_id=REVIEWER,
            answers={"C1": {"score": 1, "rationale": "why"}, "C2": {"score": 2}},
        ))
    return init


def _diagnose(client, init_id, decision, answers=None, feedback="fix it", uid=REVIEWER,
              profile="REVIEWER"):
    override(user(uid, profile=profile))
    return client.post(f"/api/initiatives/{init_id}/diagnose", json={
        "decision": decision, "feedback": feedback,
        "answers": answers if answers is not None else {"C1": 3, "C2": 2},
    })


def _rows(session, type_):
    return session.exec(select(Collaboration).where(Collaboration.type == type_)
                        .order_by(Collaboration.id)).all()


@pytest.mark.parametrize("decision,status,notice", [
    ("accept", "ACCEPTED", "ACCEPTANCE"),
    ("reject", "REJECTED", "REJECTION"),
    ("changes", "FEEDBACK", "MODIFICATION"),
])
def test_decision_writes_the_whole_transition(session, client, decision, status, notice):
    init = _proposed(session)
    resp = _diagnose(client, init.id, decision)
    assert resp.status_code == 200, resp.text
    body = data(resp)
    assert body["status"] == status and body["score"] == 5  # 3 + 2

    diags = {d.criteria: d for d in session.exec(select(Diagnostic)).all()}
    assert (diags["C1"].creator_score, diags["C1"].reviewer_score) == (1, 3)
    assert diags["C1"].rationale == "why"  # proposer's rationale untouched

    assert [r.workflow_status for r in _rows(session, "DIAGNOSIS")] == ["PENDING", "HANDLED"]
    sent = _rows(session, notice)[-1]
    assert (sent.user_id, sent.workflow_status, sent.content) == (PROPOSER, "PENDING", "fix it")


def test_accept_feedback_is_optional(session, client):
    init = _proposed(session)
    assert _diagnose(client, init.id, "accept", feedback=None).status_code == 200


@pytest.mark.parametrize("decision", ["reject", "changes"])
def test_feedback_required_for_reject_and_changes(session, client, decision):
    init = _proposed(session)
    assert _diagnose(client, init.id, decision, feedback="  ").status_code == 400
    assert session.get(Initiative, init.id).status == "ACTIVATED"


def test_unknown_decision_is_400(session, client):
    init = _proposed(session)
    assert _diagnose(client, init.id, "maybe").status_code == 400


def test_missing_initiative_is_400(session, client):
    _proposed(session)
    assert _diagnose(client, 9999, "accept").status_code == 400


def test_ineligible_caller_is_403(session, client):
    init = _proposed(session)
    assert _diagnose(client, init.id, "accept", uid=PROPOSER, profile=COLLAB).status_code == 403


def test_unassigned_reviewer_is_403(session, client):
    init = _proposed(session)
    mk_user_row(session, 30, "other_rev", profile="REVIEWER")
    assert _diagnose(client, init.id, "accept", uid=30).status_code == 403


def test_double_decision_is_409(session, client):
    init = _proposed(session)
    assert _diagnose(client, init.id, "accept").status_code == 200
    assert _diagnose(client, init.id, "reject").status_code == 409


@pytest.mark.parametrize("answers", [{"C1": 3}, {"C1": 3, "C2": 7}, {"C1": 3, "C2": 1, "X": 1}])
def test_incomplete_or_invalid_answers_are_400(session, client, answers):
    init = _proposed(session)
    assert _diagnose(client, init.id, "accept", answers=answers).status_code == 400


def test_failures_write_nothing(session, client):
    init = _proposed(session)
    before = len(session.exec(select(Collaboration)).all())
    _diagnose(client, init.id, "changes", feedback="")
    _diagnose(client, init.id, "accept", answers={"C1": 9, "C2": 1})
    assert len(session.exec(select(Collaboration)).all()) == before
    assert all(d.reviewer_score is None for d in session.exec(select(Diagnostic)).all())
