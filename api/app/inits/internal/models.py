"""Models for Initiatives module"""
from sqlmodel import Field, SQLModel, Column, String, ForeignKey
from sqlalchemy import JSON
from typing import Optional, Any
from datetime import datetime

# Initiative Models
#
# Read-only for now: no InitiativeCreate/InitiativeUpdate, no write routes.
# This module is still a stub overall (per db/CLAUDE.md) — the only thing
# needed today is listing/selecting existing initiatives so an asset can be
# related to one (see asset_inits in api/app/lib/internal/models.py). Full
# initiative management (create/edit/propose/score) is future scope for this
# domain and should go through a SpecKit spec first, per AGENTS.md.


class InitiativeBase(SQLModel):
    name: str = Field(max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    expected_impact: str = Field(max_length=100)
    priority_level: str = Field(max_length=100)
    reference: Optional[str] = Field(default=None)
    status: str = Field(max_length=100)
    type: Optional[str] = Field(default=None, max_length=100)
    tags: Optional[Any] = Field(default=None, sa_column=Column("tags", JSON))
    detail: Optional[str] = Field(default=None)
    score: Optional[int] = Field(default=None)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


class Initiative(InitiativeBase, table=True):
    __tablename__ = "initiatives"
    id: Optional[int] = Field(default=None, primary_key=True)


# Criterias Models

class CriteriaBase(SQLModel):
    code: str = Field(max_length=50, primary_key=True)
    name: str = Field(max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    list: Optional[str] = Field(default=None, foreign_key="criterias.code")
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


class Criteria(CriteriaBase, table=True):
    __tablename__ = "criterias"


class CriteriaCreate(SQLModel):
    code: str = Field(max_length=50, description="Unique criteria code")
    name: str = Field(max_length=100, description="Criteria name")
    description: Optional[str] = Field(
        default=None, max_length=500, description="Criteria description")
    list: Optional[str] = Field(
        default=None, max_length=50, description="List criteria code")
    is_active: Optional[bool] = Field(
        default=True, description="Indicates if the criteria is active")


class CriteriaUpdate(SQLModel):
    name: Optional[str] = Field(
        default=None, max_length=100, description="Criteria name")
    description: Optional[str] = Field(
        default=None, max_length=500, description="Criteria description")
    list: Optional[str] = Field(
        default=None, max_length=50, description="List criteria code")
    is_active: Optional[bool] = Field(
        default=None, description="Indicates if the criteria is active")
