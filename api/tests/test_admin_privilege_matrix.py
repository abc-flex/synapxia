"""Privilege matrix — `/api/privileges/profile/{code}/matrix` (GET + PUT).

One profile's access over the whole active option catalog, saved as one set.
"""
from sqlmodel import select

from app.admin.internal.models import Module, Option, Privilege, Profile
from app.auth.routes import current_active_user
from app.main import app
from tests.inits_helpers import data, override, superuser, user

URL = "/api/privileges/profile/{}/matrix"
ADMIN = "ADMINISTRATIVE"


def _seed(session, *, admin_can_edit=True):
    session.add_all([
        Profile(code=ADMIN, name="Admin"),
        Profile(code="COLLABORATOR", name="Collaborator"),
        Module(code="ADMIN", name="Administration", sort_order=1),
        Module(code="LIB", name="AI Library", sort_order=2),
        Module(code="OLD", name="Retired", sort_order=3, is_active=False),
        Option(module="ADMIN", code="PRIVILEGES", name="Privileges", type="CRUD", sort_order=2),
        Option(module="ADMIN", code="USERS", name="Users", type="CRUD", sort_order=1),
        Option(module="LIB", code="PROMPTS", name="Prompts", type="CARD_GALLERY"),
        Option(module="LIB", code="GONE", name="Gone", type="CRUD", is_active=False),
        Option(module="OLD", code="X", name="X", type="CRUD"),
        Privilege(profile=ADMIN, module="ADMIN", option="PRIVILEGES",
                  can_edit=admin_can_edit),
        Privilege(profile="COLLABORATOR", module="LIB", option="PROMPTS", can_edit=False),
        Privilege(profile="COLLABORATOR", module="LIB", option="GONE", can_edit=True),
    ])
    session.commit()
    override(user(1, profile=ADMIN))


def _rows(session, profile):
    return {
        (p.module, p.option): (p.can_edit, p.is_active)
        for p in session.exec(select(Privilege).where(Privilege.profile == profile)).all()
    }


def test_get_lists_active_catalog_with_access(client, session):
    _seed(session)
    m = data(client.get(URL.format("COLLABORATOR")))
    assert m["profile"] == "COLLABORATOR" and m["profile_name"] == "Collaborator"
    # Inactive modules and options are not in the catalog; order follows sort_order.
    assert [x["code"] for x in m["modules"]] == ["ADMIN", "LIB"]
    assert [o["code"] for o in m["modules"][0]["options"]] == ["USERS", "PRIVILEGES"]
    lib = m["modules"][1]["options"]
    assert [(o["code"], o["granted"], o["can_edit"]) for o in lib] == [("PROMPTS", True, False)]


def test_get_unknown_profile_404(client, session):
    _seed(session)
    assert client.get(URL.format("NOPE")).status_code == 404


def test_save_inserts_updates_revokes_and_reactivates(client, session):
    _seed(session)
    session.add(Privilege(profile="COLLABORATOR", module="ADMIN", option="USERS",
                          can_edit=False, is_active=False))
    session.commit()
    body = {"privileges": [
        {"module": "ADMIN", "option": "USERS", "can_edit": True},       # reactivated
        {"module": "ADMIN", "option": "PRIVILEGES", "can_edit": False},  # inserted
    ]}
    r = client.put(URL.format("COLLABORATOR"), json=body)
    assert r.status_code == 200, r.text
    session.expire_all()
    assert _rows(session, "COLLABORATOR") == {
        ("ADMIN", "USERS"): (True, True),
        ("ADMIN", "PRIVILEGES"): (False, True),
        ("LIB", "PROMPTS"): (False, False),   # revoked, row retained
        ("LIB", "GONE"): (True, True),        # outside the catalog: untouched
    }
    granted = {o["code"] for mod in data(r)["modules"] for o in mod["options"] if o["granted"]}
    assert granted == {"USERS", "PRIVILEGES"}


def test_save_rejects_unknown_inactive_and_duplicate_options(client, session):
    _seed(session)
    for bad in (
        [{"module": "LIB", "option": "NOPE"}],
        [{"module": "LIB", "option": "GONE"}],
        [{"module": "OLD", "option": "X"}],
        [{"module": "LIB", "option": "PROMPTS"}, {"module": "LIB", "option": "PROMPTS"}],
    ):
        assert client.put(URL.format("COLLABORATOR"), json={"privileges": bad}).status_code == 400
    session.expire_all()
    assert _rows(session, "COLLABORATOR")[("LIB", "PROMPTS")] == (False, True)


def test_cannot_lock_yourself_out(client, session):
    _seed(session)
    r = client.put(URL.format(ADMIN), json={"privileges": [
        {"module": "ADMIN", "option": "PRIVILEGES", "can_edit": False}]})
    assert r.status_code == 400
    r = client.put(URL.format(ADMIN), json={"privileges": [
        {"module": "ADMIN", "option": "PRIVILEGES", "can_edit": True},
        {"module": "ADMIN", "option": "USERS", "can_edit": True}]})
    assert r.status_code == 200
    # A superuser is never locked out, so the guard does not apply.
    override(superuser())
    assert client.put(URL.format(ADMIN), json={"privileges": []}).status_code == 200


def test_access_rules(client, session):
    _seed(session, admin_can_edit=False)
    assert client.get(URL.format("COLLABORATOR")).status_code == 200
    assert client.put(URL.format("COLLABORATOR"), json={"privileges": []}).status_code == 403
    assert client.put("/api/privileges/COLLABORATOR/LIB/PROMPTS",
                      json={"can_edit": True}).status_code == 403
    override(user(2, profile="COLLABORATOR"))
    assert client.get(URL.format("COLLABORATOR")).status_code == 403
    app.dependency_overrides.pop(current_active_user, None)
    assert client.get(URL.format("COLLABORATOR")).status_code == 401
