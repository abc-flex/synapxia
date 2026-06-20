"""Lib (asset library) contract tests — Constitution Principle II.

Focus: the `actions` model was desynced from db/sql/41-lib-ddl.sql — it typed
`asset` as a string FK to a non-existent `assets.code`, mapped a `details` JSON
column and a `measured_at` column that the table does not have, and was missing
the real `detail` TEXT column. Those phantom columns made `GET /api/actions/`
select non-existent columns. These guards lock the model to the DDL.
"""

from app.lib.internal.models import (
    Asset, AssetCreate, AssetUpdate,
    Characterization, CharacterizationCreate, CharacterizationUpdate,
    Favorite,
    Action, ActionCreate, ActionUpdate,
    AssetRelation,
    AssetPermission,
)


def test_action_has_detail_not_details_or_measured_at():
    """Action must expose `detail` (TEXT) and NOT the phantom columns."""
    assert "detail" in Action.model_fields
    assert "detail" in ActionCreate.model_fields
    assert "detail" in ActionUpdate.model_fields
    assert "details" not in Action.model_fields
    assert "measured_at" not in Action.model_fields


def test_action_asset_is_int_id():
    """`asset` must be an int FK to assets.id (assets has no `code` column)."""
    assert Action.model_fields["asset"].annotation is int
    assert ActionCreate.model_fields["asset"].annotation is int


def test_action_text_columns_unbounded():
    """DDL TEXT columns (content, reference, detail) must not be length-capped."""
    from annotated_types import MaxLen

    def max_len(model, field):
        for meta in model.model_fields[field].metadata:
            if isinstance(meta, MaxLen):
                return meta.max_length
        return None

    for field in ("content", "reference", "detail"):
        assert max_len(Action, field) is None


def test_lib_models_match_ddl_fields():
    """Every DDL column must be present on each table model (regression guard)."""
    expected = {
        Asset: ("id", "name", "description", "category", "reference", "status",
                "tags", "detail", "is_active", "created_at", "updated_at"),
        Characterization: ("asset", "feature", "value", "detail", "is_active",
                           "created_at", "updated_at"),
        Favorite: ("user_id", "asset", "is_active", "created_at", "updated_at"),
        Action: ("id", "asset", "user_id", "type", "content", "reference",
                 "parent", "detail", "is_active", "created_at", "updated_at"),
        AssetRelation: ("source", "target", "type", "rationale", "is_active",
                        "created_at", "updated_at"),
        AssetPermission: ("id", "asset", "target_type", "target_code",
                          "access_level", "valid_from", "valid_to", "is_active"),
    }
    for model, fields in expected.items():
        missing = [f for f in fields if f not in model.model_fields]
        assert not missing, f"{model.__name__} missing DDL fields: {missing}"


def test_openapi_action_schema_uses_detail():
    """OpenAPI contract must advertise `detail` and not `details`/`measured_at`."""
    from app.main import app

    schemas = app.openapi()["components"]["schemas"]
    for name in ("Action", "ActionCreate", "ActionUpdate"):
        props = schemas[name]["properties"]
        assert "detail" in props
        assert "details" not in props
        assert "measured_at" not in props
