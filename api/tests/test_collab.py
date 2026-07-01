"""Collab contract tests — covers Constitution Principle II (contract stability).

Guards that every column in db/sql/31-collab-ddl.sql is exposed by the SQLModel
schemas. The focus is `projects.detail`, which was missing from the API/UI and
silently unusable; the rest are regression guards so future edits can't drop a
field without a test going red.
"""

from app.collab.internal.models import (
    Team, TeamCreate, TeamUpdate,
    Role, RoleCreate, RoleUpdate,
    Assignment, AssignmentCreate, AssignmentUpdate,
    Project, ProjectCreate, ProjectUpdate,
    Dimension, DimensionCreate, DimensionUpdate,
    Metric, MetricCreate, MetricUpdate, MetricByDimension,
)


def test_metric_by_dimension_exposes_edit_fields():
    """The dashboard grid edits metrics in place, so its projection must carry
    the metric `id` (to PUT /api/metrics/{id}) and an ISO `measured_at` (to
    prefill the datetime picker without losing the time component)."""
    expected = (
        "id", "name", "email", "role", "team",
        "metric", "date", "measured_at", "observation",
    )
    missing = [f for f in expected if f not in MetricByDimension.model_fields]
    assert not missing, f"MetricByDimension missing fields: {missing}"


def test_project_models_expose_detail_field():
    """`detail` (TEXT) must be on the table model and both write schemas."""
    assert "detail" in Project.model_fields
    assert "detail" in ProjectCreate.model_fields
    assert "detail" in ProjectUpdate.model_fields


def test_project_create_round_trips_detail():
    """A ProjectCreate carrying `detail` must persist it into the Project row."""
    payload = ProjectCreate(code="P1", name="Proj", status="PLANNED", detail="rich text")
    row = Project.model_validate(payload)
    assert row.detail == "rich text"


def test_project_detail_optional():
    """`detail` stays optional so existing callers don't break."""
    assert ProjectCreate(code="P1", name="Proj", status="PLANNED").detail is None
    assert ProjectUpdate().detail is None


def test_collab_models_match_ddl_fields():
    """Every DDL column must be present on each table model (regression guard)."""
    expected = {
        Team: ("code", "name", "description", "lead", "chat_channel_url",
               "kanban_board_url", "is_active", "created_at", "updated_at"),
        Role: ("code", "name", "description", "icon", "is_active",
               "created_at", "updated_at"),
        Assignment: ("id", "team", "user_id", "role", "observation", "valid_from",
                     "valid_to", "is_active", "created_at", "updated_at"),
        Project: ("code", "name", "description", "team", "repo_url", "status",
                  "start_date", "end_date", "detail", "is_active",
                  "created_at", "updated_at"),
        Dimension: ("code", "name", "description", "scale", "unit", "is_active",
                    "created_at", "updated_at"),
        Metric: ("id", "dimension", "assignment", "value", "observation",
                 "measured_at", "is_active", "created_at", "updated_at"),
    }
    for model, fields in expected.items():
        missing = [f for f in fields if f not in model.model_fields]
        assert not missing, f"{model.__name__} missing DDL fields: {missing}"


def _max_len(model, field):
    """Return the declared max_length of a model field, or None if unbounded."""
    from annotated_types import MaxLen

    for meta in model.model_fields[field].metadata:
        if isinstance(meta, MaxLen):
            return meta.max_length
    return None


def test_text_columns_are_unbounded():
    """DDL TEXT columns must not be length-capped on the API models."""
    assert _max_len(Role, "icon") is None              # roles.icon TEXT
    assert _max_len(Team, "chat_channel_url") is None  # teams.chat_channel_url TEXT
    assert _max_len(Team, "kanban_board_url") is None  # teams.kanban_board_url TEXT
    assert _max_len(Assignment, "observation") is None  # assignments.observation TEXT
    assert _max_len(Project, "repo_url") is None        # projects.repo_url TEXT
    assert _max_len(Project, "detail") is None          # projects.detail TEXT
    assert _max_len(Metric, "value") is None            # metrics.value TEXT
    assert _max_len(Metric, "observation") is None      # metrics.observation TEXT


def test_varchar_columns_match_ddl_lengths():
    """DDL VARCHAR(n) columns must keep their length on the API models."""
    assert _max_len(Role, "description") == 500   # roles.description VARCHAR(500)
    assert _max_len(Team, "description") == 500    # teams.description VARCHAR(500)
    assert _max_len(Project, "status") == 100      # projects.status VARCHAR(100)
    assert _max_len(DimensionCreate, "scale") == 100  # dimensions.scale VARCHAR(100)


def test_openapi_project_schema_includes_detail():
    """The published OpenAPI contract must advertise `detail` on Project schemas."""
    from app.main import app

    schemas = app.openapi()["components"]["schemas"]
    assert "detail" in schemas["Project"]["properties"]
    assert "detail" in schemas["ProjectCreate"]["properties"]
    assert "detail" in schemas["ProjectUpdate"]["properties"]
