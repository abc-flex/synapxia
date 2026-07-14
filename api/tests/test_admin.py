"""Admin contract tests — Constitution Principle II (contract stability).

Guards the admin models against db/sql/11-admin-ddl.sql: every column present,
`profiles.icon` exposed (was missing entirely), and `max_length` caps aligned
to the DDL so valid long values (e.g. a 244-char email) don't fail validation.
"""

from annotated_types import MaxLen

from app.admin.internal.models import (
    Module, ModuleCreate, ModuleUpdate,
    BusinessUnit, BusinessUnitCreate, BusinessUnitUpdate,
    List as ListModel, ListCreate, ListUpdate,
    ListItem, ListItemCreate, ListItemUpdate,
    Profile, ProfileCreate, ProfileUpdate,
    User, UserCreate, UserUpdate,
    Option, OptionCreate, OptionUpdate,
    Privilege,
)


def _max_len(model, field):
    for meta in model.model_fields[field].metadata:
        if isinstance(meta, MaxLen):
            return meta.max_length
    return None


def test_profile_models_expose_icon():
    """`profiles.icon` (TEXT) must be on the table model and both write schemas."""
    assert "icon" in Profile.model_fields
    assert "icon" in ProfileCreate.model_fields
    assert "icon" in ProfileUpdate.model_fields
    assert _max_len(Profile, "icon") is None  # TEXT → unbounded


def test_profile_create_round_trips_icon():
    payload = ProfileCreate(code="ADMIN", name="Admin", icon="heroicon-shield")
    row = Profile.model_validate(payload)
    assert row.icon == "heroicon-shield"


def test_varchar_lengths_match_ddl():
    """API max_length caps must match the DDL VARCHAR(n) widths."""
    assert _max_len(Module, "description") == 500       # VARCHAR(500)
    assert _max_len(ListModel, "description") == 500     # VARCHAR(500)
    assert _max_len(Profile, "description") == 500       # VARCHAR(500)
    assert _max_len(BusinessUnit, "type") == 100         # VARCHAR(100)
    assert _max_len(ListItem, "label") == 200            # VARCHAR(200)
    assert _max_len(User, "email") == 244                # VARCHAR(244)


def test_option_text_columns_unbounded():
    """options.path / options.icon are TEXT in the DDL — must be unbounded."""
    assert _max_len(Option, "path") is None
    assert _max_len(Option, "icon") is None


def test_admin_models_match_ddl_fields():
    """Every DDL column must be present on each table model (regression guard)."""
    expected = {
        Module: ("code", "name", "description", "sort_order", "icon",
                 "is_active", "created_at", "updated_at"),
        BusinessUnit: ("code", "name", "description", "type", "parent",
                       "is_active", "created_at", "updated_at"),
        ListModel: ("code", "name", "description", "module", "type",
                    "is_active", "created_at", "updated_at"),
        ListItem: ("list", "lang", "value", "label", "sort_order",
                   "is_active", "created_at", "updated_at"),
        Profile: ("code", "name", "description", "icon", "is_active",
                  "created_at", "updated_at"),
        User: ("id", "username", "email", "password_hash", "first_name",
               "last_name", "profile", "unit", "is_superuser", "is_verified",
               "is_active", "created_at", "updated_at", "last_login_at"),
        Option: ("module", "code", "name", "description", "path", "icon",
                 "type", "sort_order", "is_active", "created_at", "updated_at"),
        Privilege: ("profile", "module", "option", "can_edit", "is_active",
                    "created_at", "updated_at"),
    }
    for model, fields in expected.items():
        missing = [f for f in fields if f not in model.model_fields]
        assert not missing, f"{model.__name__} missing DDL fields: {missing}"


def test_openapi_profile_schema_includes_icon():
    from app.main import app

    schemas = app.openapi()["components"]["schemas"]
    assert "icon" in schemas["Profile"]["properties"]
    assert "icon" in schemas["ProfileCreate"]["properties"]
    assert "icon" in schemas["ProfileUpdate"]["properties"]
