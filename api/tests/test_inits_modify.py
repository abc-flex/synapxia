"""Modify Initiative (HU-IN16) — specs/005-explore-initiatives US7."""
from sqlmodel import select

from app.inits.internal import diagnosis_service, propose_service
from app.inits.internal.models import (
    Collaboration, Diagnostic, Initiative, InitiativeDiagnoseRequest,
    InitiativeProposeRequest,
)
from tests.inits_helpers import (
    COLLAB, data, mk_user_row, override, seed_core_lists, seed_criteria_with_scale,
    user,
)

PROPOSER = 10
REVIEWER = 20


def _in_feedback(session):
    seed_core_lists(session)
    seed_criteria_with_scale(session, codes=("C1", "C2"))
    mk_user_row(session, PROPOSER, "prop", profile=COLLAB)
    mk_user_row(session, REVIEWER, "rev", profile="REVIEWER")
    init = propose_service.propose_initiative(
        session, user(PROPOSER, profile=COLLAB),
        InitiativeProposeRequest(
            name="Loop", description="v1", expected_impact="OTHER", priority_level="LOW",
            reviewer_id=REVIEWER, answers={"C1": {"score": 1}, "C2": {"score": 2}},
        ))
    _changes(session, init.id)
    return init


def _changes(session, init_id, decision="changes"):
    diagnosis_service.diagnose_initiative(
        session, user(REVIEWER, profile="REVIEWER"), init_id,
        InitiativeDiagnoseRequest(decision=decision, feedback="more detail",
                                  answers={"C1": 2, "C2": 2}))


def _resubmit(client, init_id, body, uid=PROPOSER):
    override(user(uid, profile=COLLAB))
    return client.post(f"/api/initiatives/{init_id}/resubmit", json=body)


def test_resubmit_applies_fields_answers_and_rearms_reviewer(session, client):
    init = _in_feedback(session)
    resp = _resubmit(client, init.id, {
        "description": "v2",
        "answers": {"C1": {"score": 3, "rationale": "now clear"}, "C2": {"score": 2}},
    })
    assert resp.status_code == 200, resp.text
    body = data(resp)
    assert body["status"] == "ACTIVATED" and body["description"] == "v2"
    assert body["name"] == "Loop"  # unsent field untouched

    d1 = session.get(Diagnostic, (init.id, "C1"))
    assert (d1.creator_score, d1.rationale, d1.reviewer_score) == (3, "now clear", 2)

    mods = session.exec(select(Collaboration).where(Collaboration.type == "MODIFICATION")).all()
    assert [m.workflow_status for m in mods] == ["PENDING", "HANDLED"]
    diag = session.exec(select(Collaboration).where(Collaboration.type == "DIAGNOSIS")
                        .order_by(Collaboration.id.desc())).first()
    assert (diag.user_id, diag.workflow_status) == (REVIEWER, "PENDING")


def test_resubmit_without_answers_keeps_them(session, client):
    init = _in_feedback(session)
    assert _resubmit(client, init.id, {"name": "Loop v2"}).status_code == 200
    assert session.get(Diagnostic, (init.id, "C1")).creator_score == 1


def test_not_the_proposer_is_403(session, client):
    init = _in_feedback(session)
    mk_user_row(session, 30, "stranger", profile=COLLAB)
    assert _resubmit(client, init.id, {"name": "x"}, uid=30).status_code == 403


def test_not_in_feedback_is_409(session, client):
    init = _in_feedback(session)
    assert _resubmit(client, init.id, {"name": "x"}).status_code == 200
    assert _resubmit(client, init.id, {"name": "y"}).status_code == 409


def test_invalid_values_or_incomplete_answers_are_400(session, client):
    init = _in_feedback(session)
    assert _resubmit(client, init.id, {"priority_level": "NOPE"}).status_code == 400
    assert _resubmit(client, init.id, {"name": "  "}).status_code == 400
    assert _resubmit(client, init.id, {"answers": {"C1": {"score": 1}}}).status_code == 400
    assert session.get(Initiative, init.id).status == "FEEDBACK"


def test_reviewer_assets_and_status_in_body_are_ignored(session, client):
    init = _in_feedback(session)
    resp = _resubmit(client, init.id, {"status": "ACCEPTED", "reviewer_id": 99, "assets": []})
    assert resp.status_code == 200 and data(resp)["status"] == "ACTIVATED"


def test_two_round_loop_then_accept(session, client):
    init = _in_feedback(session)
    assert _resubmit(client, init.id, {"description": "v2"}).status_code == 200
    _changes(session, init.id)
    assert _resubmit(client, init.id, {"description": "v3"}).status_code == 200
    _changes(session, init.id, decision="accept")
    final = session.get(Initiative, init.id)
    assert (final.status, final.description, final.score) == ("ACCEPTED", "v3", 4)
