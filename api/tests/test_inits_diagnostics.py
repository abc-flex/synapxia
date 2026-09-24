"""Diagnosis Questions read model — `GET /api/initiatives/{id}/diagnostics`."""
from tests.inits_helpers import (
    data, mk_criteria, mk_diag, mk_init, mk_list, mk_perm, override,
    seed_privileges, user,
)

SCALE_EN = [("1", "Low"), ("2", "Medium"), ("3", "High")]
SCALE_ES = [("1", "Baja"), ("2", "Media"), ("3", "Alta")]


def _setup(session, grant=True):
    seed_privileges(session, can_edit=False)
    init = mk_init(session, score=11)
    if grant:
        mk_perm(session, init.id, "USER", "1", access_level="VIEW")
    for code in ("A", "B"):
        mk_criteria(session, code)
        mk_list(session, code, SCALE_EN, lang="en")
        mk_list(session, code, SCALE_ES, lang="es")
    return init


def _get(client, init_id, **params):
    return client.get(f"/api/initiatives/{init_id}/diagnostics", params=params)


def test_one_row_per_active_criterion_with_labels(client, session):
    init = _setup(session)
    mk_diag(session, init.id, "A", creator=2, reviewer=3, rationale="why")
    override(user(1))
    body = data(_get(client, init.id))
    assert body["score"] == 11
    rows = {r["criteria"]: r for r in body["items"]}
    assert set(rows) == {"A", "B"}
    assert rows["A"]["creator_label"] == "Medium"
    assert rows["A"]["reviewer_label"] == "High"
    assert rows["A"]["rationale"] == "why"
    assert rows["B"]["creator_score"] is None and rows["B"]["creator_label"] is None


def test_spanish_labels_with_english_fallback(client, session):
    init = _setup(session)
    mk_criteria(session, "C")
    mk_list(session, "C", SCALE_EN, lang="en")  # no Spanish rows for C
    mk_diag(session, init.id, "A", creator=1)
    mk_diag(session, init.id, "C", creator=3)
    override(user(1))
    rows = {r["criteria"]: r for r in data(_get(client, init.id, lang="es"))["items"]}
    assert rows["A"]["creator_label"] == "Baja"
    assert rows["C"]["creator_label"] == "High"


def test_raw_value_when_no_label_exists(client, session):
    init = _setup(session)
    mk_criteria(session, "NOLIST", list_code="MISSING")
    mk_diag(session, init.id, "NOLIST", creator=2)
    override(user(1))
    rows = {r["criteria"]: r for r in data(_get(client, init.id))["items"]}
    assert rows["NOLIST"]["creator_label"] == "2"


def test_pending_reviewer_answer(client, session):
    init = _setup(session)
    mk_diag(session, init.id, "A", creator=2)
    override(user(1))
    row = next(r for r in data(_get(client, init.id))["items"] if r["criteria"] == "A")
    assert row["reviewer_score"] is None and row["reviewer_label"] is None


def test_inactive_criterion_only_when_answered(client, session):
    init = _setup(session)
    mk_criteria(session, "OLD", active=False)
    mk_criteria(session, "OLD2", active=False)
    mk_list(session, "OLD", SCALE_EN)
    mk_diag(session, init.id, "OLD", creator=1)
    override(user(1))
    rows = {r["criteria"]: r for r in data(_get(client, init.id))["items"]}
    assert "OLD" in rows and rows["OLD"]["is_active_criteria"] is False
    assert "OLD2" not in rows


def test_requires_view_and_existing_initiative(client, session):
    init = _setup(session, grant=False)
    override(user(1))
    assert _get(client, init.id).status_code == 403
    assert _get(client, 999).status_code == 404


def test_rejects_unknown_lang(client, session):
    init = _setup(session)
    override(user(1))
    assert _get(client, init.id, lang="fr").status_code in (400, 422)


def test_overall_score_per_party(client, session):
    init = _setup(session)
    mk_diag(session, init.id, "A", creator=2, reviewer=3)
    mk_diag(session, init.id, "B", creator=1)
    override(user(1))
    body = data(_get(client, init.id))
    assert (body["creator_total"], body["creator_answered"]) == (3, 2)
    assert (body["reviewer_total"], body["reviewer_answered"]) == (3, 1)


def test_reviewer_total_null_when_undiagnosed(client, session):
    init = _setup(session)
    mk_diag(session, init.id, "A", creator=2)
    override(user(1))
    body = data(_get(client, init.id))
    assert body["reviewer_total"] is None and body["reviewer_answered"] == 0
