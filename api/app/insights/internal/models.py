"""Models for the Analytics (ANA) module — Dashboard Management.

specs/006-dashboard-management (HU-AN01 / HU-AN02 / HU-AN03). The three tables
already exist in db/sql/61-ana-ddl.sql; this module only maps them.

- ``dashboards``: the governed inventory. A dashboard is created in DRAFT and
  its status then follows insights/internal/status_service.py.
- ``parameters``: the inputs a dashboard accepts, keyed by (dashboard, name).
  The *value source* is derived, never stored: GRANT when ``context_binding``
  is set, else LIST when ``list`` is set, else INPUT (the viewer types it).
- ``dashboard_permissions``: per-dashboard grants, bound to the shared engine
  in app/internal/resource_permissions.py. Revoked by closing ``valid_to`` —
  never deleted, so there is deliberately no ``is_active``.
"""
from datetime import datetime
from typing import Any, List, Optional

from sqlalchemy import JSON, BigInteger
from sqlmodel import Column, Field, ForeignKey, SQLModel, String


# ── Dashboards ───────────────────────────────────────────────────────────────


class DashboardBase(SQLModel):
    name: str = Field(max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    type: str = Field(max_length=100)
    sources_types: str = Field(max_length=100)
    source_url: Optional[str] = Field(default=None)
    status: str = Field(max_length=100)
    tags: Optional[Any] = Field(default=None, sa_column=Column("tags", JSON))
    detail: Optional[str] = Field(default=None)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


class Dashboard(DashboardBase, table=True):
    __tablename__ = "dashboards"
    id: Optional[int] = Field(default=None, primary_key=True)


class DashboardCreate(SQLModel):
    name: str = Field(max_length=100, description="Dashboard name")
    description: Optional[str] = Field(default=None, max_length=500)
    type: str = Field(max_length=100, description="DASHBOARD_TYPE value")
    sources_types: str = Field(max_length=100, description="SOURCE_TYPE value")
    source_url: str = Field(
        description="Platform path for INTERNAL_PAGE, absolute https URL otherwise")
    status: Optional[str] = Field(
        default=None, max_length=100,
        description="Ignored unless DRAFT — a new dashboard always starts in DRAFT")
    tags: Optional[List[str]] = None
    detail: Optional[str] = None


class DashboardUpdate(SQLModel):
    name: Optional[str] = Field(default=None, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    type: Optional[str] = Field(default=None, max_length=100)
    sources_types: Optional[str] = Field(default=None, max_length=100)
    source_url: Optional[str] = None
    status: Optional[str] = Field(default=None, max_length=100)
    tags: Optional[List[str]] = None
    detail: Optional[str] = None


class DashboardWithAccess(DashboardBase):
    """Dashboard read projection for Dashboard Management: the caller's own
    effective access, the statuses the status control may offer (the current
    one plus its allowed moves) and the scope types through which a live grant
    reaches the caller (drives the list's privileges filter)."""
    id: int
    my_access: str
    is_favorite: bool = False
    allowed_statuses: List[str] = Field(default_factory=list)
    permission_scopes: List[str] = Field(default_factory=list)


class ListOption(SQLModel):
    value: str
    label: str


# ── Favorites ────────────────────────────────────────────────────────────────
# A user's personal mark on a dashboard (the counterpart of lib's `favorites`
# and inits' `favorite_inits`). Logical removal; marking again restores the row.


class FavoriteDashboard(SQLModel, table=True):
    __tablename__ = "favorite_dashboards"
    user_id: int = Field(sa_column=Column(
        "user_id", BigInteger, ForeignKey("users.id"), primary_key=True))
    dashboard: int = Field(sa_column=Column(
        "dashboard", BigInteger, ForeignKey("dashboards.id"), primary_key=True))
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


class DashboardFavoriteState(SQLModel):
    dashboard: int
    is_favorite: bool


# ── Grants ───────────────────────────────────────────────────────────────────


class DashboardPermission(SQLModel, table=True):
    __tablename__ = "dashboard_permissions"
    id: Optional[int] = Field(default=None, primary_key=True)
    dashboard: int = Field(sa_column=Column(
        "dashboard", BigInteger, ForeignKey("dashboards.id"), nullable=False))
    target_type: str = Field(max_length=100)
    target_code: str = Field(max_length=50)
    access_level: str = Field(max_length=100)
    valid_from: datetime = Field(default_factory=datetime.utcnow)
    valid_to: Optional[datetime] = None


class DashboardPermissionCreate(SQLModel):
    dashboard: int = Field(description="Dashboard id (FK to dashboards.id)")
    target_type: str = Field(
        max_length=100, description="Target type (TARGET_TYPE list value)")
    target_code: str = Field(
        default="ALL", max_length=50, description="Target id/code; 'ALL' for PUBLIC")
    access_level: str = Field(
        max_length=100, description="Access level (ACCESS_LEVEL list value)")
    valid_from: Optional[datetime] = Field(
        default=None, description="Optional start timestamp (default: now)")
    valid_to: Optional[datetime] = Field(
        default=None, description="Optional expiry timestamp")


class DashboardPermissionUpdate(SQLModel):
    access_level: Optional[str] = Field(default=None, max_length=100)
    valid_from: Optional[datetime] = Field(default=None)
    valid_to: Optional[datetime] = Field(
        default=None, description="Expiry timestamp; DELETE revokes immediately")


class RevokedDashboardPermission(SQLModel):
    """A revoked grant plus the active parameters still bound to it — the
    binding is kept, it simply stops applying (spec US4-7)."""
    id: int
    dashboard: int
    target_type: str
    target_code: str
    access_level: str
    valid_from: datetime
    valid_to: Optional[datetime] = None
    bound_parameters: List[str] = Field(default_factory=list)


# ── Parameters ───────────────────────────────────────────────────────────────


class Parameter(SQLModel, table=True):
    __tablename__ = "parameters"
    dashboard: int = Field(sa_column=Column(
        "dashboard", BigInteger, ForeignKey("dashboards.id"), primary_key=True))
    name: str = Field(sa_column=Column("name", String(100), primary_key=True))
    label: str = Field(max_length=100)
    data_type: str = Field(max_length=100)
    default_value: Optional[str] = Field(default=None)
    is_required: bool = Field(default=False)
    list: Optional[str] = Field(default=None, sa_column=Column(
        "list", String(50), ForeignKey("lists.code"), nullable=True))
    context_binding: Optional[int] = Field(default=None, sa_column=Column(
        "context_binding", BigInteger, ForeignKey("dashboard_permissions.id"),
        nullable=True))
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


class ParameterCreate(SQLModel):
    # Lengths are checked by parameter_validation (→ 400), not by the model (→ 422).
    name: str = Field(description="Machine key, ^[a-z][a-z0-9_]*$, at most 100")
    label: str = Field(description="At most 100 characters")
    data_type: str = Field(description="PARAM_TYPE value")
    default_value: Optional[str] = None
    is_required: bool = False
    list: Optional[str] = Field(
        default=None, max_length=50, description="Allowed-values list (lists.code)")
    context_binding: Optional[int] = Field(
        default=None, description="Id of one of this dashboard's non-PUBLIC live grants")


class ParameterUpdate(SQLModel):
    """`name` is part of the primary key and cannot be renamed."""
    label: Optional[str] = None
    data_type: Optional[str] = None
    default_value: Optional[str] = None
    is_required: Optional[bool] = None
    list: Optional[str] = Field(default=None, max_length=50)
    context_binding: Optional[int] = None


class ParameterRead(SQLModel):
    dashboard: int
    name: str
    label: str
    data_type: str
    default_value: Optional[str] = None
    is_required: bool = False
    list: Optional[str] = None
    context_binding: Optional[int] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    # Derived: GRANT / LIST / INPUT (see module docstring).
    value_source: str
    # "<TARGET_TYPE> <target_code>" of the bound grant, when there is one.
    binding_label: Optional[str] = None
