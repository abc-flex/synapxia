"""Dashboard Management — `GET /api/dashboards/parameter-lists`
(the allowed-values lists a parameter may use; specs/006, R7)."""
from tests.ana_helpers import data, mk_list_def, override, seed_ana_lists, seed_privileges, user

URL = "/api/dashboards/parameter-lists"


def test_only_active_list_of_values_lists(client, session):
    seed_privileges(session)
    seed_ana_lists(session)  # GRANULARITY (LoV) + TREE (HIERARCHY)
    mk_list_def(session, "ARCHIVED_LIST", name="Archived", active=False)
    mk_list_def(session, "ALPHA", name="Alpha")
    override(user(1))
    r = client.get(URL)
    assert r.status_code == 200
    assert data(r) == [
        {"value": "ALPHA", "label": "Alpha"},
        {"value": "GRANULARITY", "label": "Granularity"},
    ]


def test_requires_rbac(client, session):
    override(user(1))
    assert client.get(URL).status_code == 403


def test_requires_token(client, session):
    assert client.get(URL).status_code == 401
