"""Option catalog — `GET /api/options/catalog`, backing `/admin/options`.

Every active option of every active module, not scoped to the caller's own
privileges (unlike `GET /api/options/`).
"""
from app.admin.internal.models import Module, Option, Privilege, Profile
from tests.inits_helpers import data, override, user

URL = "/api/options/catalog"
ADMIN = "ADMINISTRATIVE"


def _seed(session, *, can_read=True):
    session.add_all([
        Profile(code=ADMIN, name="Admin"),
        Module(code="ADMIN", name="Administration", sort_order=1, icon="wrench-screwdriver"),
        Module(code="LIB", name="AI Library", sort_order=2, icon="ai-library"),
        Module(code="OLD", name="Retired", sort_order=3, is_active=False),
        Option(module="ADMIN", code="OPTIONS", name="Options", type="FORM", sort_order=2,
               path="/admin/options", icon="adjustments-horizontal"),
        Option(module="ADMIN", code="USERS", name="Users", type="FORM", sort_order=1),
        Option(module="LIB", code="PROMPTS", name="Prompts", type="CARD_GALLERY"),
        Option(module="LIB", code="GONE", name="Gone", type="FORM", is_active=False),
        Option(module="OLD", code="X", name="X", type="FORM"),
    ])
    if can_read:
        session.add(Privilege(profile=ADMIN, module="ADMIN", option="OPTIONS", can_edit=False))
    session.commit()
    override(user(1, profile=ADMIN))


def test_lists_active_modules_with_active_options_in_order(client, session):
    _seed(session)
    mods = data(client.get(URL))
    assert [m["code"] for m in mods] == ["ADMIN", "LIB"]
    assert mods[0]["icon"] == "wrench-screwdriver"
    assert [o["code"] for o in mods[0]["options"]] == ["USERS", "OPTIONS"]
    opt = mods[0]["options"][1]
    assert opt["icon"] == "adjustments-horizontal" and opt["path"] == "/admin/options"
    assert opt["type"] == "FORM" and opt["sort_order"] == 2
    # Not scoped to the caller: LIB/PROMPTS is listed without a privilege on it.
    assert [o["code"] for o in mods[1]["options"]] == ["PROMPTS"]


def test_requires_options_privilege(client, session):
    _seed(session, can_read=False)
    assert client.get(URL).status_code == 403
