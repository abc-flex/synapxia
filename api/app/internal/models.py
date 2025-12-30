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
    code: str = Field(max_length=50, description="Código único del rol")
    name: str = Field(max_length=100, description="Nombre del rol")
    description: Optional[str] = Field(default=None, max_length=255, description="Descripción del rol")
    is_active: Optional[bool] = Field(default=True, description="Indica si el rol está activo")

class RoleUpdate(SQLModel):
    name: Optional[str] = Field(default=None, max_length=100, description="Nombre del rol")
    description: Optional[str] = Field(default=None, max_length=255, description="Descripción del rol")
    is_active: Optional[bool] = Field(default=None, description="Indica si el rol está activo")

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

class ModuleCreate(SQLModel):
    code: str = Field(max_length=50, description="Código único del módulo")
    name: str = Field(max_length=100, description="Nombre del módulo")
    description: Optional[str] = Field(default=None, max_length=255, description="Descripción del módulo")
    sort_order: Optional[int] = Field(default=0, description="Orden de visualización")
    is_active: Optional[bool] = Field(default=True, description="Indica si el módulo está activo")

class ModuleUpdate(SQLModel):
    name: Optional[str] = Field(default=None, max_length=100, description="Nombre del módulo")
    description: Optional[str] = Field(default=None, max_length=255, description="Descripción del módulo")
    sort_order: Optional[int] = Field(default=None, description="Orden de visualización")
    is_active: Optional[bool] = Field(default=None, description="Indica si el módulo está activo")

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

class ListCreate(SQLModel):
    code: str = Field(max_length=50, description="Código único de la lista")
    name: str = Field(max_length=100, description="Nombre de la lista")
    description: Optional[str] = Field(default=None, max_length=255, description="Descripción de la lista")
    type: str = Field(max_length=100, description="Tipo de lista")
    module: Optional[str] = Field(default=None, max_length=50, description="Código del módulo asociado")
    is_active: Optional[bool] = Field(default=True, description="Indica si la lista está activa")

class ListUpdate(SQLModel):
    name: Optional[str] = Field(default=None, max_length=100, description="Nombre de la lista")
    description: Optional[str] = Field(default=None, max_length=255, description="Descripción de la lista")
    type: Optional[str] = Field(default=None, max_length=100, description="Tipo de lista")
    module: Optional[str] = Field(default=None, max_length=50, description="Código del módulo asociado")
    is_active: Optional[bool] = Field(default=None, description="Indica si la lista está activa")

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

class ListItemCreate(SQLModel):
    list: str = Field(max_length=50, description="Código de la lista")
    value: str = Field(max_length=100, description="Valor del elemento")
    label: str = Field(max_length=150, description="Etiqueta del elemento")
    sort_order: Optional[int] = Field(default=0, description="Orden de visualización")
    is_active: Optional[bool] = Field(default=True, description="Indica si el elemento está activo")

class ListItemUpdate(SQLModel):
    label: Optional[str] = Field(default=None, max_length=150, description="Etiqueta del elemento")
    sort_order: Optional[int] = Field(default=None, description="Orden de visualización")
    is_active: Optional[bool] = Field(default=None, description="Indica si el elemento está activo")