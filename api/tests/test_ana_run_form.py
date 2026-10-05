"""Run form — `GET /api/dashboards/{id}/run-form` (specs/007-dashboard-catalog US2)."""
from tests.catalog_helpers import (
    data, mk_dashboard, mk_execution, mk_grant, mk_list, mk_list_def, mk_param, override,
    setup_catalog, viewer,
)


def url(d):
    return f"/api/dashboards/{d.id}/run-form"


def test_guards(client, session):
    d = setup_catalog(session)
    draft = mk_dashboard(session, name="Draft", status="DRAFT")
    mk_grant(session, draft.id, "USER", "1", access_level="VIEW")
    hidden = mk_dashboard(session, name="Hidden", status="PUBLISHED")
    gone = mk_dashboard(session, name="Gone", status="PUBLISHED", is_active=False)
    mk_grant(session, gone.id, "USER", "1", access_level="VIEW")
    override(viewer())
    assert client.get(url(d)).status_code == 200
    assert client.get(url(draft)).status_code == 403
    assert client.get(url(hidden)).status_code == 403
    assert client.get(url(gone)).status_code == 404
    assert client.get("/api/dashboards/999999/run-form").status_code == 404


def test_mode(client, session):
    d = setup_catalog(session)
    internal = mk_dashboard(session, name="Internal", status="PUBLISHED",
                            sources_types="INTERNAL_PAGE", source_url="/support")
    mk_grant(session, internal.id, "USER", "1", access_level="VIEW")
    override(viewer())
    assert data(client.get(url(d)))["mode"] == "TAB"
    assert data(client.get(url(internal)))["mode"] == "VIEWER"


def test_parameters_by_effective_source(client, session):
    d = setup_catalog(session, grant=("PUBLIC", "ALL"))
    unit = mk_grant(session, d.id, "UNIT", "ENG", access_level="VIEW")
    mk_list(session, "GRANULARITY", [("DAY", "Día"), ("WEEK", "Semana"), ("MONTH", "Mes")], lang="es")
    mk_list_def(session, "EMPTY", name="Empty")
    mk_param(session, d.id, "unit", label="Unit", context_binding=unit.id)
    mk_param(session, d.id, "gran", label="Granularity", list="GRANULARITY", default_value="WEEK")
    mk_param(session, d.id, "top", label="Top", data_type="NUMBER", is_required=True)
    mk_param(session, d.id, "empty", list="EMPTY")
    override(viewer())
    form = data(client.get(url(d)))
    by = {p["name"]: p for p in form["parameters"]}
    assert [p["name"] for p in form["parameters"]] == ["empty", "gran", "top", "unit"]
    assert by["unit"]["effective_source"] == "GRANT"
    assert by["unit"]["bound_value"] == "ENG" and by["unit"]["bound_label"] == "UNIT ENG"
    assert by["gran"]["effective_source"] == "LIST" and by["gran"]["default_value"] == "WEEK"
    langs = {(o["value"], o["lang"]) for o in by["gran"]["options"]}
    assert ("WEEK", "en") in langs and ("WEEK", "es") in langs
    assert by["top"]["effective_source"] == "INPUT" and by["top"]["is_required"] is True
    assert by["top"]["options"] is None
    assert by["empty"]["list_unavailable"] is True and by["empty"]["options"] == []


def test_has_last_values(client, session):
    d = setup_catalog(session)
    override(viewer())
    assert data(client.get(url(d)))["has_last_values"] is False
    mk_execution(session, d.id, user_id=1, status="FAILED")
    mk_execution(session, d.id, user_id=1, status=None)
    mk_execution(session, d.id, user_id=2, status="SUCCESS")
    assert data(client.get(url(d)))["has_last_values"] is False
    mk_execution(session, d.id, user_id=1, status="SUCCESS")
    assert data(client.get(url(d)))["has_last_values"] is True
