"""List value matrix — `/api/list_items/matrix/{list}` (GET + PUT).

One list's values, each with its order and a label per language, saved as one set.
"""
from sqlmodel import select

from app.admin.internal.models import List as ListModel, ListItem, Module, Option, Privilege, Profile
from app.auth.routes import current_active_user
from app.main import app
from tests.inits_helpers import data, override, superuser, user

URL = "/api/list_items/matrix/{}"
ADMIN = "ADMINISTRATOR"


def _seed(session, *, can_edit=True):
    session.add_all([
        Profile(code=ADMIN, name="Admin"),
        Profile(code="COLLABORATOR", name="Collaborator"),
        Module(code="ADMIN", name="Administration"),
        Option(module="ADMIN", code="LISTS", name="Lists", type="CRUD"),
        Privilege(profile=ADMIN, module="ADMIN", option="LISTS", can_edit=can_edit),
        ListModel(code="STATUS", name="Statuses", type="LIST_OF_VALUES"),
        ListItem(list="STATUS", lang="en", value="OPEN", label="Open", sort_order=1),
        ListItem(list="STATUS", lang="es", value="OPEN", label="Abierto", sort_order=1),
        ListItem(list="STATUS", lang="en", value="DONE", label="Done", sort_order=2),
        ListItem(list="STATUS", lang="es", value="DONE", label="Hecho", sort_order=2,
                 is_active=False),
        ListItem(list="STATUS", lang="en", value="OLD", label="Old", sort_order=3,
                 is_active=False),
    ])
    session.commit()
    override(user(1, profile=ADMIN))


def _rows(session):
    return {
        (r.value, r.lang): (r.label, r.sort_order, r.is_active)
        for r in session.exec(select(ListItem).where(ListItem.list == "STATUS")).all()
    }


def test_get_groups_active_rows_by_value(client, session):
    _seed(session)
    m = data(client.get(URL.format("STATUS")))
    assert m["list"] == "STATUS" and m["list_name"] == "Statuses"
    assert m["languages"] == ["en", "es"]
    assert m["values"] == [
        {"value": "OPEN", "sort_order": 1, "labels": {"en": "Open", "es": "Abierto"}},
        {"value": "DONE", "sort_order": 2, "labels": {"en": "Done"}},
    ]


def test_get_unknown_list_404(client, session):
    _seed(session)
    assert client.get(URL.format("NOPE")).status_code == 404


def test_save_inserts_updates_removes_and_reactivates(client, session):
    _seed(session)
    r = client.put(URL.format("STATUS"), json={"values": [
        {"value": "DONE", "sort_order": 1, "labels": {"en": "Finished", "es": "Hecho"}},
        {"value": "OPEN", "sort_order": 2, "labels": {"en": "Open", "es": "  "}},
        {"value": "NEW", "sort_order": 3, "labels": {"es": "Nuevo"}},
    ]})
    assert r.status_code == 200, r.text
    session.expire_all()
    assert _rows(session) == {
        ("DONE", "en"): ("Finished", 1, True),
        ("DONE", "es"): ("Hecho", 1, True),      # reactivated
        ("OPEN", "en"): ("Open", 2, True),
        ("OPEN", "es"): ("Abierto", 1, False),   # blank label removes the language
        ("OLD", "en"): ("Old", 3, False),        # already removed: untouched
        ("NEW", "es"): ("Nuevo", 3, True),       # inserted
    }
    assert [v["value"] for v in data(r)["values"]] == ["DONE", "OPEN", "NEW"]


def test_save_left_out_value_is_removed(client, session):
    _seed(session)
    r = client.put(URL.format("STATUS"), json={"values": [
        {"value": "OPEN", "sort_order": 1, "labels": {"en": "Open", "es": "Abierto"}}]})
    assert r.status_code == 200
    session.expire_all()
    assert _rows(session)[("DONE", "en")][2] is False


def test_save_rejects_invalid_sets(client, session):
    _seed(session)
    for bad in (
        [{"value": " ", "labels": {"en": "X"}}],
        [{"value": "A", "labels": {"en": " "}}],
        [{"value": "A", "labels": {"en": "x"}}, {"value": "A", "labels": {"es": "y"}}],
        [{"value": "A", "labels": {"toolonglang": "x"}}],
        [{"value": "A", "labels": {"en": "x" * 201}}],
    ):
        assert client.put(URL.format("STATUS"), json={"values": bad}).status_code == 400
    session.expire_all()
    assert _rows(session)[("OPEN", "en")] == ("Open", 1, True)


def test_access_rules(client, session):
    _seed(session, can_edit=False)
    assert client.get(URL.format("STATUS")).status_code == 200
    assert client.put(URL.format("STATUS"), json={"values": []}).status_code == 403
    override(user(2, profile="COLLABORATOR"))
    assert client.get(URL.format("STATUS")).status_code == 403
    override(superuser())
    assert client.put(URL.format("STATUS"), json={"values": []}).status_code == 200
    app.dependency_overrides.pop(current_active_user, None)
    assert client.get(URL.format("STATUS")).status_code == 401
