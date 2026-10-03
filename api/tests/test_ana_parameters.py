"""Dashboard Management — `/api/dashboards/{id}/parameters`
(specs/006-dashboard-management, US3 / FR-014–FR-018)."""
from app.insights.internal.models import Parameter
from tests.ana_helpers import (
    PAST, data, mk_dashboard, mk_grant, mk_param, override, setup_owner, user,
)


def base(d):
    return f"/api/dashboards/{d.id}/parameters"


def _post(client, d, **kw):
    body = {"name": "date_from", "label": "From", "data_type": "DATE", **kw}
    return client.post(base(d), json=body)


# ── GET ─────────────────────────────────────────────────────────────────────

def test_list_active_with_derived_source(client, session):
    d = setup_owner(session, access="VIEW")
    grant = mk_grant(session, d.id, "TEAM", "ANALYTICS", access_level="VIEW")
    mk_param(session, d.id, "team", context_binding=grant.id)
    mk_param(session, d.id, "granularity", list="GRANULARITY")
    mk_param(session, d.id, "min_events", data_type="NUMBER")
    mk_param(session, d.id, "gone", is_active=False)
    override(user(1))
    r = client.get(base(d))
    assert r.status_code == 200
    rows = {p["name"]: p for p in data(r)}
    assert set(rows) == {"team", "granularity", "min_events"}
    assert rows["team"]["value_source"] == "GRANT"
    assert rows["team"]["binding_label"] == "TEAM ANALYTICS"
    assert rows["granularity"]["value_source"] == "LIST"
    assert rows["min_events"]["value_source"] == "INPUT"
    assert rows["min_events"]["binding_label"] is None


def test_list_requires_view(client, session):
    setup_owner(session)
    other = mk_dashboard(session, name="Other")
    override(user(1))
    assert client.get(base(other)).status_code == 403


# ── POST ────────────────────────────────────────────────────────────────────

def test_create_and_duplicates(client, session):
    d = setup_owner(session)
    override(user(1))
    r = _post(client, d, default_value="2026-01-01", is_required=True)
    assert r.status_code == 201
    assert data(r)["value_source"] == "INPUT" and data(r)["is_required"] is True
    assert _post(client, d).status_code == 409


def test_readding_a_removed_name_restores_it(client, session):
    d = setup_owner(session)
    mk_param(session, d.id, "date_from", label="Old", data_type="STRING", is_active=False)
    override(user(1))
    r = _post(client, d, label="New")
    assert r.status_code == 200
    assert data(r)["label"] == "New" and data(r)["data_type"] == "DATE"
    session.expire_all()
    assert session.get(Parameter, (d.id, "date_from")).is_active is True


def test_name_and_type_rules(client, session):
    d = setup_owner(session)
    override(user(1))
    for bad in ("Date From", "1x", "date-from", "a" * 101, ""):
        assert _post(client, d, name=bad).status_code == 400, bad
    assert _post(client, d, data_type="TEXT").status_code == 400
    assert _post(client, d, label="  ").status_code == 400


def test_default_must_match_type(client, session):
    d = setup_owner(session)
    override(user(1))
    cases = [
        ("NUMBER", "abc", 400), ("NUMBER", "1.5", 201), ("NUMBER", "-10", 201),
        ("BOOLEAN", "yes", 400), ("BOOLEAN", "true", 201),
        ("DATE", "2026-13-01", 400), ("DATE", "01/01/2026", 400), ("DATE", "2026-02-30", 400),
        ("DATE", "2026-01-01", 201), ("STRING", "anything", 201),
    ]
    for i, (dtype, default, expected) in enumerate(cases):
        r = _post(client, d, name=f"p{i}", data_type=dtype, default_value=default)
        assert r.status_code == expected, (dtype, default, r.json())


def test_list_rules(client, session):
    d = setup_owner(session)
    override(user(1))
    assert _post(client, d, name="a", data_type="STRING", list="NOPE").status_code == 400
    assert _post(client, d, name="b", data_type="STRING", list="TREE").status_code == 400
    assert _post(client, d, name="c", data_type="STRING", list="GRANULARITY",
                 default_value="YEAR").status_code == 400
    r = _post(client, d, name="d", data_type="STRING", list="GRANULARITY", default_value="WEEK")
    assert r.status_code == 201 and data(r)["value_source"] == "LIST"


def test_binding_rules(client, session):
    d = setup_owner(session)
    other = mk_dashboard(session, name="Other")
    team = mk_grant(session, d.id, "TEAM", "ANALYTICS", access_level="VIEW")
    public = mk_grant(session, d.id, "PUBLIC", "ALL", access_level="VIEW")
    revoked = mk_grant(session, d.id, "TEAM", "LAB", access_level="VIEW", valid_to=PAST)
    foreign = mk_grant(session, other.id, "TEAM", "ANALYTICS", access_level="VIEW")
    override(user(1))
    for i, gid in enumerate((public.id, revoked.id, foreign.id, 9999)):
        r = _post(client, d, name=f"t{i}", data_type="STRING", context_binding=gid)
        assert r.status_code == 400, gid
    r = _post(client, d, name="team", data_type="STRING", context_binding=team.id,
              list="GRANULARITY")
    assert r.status_code == 201
    assert data(r)["value_source"] == "GRANT"


def test_view_holder_cannot_write(client, session):
    d = setup_owner(session, access="VIEW")
    mk_param(session, d.id, "x")
    override(user(1))
    assert _post(client, d).status_code == 403
    assert client.put(f"{base(d)}/x", json={"label": "Y"}).status_code == 403
    assert client.delete(f"{base(d)}/x").status_code == 403


# ── PUT / DELETE ────────────────────────────────────────────────────────────

def test_update_partial_and_revalidated(client, session):
    d = setup_owner(session)
    mk_param(session, d.id, "min", data_type="STRING", default_value="abc")
    override(user(1))
    r = client.put(f"{base(d)}/min", json={"label": "Minimum"})
    assert r.status_code == 200 and data(r)["label"] == "Minimum"
    # Switching to NUMBER re-checks the stored default.
    assert client.put(f"{base(d)}/min", json={"data_type": "NUMBER"}).status_code == 400
    r = client.put(f"{base(d)}/min", json={"data_type": "NUMBER", "default_value": "3"})
    assert r.status_code == 200 and data(r)["default_value"] == "3"
    assert client.put(f"{base(d)}/nope", json={"label": "X"}).status_code == 404


def test_update_switches_source(client, session):
    d = setup_owner(session)
    team = mk_grant(session, d.id, "TEAM", "ANALYTICS", access_level="VIEW")
    mk_param(session, d.id, "team", list="GRANULARITY", context_binding=team.id)
    override(user(1))
    r = client.put(f"{base(d)}/team", json={"context_binding": None})
    assert data(r)["value_source"] == "LIST"
    r = client.put(f"{base(d)}/team", json={"list": None})
    assert data(r)["value_source"] == "INPUT"


def test_name_in_body_is_ignored(client, session):
    d = setup_owner(session)
    mk_param(session, d.id, "x")
    override(user(1))
    r = client.put(f"{base(d)}/x", json={"name": "renamed", "label": "L"})
    assert r.status_code == 200 and data(r)["name"] == "x"


def test_delete_is_logical(client, session):
    d = setup_owner(session)
    mk_param(session, d.id, "x")
    override(user(1))
    assert client.delete(f"{base(d)}/x").status_code == 200
    assert data(client.get(base(d))) == []
    session.expire_all()
    assert session.get(Parameter, (d.id, "x")).is_active is False
    assert client.delete(f"{base(d)}/x").status_code == 404


def test_missing_dashboard(client, session):
    setup_owner(session)
    override(user(1))
    assert client.get("/api/dashboards/999/parameters").status_code == 404
