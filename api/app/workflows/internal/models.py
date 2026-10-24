"""Models for the Processes (PROC) module — Process Management.

specs/009-process-management (HU-PR01–04). The four tables live in
db/sql/71-proc-ddl.sql; this module only maps them.

- ``processes``: the inventory, keyed by an immutable ``code``. A process is
  created in DRAFT and its status then follows workflows/internal/status_service.py.
  ``parent`` nests processes; the hierarchy must stay acyclic.
- ``related_processes``: process → process links typed with the dedicated,
  BPMN-oriented PROCESS_RELATION_TYPE list (workflows/internal/relation_rules.py).
- ``process_assets`` / ``process_inits``: process → asset / initiative links
  typed with the shared RELATION_TYPE list; one link per (pair, type).

Links are never deleted: removing one sets ``is_active = False`` and adding the
identical link again reactivates that row.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import JSON
from sqlmodel import Column, Field, SQLModel


# ── Tables ───────────────────────────────────────────────────────────────────


class Process(SQLModel, table=True):
    __tablename__ = "processes"
    code: str = Field(primary_key=True, max_length=50)
    name: str = Field(max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    type: str = Field(max_length=100)
    parent: Optional[str] = Field(default=None, max_length=50)
    unit: Optional[str] = Field(default=None, max_length=50)
    owner: int
    reference: Optional[str] = None
    status: str = Field(max_length=100)
    tags: Optional[Any] = Field(default=None, sa_column=Column("tags", JSON))
    detail: Optional[str] = None
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


class RelatedProcess(SQLModel, table=True):
    __tablename__ = "related_processes"
    source: str = Field(primary_key=True, max_length=50)
    target: str = Field(primary_key=True, max_length=50)
    type: str = Field(primary_key=True, max_length=100)
    rationale: Optional[str] = None
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


class ProcessAsset(SQLModel, table=True):
    __tablename__ = "process_assets"
    process: str = Field(primary_key=True, max_length=50)
    asset: int = Field(primary_key=True)
    type: str = Field(primary_key=True, max_length=100)
    rationale: Optional[str] = None
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


class ProcessInit(SQLModel, table=True):
    __tablename__ = "process_inits"
    process: str = Field(primary_key=True, max_length=50)
    init: int = Field(primary_key=True)
    type: str = Field(primary_key=True, max_length=100)
    rationale: Optional[str] = None
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


# ── Link items (request bodies) ──────────────────────────────────────────────
# Lengths and list values are checked by the services so a bad value answers
# 400 with a message, not a bare pydantic 422.


class RelationItem(SQLModel):
    target: str = Field(description="The other process's code")
    type: str = Field(description="PROCESS_RELATION_TYPE value")
    rationale: Optional[str] = None


class AssetLinkItem(SQLModel):
    asset: int
    type: str = Field(description="RELATION_TYPE value")
    rationale: Optional[str] = None


class InitLinkItem(SQLModel):
    init: int
    type: str = Field(description="RELATION_TYPE value")
    rationale: Optional[str] = None


class RelationsReplace(SQLModel):
    relations: List[RelationItem] = []


class AssetsReplace(SQLModel):
    assets: List[AssetLinkItem] = []


class InitsReplace(SQLModel):
    inits: List[InitLinkItem] = []


# ── Process requests ─────────────────────────────────────────────────────────


class ProcessCreate(SQLModel):
    code: str = Field(description="Unique, immutable code (A–Z, 0–9, '_' or '-')")
    name: str
    description: Optional[str] = None
    type: str = Field(description="PROCESS_TYPE value")
    parent: Optional[str] = None
    unit: Optional[str] = None
    owner: Optional[int] = Field(default=None, description="Defaults to the caller")
    reference: Optional[str] = None
    status: Optional[str] = Field(
        default=None, description="Ignored unless DRAFT — a new process always starts in DRAFT")
    tags: Optional[List[str]] = None
    detail: Optional[str] = None
    relations: Optional[List[RelationItem]] = None
    assets: Optional[List[AssetLinkItem]] = None
    inits: Optional[List[InitLinkItem]] = None


class ProcessUpdate(SQLModel):
    """Core fields only, all optional. There is deliberately no ``code``."""
    name: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    parent: Optional[str] = None
    unit: Optional[str] = None
    owner: Optional[int] = None
    reference: Optional[str] = None
    status: Optional[str] = None
    tags: Optional[List[str]] = None
    detail: Optional[str] = None


# ── Responses ────────────────────────────────────────────────────────────────


class ProcessRead(SQLModel):
    code: str
    name: str
    description: Optional[str] = None
    type: str
    parent: Optional[str] = None
    parent_name: Optional[str] = None
    unit: Optional[str] = None
    unit_name: Optional[str] = None
    owner: int
    owner_name: Optional[str] = None
    reference: Optional[str] = None
    status: str
    tags: Optional[Any] = None
    detail: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class ProcessDetail(ProcessRead):
    allowed_statuses: List[str] = []


class ProcessRelationRead(SQLModel):
    source: str
    target: str = Field(description="The other process (the source, for an incoming row)")
    target_name: Optional[str] = None
    target_type: Optional[str] = None
    target_active: bool = True
    type: str
    rationale: Optional[str] = None
    direction: str = Field(description="outgoing | incoming (INTERACTS_WITH only)")


class ProcessAssetRead(SQLModel):
    asset: int
    asset_name: Optional[str] = None
    category: Optional[str] = None
    asset_active: bool = True
    type: str
    rationale: Optional[str] = None


class ProcessInitRead(SQLModel):
    init: int
    init_name: Optional[str] = None
    init_active: bool = True
    type: str
    rationale: Optional[str] = None


class ProcessOption(SQLModel):
    code: str
    name: str
    type: str


class UnitOption(SQLModel):
    code: str
    name: str


class OwnerOption(SQLModel):
    id: int
    name: str


class AssetOption(SQLModel):
    id: int
    name: str
    category: Optional[str] = None


class InitOption(SQLModel):
    id: int
    name: str


class ProcessFormOptions(SQLModel):
    can_edit: bool
    processes: List[ProcessOption] = []
    units: List[UnitOption] = []
    owners: List[OwnerOption] = []
    assets: List[AssetOption] = []
    initiatives: List[InitOption] = []
    relation_rules: Dict[str, Dict[str, Any]] = {}
