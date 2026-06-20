"""Category contract tests — covers Constitution Principle II (contract stability).

Locks in that the `icon` column from db/sql/21-taxo-ddl.sql is exposed by the
Category models end-to-end (read + create + update) so the field stops being
silently dropped between the UI and the DB.
"""

from app.taxo.internal.models import (
    Category,
    CategoryCreate,
    CategoryUpdate,
    Feature,
    FeatureCreate,
    FeatureUpdate,
)


def test_category_models_expose_icon_field():
    """`icon` must be a declared field on the table model and both write schemas."""
    assert "icon" in Category.model_fields
    assert "icon" in CategoryCreate.model_fields
    assert "icon" in CategoryUpdate.model_fields


def test_category_create_round_trips_icon():
    """A CategoryCreate carrying `icon` must persist it into the Category row."""
    payload = CategoryCreate(code="AI", name="AI Assets", icon="heroicon-cpu")
    row = Category.model_validate(payload)
    assert row.icon == "heroicon-cpu"


def test_category_icon_optional():
    """`icon` stays optional (defaults to None) so existing callers don't break."""
    assert CategoryCreate(code="AI", name="AI Assets").icon is None
    assert CategoryUpdate().icon is None


def test_openapi_category_schema_includes_icon():
    """The published OpenAPI contract must advertise `icon` on Category schemas.

    Built straight from ``app.openapi()`` (no DB) so it stays green despite the
    pre-existing SQLite ``create_all`` breakage that errors the client fixture.
    """
    from app.main import app

    schemas = app.openapi()["components"]["schemas"]
    assert "icon" in schemas["Category"]["properties"]
    assert "icon" in schemas["CategoryCreate"]["properties"]
    assert "icon" in schemas["CategoryUpdate"]["properties"]


def test_feature_models_expose_list_field():
    """`list` must be a declared field on the table model and both write schemas."""
    assert "list" in Feature.model_fields
    assert "list" in FeatureCreate.model_fields
    assert "list" in FeatureUpdate.model_fields


def test_feature_create_round_trips_list():
    """A FeatureCreate carrying `list` must persist it into the Feature row."""
    payload = FeatureCreate(code="LANGUAGE", name="Language", type="SINGLE", list="LANGUAGES")
    row = Feature.model_validate(payload)
    assert row.list == "LANGUAGES"


def test_feature_list_optional():
    """`list` stays optional (defaults to None) so existing callers don't break."""
    assert FeatureCreate(code="LANGUAGE", name="Language", type="SINGLE").list is None
    assert FeatureUpdate().list is None


def test_openapi_feature_schema_includes_list():
    """The published OpenAPI contract must advertise `list` on Feature schemas."""
    from app.main import app

    schemas = app.openapi()["components"]["schemas"]
    assert "list" in schemas["Feature"]["properties"]
    assert "list" in schemas["FeatureCreate"]["properties"]
    assert "list" in schemas["FeatureUpdate"]["properties"]
