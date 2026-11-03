"""Specification matrix — `/api/specifications/category/{code}/matrix` (GET + PUT).

One category's specification over the whole active feature catalog, saved as one set.
"""
from sqlmodel import select

from app.admin.internal.models import ListItem, Module, Option, Privilege, Profile
from app.auth.routes import current_active_user
from app.main import app
from app.taxo.internal.models import Category, Feature, Specification
from tests.inits_helpers import data, override, superuser, user

URL = "/api/specifications/category/{}/matrix"
ADMIN = "ADMINISTRATOR"


def _seed(session, *, can_edit=True):
    session.add_all([
        Profile(code=ADMIN, name="Admin"),
        Profile(code="COLLABORATOR", name="Collaborator"),
        Module(code="TAXO", name="Taxonomy"),
        Option(module="TAXO", code="CATEGORIES", name="Categories", type="CRUD"),
        Privilege(profile=ADMIN, module="TAXO", option="CATEGORIES", can_edit=can_edit),
        Category(code="PROMPTS", name="Prompts"),
        Feature(code="MODE", name="Mode", type="GENERAL", list="EXECUTION_MODE"),
        Feature(code="PLATFORM", name="Platform", type="TECHNICAL"),
        Feature(code="TOOLS", name="Tools", type="TECHNICAL"),
        Feature(code="GONE", name="Gone", type="GENERAL", is_active=False),
        ListItem(list="EXECUTION_MODE", lang="en", value="REMOTE", label="Remote"),
        Specification(category="PROMPTS", feature="PLATFORM", default_value="VSCode",
                      required=True, sort_order=10),
        Specification(category="PROMPTS", feature="TOOLS", copyable=True, sort_order=20,
                      is_active=False),
        Specification(category="PROMPTS", feature="GONE", sort_order=30),
    ])
    session.commit()
    override(user(1, profile=ADMIN))


def _rows(session):
    return {
        s.feature: (s.default_value, s.required, s.copyable, s.sort_order, s.is_active)
        for s in session.exec(select(Specification).where(Specification.category == "PROMPTS")).all()
    }


def test_get_lists_every_active_feature(client, session):
    _seed(session)
    m = data(client.get(URL.format("PROMPTS")))
    assert m["category"] == "PROMPTS" and m["category_name"] == "Prompts"
    by_code = {f["code"]: f for f in m["features"]}
    assert set(by_code) == {"MODE", "PLATFORM", "TOOLS"}   # inactive feature left out
    assert by_code["PLATFORM"]["specified"] is True
    assert by_code["PLATFORM"]["default_value"] == "VSCode" and by_code["PLATFORM"]["required"]
    assert by_code["TOOLS"]["specified"] is False           # inactive spec is not specified
    assert by_code["MODE"]["list"] == "EXECUTION_MODE"


def test_get_unknown_category_404(client, session):
    _seed(session)
    assert client.get(URL.format("NOPE")).status_code == 404


def test_save_inserts_updates_removes_and_reactivates(client, session):
    _seed(session)
    r = client.put(URL.format("PROMPTS"), json={"specifications": [
        {"feature": "TOOLS", "copyable": True, "sort_order": 5},
        {"feature": "MODE", "default_value": " REMOTE ", "required": True, "sort_order": 15},
    ]})
    assert r.status_code == 200, r.text
    session.expire_all()
    assert _rows(session) == {
        "PLATFORM": ("VSCode", True, False, 10, False),   # left out: removed
        "TOOLS": (None, False, True, 5, True),            # reactivated
        "MODE": ("REMOTE", True, False, 15, True),        # inserted, value trimmed
        "GONE": (None, False, False, 30, True),           # outside the catalog: untouched
    }
    assert {f["code"] for f in data(r)["features"] if f["specified"]} == {"TOOLS", "MODE"}


def test_save_rejects_invalid_sets(client, session):
    _seed(session)
    for bad in (
        [{"feature": "NOPE"}],
        [{"feature": "GONE"}],
        [{"feature": "MODE"}, {"feature": "MODE"}],
        [{"feature": "MODE", "default_value": "LOCAL"}],   # not a value of its list
    ):
        assert client.put(URL.format("PROMPTS"), json={"specifications": bad}).status_code == 400
    session.expire_all()
    assert _rows(session)["PLATFORM"][4] is True


def test_access_rules(client, session):
    _seed(session, can_edit=False)
    assert client.get(URL.format("PROMPTS")).status_code == 200
    assert client.put(URL.format("PROMPTS"), json={"specifications": []}).status_code == 403
    override(user(2, profile="COLLABORATOR"))
    assert client.get(URL.format("PROMPTS")).status_code == 403
    override(superuser())
    assert client.put(URL.format("PROMPTS"), json={"specifications": []}).status_code == 200
    app.dependency_overrides.pop(current_active_user, None)
    assert client.get(URL.format("PROMPTS")).status_code == 401
