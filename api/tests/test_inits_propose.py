"""Propose Initiative (HU-IN05) — specs/005-explore-initiatives US1/US2.

One all-or-nothing transaction: initiative (ACTIVATED) + proposer answers +
asset links + ACTIVATION/HANDLED + DIAGNOSIS/PENDING + MANAGE grants. Every
validation failure is a 400 that writes nothing.
"""
from sqlmodel import select

from app.inits.internal.models import (
    Collaboration, Diagnostic, InitPermission, Initiative,
)
from app.lib.internal.models import AssetInit
from tests.inits_helpers import (
    COLLAB, data, mk_asset, mk_asset_perm, mk_user_row, override, seed_core_lists,
    seed_criteria_with_scale, seed_privileges, superuser, user,
)

PROPOSER = 10
REVIEWER = 20


def _world(session, proposer_profile=COLLAB):
    seed_core_lists(session)
    seed_criteria_with_scale(session, codes=("C1", "C2"))
    mk_user_row(session, PROPOSER, "prop", profile=proposer_profile)
    mk_user_row(session, REVIEWER, "rev", profile="REVIEWER")
    seed_privileges(session, profile=proposer_profile, options=("EXPLORE",), can_edit=True)
    return user(PROPOSER, profile=proposer_profile)


def _body(**kw):
    body = {
        "name": "Clause Extractor",
        "description": "Extract clauses",
        "type": "PROTOTYPING",
        "expected_impact": "OTHER",
        "priority_level": "HIGH",
        "tags": ["legal"],
        "reviewer_id": REVIEWER,
        "answers": {"C1": {"score": 2, "rationale": "clear enough"}, "C2": {"score": 3}},
        "assets": [],
    }
    body.update(kw)
    return body


def _counts(session):
    return tuple(len(session.exec(select(m)).all())
                 for m in (Initiative, Diagnostic, Collaboration, InitPermission, AssetInit))


# ── Happy path ──────────────────────────────────────────────────────────────

def test_propose_writes_the_whole_workflow(session, client):
    proposer = _world(session)
    mk_asset(session, 5, "Prompt")
    mk_asset_perm(session, 5, target_code=str(PROPOSER))
    override(proposer)

    resp = client.post("/api/initiatives/propose", json=_body(
        assets=[{"asset": 5, "type": "USED_BY", "rationale": " reuse "}]))
    assert resp.status_code == 201, resp.text
    init = data(resp)
    assert init["status"] == "ACTIVATED" and init["score"] is None

    diags = {d.criteria: d for d in session.exec(select(Diagnostic)).all()}
    assert diags["C1"].creator_score == 2 and diags["C1"].rationale == "clear enough"
    assert diags["C2"].creator_score == 3 and diags["C2"].reviewer_score is None

    collabs = {(c.type, c.workflow_status, c.user_id) for c in session.exec(select(Collaboration)).all()}
    assert collabs == {("ACTIVATION", "HANDLED", PROPOSER), ("DIAGNOSIS", "PENDING", REVIEWER)}

    grants = {(g.target_type, g.target_code, g.access_level) for g in session.exec(select(InitPermission)).all()}
    assert grants == {("USER", str(PROPOSER), "MANAGE"), ("USER", str(REVIEWER), "MANAGE")}

    link = session.exec(select(AssetInit)).one()
    assert (link.asset, link.type, link.rationale) == (5, "USED_BY", "reuse")


def test_admin_self_review_yields_one_grant(session, client):
    _world(session, proposer_profile="ADMINISTRATIVE")
    override(user(PROPOSER, profile="ADMINISTRATIVE"))
    resp = client.post("/api/initiatives/propose", json=_body(reviewer_id=PROPOSER))
    assert resp.status_code == 201, resp.text
    assert len(session.exec(select(InitPermission)).all()) == 1


def test_actor_comes_from_session_not_body(session, client):
    proposer = _world(session)
    override(proposer)
    resp = client.post("/api/initiatives/propose", json={**_body(), "user_id": 999})
    assert resp.status_code == 201
    activation = session.exec(select(Collaboration).where(Collaboration.type == "ACTIVATION")).one()
    assert activation.user_id == PROPOSER


# ── Validation: 400 and nothing written ─────────────────────────────────────

def _assert_refused(session, client, proposer, body):
    before = _counts(session)
    override(proposer)
    resp = client.post("/api/initiatives/propose", json=body)
    assert resp.status_code == 400, resp.text
    assert _counts(session) == before


def test_blank_name_refused(session, client):
    _assert_refused(session, client, _world(session), _body(name="   "))


def test_invalid_list_values_refused(session, client):
    proposer = _world(session)
    _assert_refused(session, client, proposer, _body(expected_impact="NOPE"))
    _assert_refused(session, client, proposer, _body(priority_level=""))
    _assert_refused(session, client, proposer, _body(type="NOPE"))


def test_incomplete_or_invalid_answers_refused(session, client):
    proposer = _world(session)
    _assert_refused(session, client, proposer, _body(answers={"C1": {"score": 2}}))
    _assert_refused(session, client, proposer, _body(
        answers={"C1": {"score": 2}, "C2": {"score": 9}}))
    _assert_refused(session, client, proposer, _body(
        answers={"C1": {"score": 2}, "C2": {"score": 1}, "X": {"score": 1}}))


def test_invisible_inactive_or_duplicate_assets_refused(session, client):
    proposer = _world(session)
    mk_asset(session, 5, "Visible")
    mk_asset_perm(session, 5, target_code=str(PROPOSER))
    mk_asset(session, 6, "Hidden")
    mk_asset(session, 7, "Gone", active=False)
    mk_asset_perm(session, 7, target_code=str(PROPOSER))
    _assert_refused(session, client, proposer, _body(assets=[{"asset": 6, "type": "USED_BY"}]))
    _assert_refused(session, client, proposer, _body(assets=[{"asset": 7, "type": "USED_BY"}]))
    _assert_refused(session, client, proposer, _body(assets=[{"asset": 5, "type": "NOPE"}]))
    _assert_refused(session, client, proposer, _body(assets=[
        {"asset": 5, "type": "USED_BY"}, {"asset": 5, "type": "USED_BY"}]))


def test_same_asset_with_two_types_is_allowed(session, client):
    proposer = _world(session)
    mk_asset(session, 5, "Visible")
    mk_asset_perm(session, 5, target_code=str(PROPOSER))
    override(proposer)
    resp = client.post("/api/initiatives/propose", json=_body(assets=[
        {"asset": 5, "type": "USED_BY"}, {"asset": 5, "type": "CONTAINS"}]))
    assert resp.status_code == 201
    assert len(session.exec(select(AssetInit)).all()) == 2


def test_non_admin_self_review_refused(session, client):
    mk_user_row(session, 30, "rev_prop", profile="REVIEWER")
    proposer = _world(session, proposer_profile="REVIEWER")
    _assert_refused(session, client, proposer, _body(reviewer_id=PROPOSER))


def test_no_eligible_reviewer_refused(session, client):
    seed_core_lists(session)
    seed_criteria_with_scale(session, codes=("C1", "C2"))
    mk_user_row(session, PROPOSER, "prop", profile=COLLAB)
    seed_privileges(session, profile=COLLAB, options=("EXPLORE",), can_edit=True)
    _assert_refused(session, client, user(PROPOSER, profile=COLLAB), _body(reviewer_id=None))


# ── Access ──────────────────────────────────────────────────────────────────

def test_read_only_explore_privilege_cannot_propose(session, client):
    seed_core_lists(session)
    seed_criteria_with_scale(session, codes=("C1", "C2"))
    mk_user_row(session, REVIEWER, "rev", profile="REVIEWER")
    seed_privileges(session, profile=COLLAB, options=("EXPLORE",), can_edit=False)
    override(user(PROPOSER, profile=COLLAB))
    assert client.post("/api/initiatives/propose", json=_body()).status_code == 403


def test_no_inits_privilege_cannot_propose(session, client):
    override(user(PROPOSER, profile=COLLAB))
    assert client.post("/api/initiatives/propose", json=_body()).status_code == 403


# ── Linkable assets (T022) ─────────────────────────────────────────────────

def test_linkable_assets_lists_only_visible(session, client):
    proposer = _world(session)
    mk_asset(session, 5, "Visible")
    mk_asset_perm(session, 5, target_code=str(PROPOSER))
    mk_asset(session, 6, "Hidden")
    override(proposer)
    resp = client.get("/api/initiatives/linkable-assets")
    assert resp.status_code == 200
    assert [a["value"] for a in data(resp)] == [5]

    override(superuser())
    assert {a["value"] for a in data(client.get("/api/initiatives/linkable-assets"))} == {5, 6}


# ── Reviewers (T028, US2) ──────────────────────────────────────────────────

def test_reviewers_exclude_non_admin_caller(session, client):
    _world(session, proposer_profile="REVIEWER")
    override(user(PROPOSER, profile="REVIEWER"))
    ids = [r["value"] for r in data(client.get("/api/initiatives/reviewers"))]
    assert PROPOSER not in ids and REVIEWER in ids


def test_reviewers_include_admin_caller(session, client):
    _world(session, proposer_profile="ADMINISTRATIVE")
    override(user(PROPOSER, profile="ADMINISTRATIVE"))
    ids = [r["value"] for r in data(client.get("/api/initiatives/reviewers"))]
    assert PROPOSER in ids


def test_reviewers_need_an_inits_privilege(session, client):
    override(user(PROPOSER, profile=COLLAB))
    assert client.get("/api/initiatives/reviewers").status_code == 403


def test_auto_assign_never_picks_non_admin_proposer(session, client):
    _world(session, proposer_profile="REVIEWER")  # proposer 10 < reviewer 20
    override(user(PROPOSER, profile="REVIEWER"))
    resp = client.post("/api/initiatives/propose", json=_body(reviewer_id=None))
    assert resp.status_code == 201, resp.text
    diag = session.exec(select(Collaboration).where(Collaboration.type == "DIAGNOSIS")).one()
    assert diag.user_id == REVIEWER
