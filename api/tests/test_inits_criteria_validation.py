"""Diagnosis answer validation (inits/internal/criteria_validation.py, R10)."""
import pytest

from app.inits.internal import criteria_validation as cv
from app.inits.internal.models import DiagnosisAnswer
from tests.inits_helpers import mk_criteria, seed_criteria_with_scale


def _answers(**scores):
    return {code: DiagnosisAnswer(score=v) for code, v in scores.items()}


def test_complete_valid_answers_pass(session):
    seed_criteria_with_scale(session, codes=("C1", "C2"))
    out = cv.validate_creator_answers(session, _answers(C1=1, C2=3))
    assert set(out) == {"C1", "C2"}


def test_missing_criterion_refused(session):
    seed_criteria_with_scale(session, codes=("C1", "C2"))
    with pytest.raises(ValueError, match="missing: C2"):
        cv.validate_creator_answers(session, _answers(C1=1))


def test_unknown_code_refused(session):
    seed_criteria_with_scale(session, codes=("C1",))
    with pytest.raises(ValueError, match="Unknown"):
        cv.validate_creator_answers(session, _answers(C1=1, NOPE=1))


def test_inactive_criterion_is_not_required_and_not_accepted(session):
    seed_criteria_with_scale(session, codes=("C1",))
    mk_criteria(session, "OLD", list_code="C1", active=False)
    cv.validate_creator_answers(session, _answers(C1=2))
    with pytest.raises(ValueError, match="Unknown"):
        cv.validate_creator_answers(session, _answers(C1=2, OLD=2))


def test_out_of_scale_refused(session):
    seed_criteria_with_scale(session, codes=("C1",), values=(1, 2, 3))
    with pytest.raises(ValueError, match="not a valid answer"):
        cv.validate_creator_answers(session, _answers(C1=4))
    with pytest.raises(ValueError, match="not a valid answer"):
        cv.validate_reviewer_answers(session, {"C1": 0})


def test_zero_active_criteria_accepts_empty(session):
    assert cv.validate_creator_answers(session, {}) == {}
    assert cv.validate_reviewer_answers(session, {}) == {}


def test_blank_rationale_normalised(session):
    seed_criteria_with_scale(session, codes=("C1",))
    out = cv.validate_creator_answers(
        session, {"C1": DiagnosisAnswer(score=1, rationale="   ")})
    assert out["C1"].rationale is None


# ── GET /api/initiatives/diagnosis-form ─────────────────────────────────────

from tests.inits_helpers import COLLAB, data, override, seed_privileges, user  # noqa: E402


def test_diagnosis_form_active_criteria_and_localized_scales(session, client):
    seed_criteria_with_scale(session, codes=("C1",), values=(1, 2))
    mk_criteria(session, "OLD", list_code="C1", active=False)
    seed_privileges(session, profile=COLLAB, options=("EXPLORE",), can_edit=False)
    override(user(1, profile=COLLAB))
    body = data(client.get("/api/initiatives/diagnosis-form", params={"lang": "es"}))
    assert [i["criteria"] for i in body["items"]] == ["C1"]
    assert body["scales"]["C1"] == [{"value": 1, "label": "C1-es-1"}, {"value": 2, "label": "C1-es-2"}]


def test_diagnosis_form_needs_an_inits_privilege(session, client):
    override(user(1, profile=COLLAB))
    assert client.get("/api/initiatives/diagnosis-form").status_code == 403
