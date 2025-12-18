from sqlmodel import Field, SQLModel, Relationship, Column, String, ForeignKey
from typing import Optional, List
from datetime import datetime

class RoleBase(SQLModel):
    code: str = Field(max_length=50, primary_key=True)
    name: str = Field(max_length=100)
    description: Optional[str] = Field(default=None, max_length=255)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

class Role(RoleBase, table=True):
    __tablename__ = "roles"

class RoleCreate(SQLModel):
    code: str
    name: str
    description: Optional[str] = None

class RoleUpdate(SQLModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

class ModuleBase(SQLModel):
    code: str = Field(max_length=50, primary_key=True)
    name: str = Field(max_length=100)
    description: Optional[str] = Field(default=None, max_length=255)
    sort_order: int = Field(default=0)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

class Module(ModuleBase, table=True):
    __tablename__ = "modules"
    lists: List["List"] = Relationship(back_populates="module", sa_relationship_kwargs={"primaryjoin": "Module.code==List.module"})

class ListBase(SQLModel):
    code: str = Field(max_length=50, primary_key=True)
    name: str = Field(max_length=100)
    description: Optional[str] = Field(default=None, max_length=255)
    type: str = Field(max_length=100)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    module: Optional[str] = Field(default=None, foreign_key="modules.code")

class List(ListBase, table=True):
    __tablename__ = "lists"
    module: Optional[Module] = Relationship(back_populates="lists", sa_relationship_kwargs={"primaryjoin": "List.module==Module.code"})
    items: List["ListItem"] = Relationship(back_populates="list", sa_relationship_kwargs={"primaryjoin": "List.code==ListItem.list"})

class ListItemBase(SQLModel):
    list: str = Field(sa_column=Column('list', String, ForeignKey('lists.code'), primary_key=True))
    value: str = Field(sa_column=Column('value', String(100), primary_key=True))
    label: str = Field(max_length=150)
    sort_order: int = Field(default=0)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

class ListItem(ListItemBase, table=True):
    __tablename__ = "list_items"
    list: Optional[List] = Relationship(back_populates="items", sa_relationship_kwargs={"primaryjoin": "ListItem.list==List.code"})