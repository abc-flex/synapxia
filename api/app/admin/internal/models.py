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

# Units Models
class UnitBase(SQLModel):
    code: str = Field(max_length=50, primary_key=True)
    name: str = Field(max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    unit_type: Optional[str] = Field(default=None, max_length=50, sa_column_kwargs={"name": "unit_type"})
    parent_unit: Optional[str] = Field(default=None, max_length=50, foreign_key="units.code", sa_column_kwargs={"name": "parent_unit"})
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

class Unit(UnitBase, table=True):
    __tablename__ = "units"

class UnitCreate(SQLModel):
    code: str = Field(max_length=50, description="Código único de la unidad")
    name: str = Field(max_length=100, description="Nombre de la unidad")
    description: Optional[str] = Field(default=None, max_length=500, description="Descripción de la unidad")
    unit_type: Optional[str] = Field(default=None, max_length=50, description="Tipo de unidad")
    parent_unit: Optional[str] = Field(default=None, max_length=50, description="Código de la unidad padre")
    is_active: Optional[bool] = Field(default=True, description="Indica si la unidad está activa")

class UnitUpdate(SQLModel):
    name: Optional[str] = Field(default=None, max_length=100, description="Nombre de la unidad")
    description: Optional[str] = Field(default=None, max_length=500, description="Descripción de la unidad")
    unit_type: Optional[str] = Field(default=None, max_length=50, description="Tipo de unidad")
    parent_unit: Optional[str] = Field(default=None, max_length=50, description="Código de la unidad padre")
    is_active: Optional[bool] = Field(default=None, description="Indica si la unidad está activa")

# Users Models
class UserBase(SQLModel):
    username: str = Field(max_length=50, unique=True)
    email: str = Field(max_length=100, unique=True)
    password_hash: str = Field(max_length=500)
    first_name: str = Field(max_length=100)
    last_name: str = Field(max_length=100)
    menu_role: str = Field(max_length=50, foreign_key="roles.code")
    unit: str = Field(max_length=50, foreign_key="units.code")
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None

class User(UserBase, table=True):
    __tablename__ = "users"
    id: Optional[int] = Field(default=None, primary_key=True)

class UserCreate(SQLModel):
    username: str = Field(max_length=50, description="Nombre de usuario único")
    email: str = Field(max_length=100, description="Correo electrónico único")
    password_hash: str = Field(max_length=500, description="Hash de la contraseña")
    first_name: str = Field(max_length=100, description="Nombre")
    last_name: str = Field(max_length=100, description="Apellido")
    menu_role: str = Field(max_length=50, description="Código del rol")
    unit: str = Field(max_length=50, description="Código de la unidad")
    is_active: Optional[bool] = Field(default=True, description="Indica si el usuario está activo")

class UserUpdate(SQLModel):
    email: Optional[str] = Field(default=None, max_length=100, description="Correo electrónico")
    password_hash: Optional[str] = Field(default=None, max_length=500, description="Hash de la contraseña")
    first_name: Optional[str] = Field(default=None, max_length=100, description="Nombre")
    last_name: Optional[str] = Field(default=None, max_length=100, description="Apellido")
    menu_role: Optional[str] = Field(default=None, max_length=50, description="Código del rol")
    unit: Optional[str] = Field(default=None, max_length=50, description="Código de la unidad")
    is_active: Optional[bool] = Field(default=None, description="Indica si el usuario está activo")
    last_login_at: Optional[datetime] = Field(default=None, description="Última fecha de inicio de sesión")

# Options Models
class OptionBase(SQLModel):
    module: str = Field(sa_column=Column('module', String, ForeignKey('modules.code'), primary_key=True))
    code: str = Field(sa_column=Column('code', String(50), primary_key=True))
    name: str = Field(max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    path: Optional[str] = Field(default=None, max_length=500)
    icon: Optional[str] = Field(default=None, max_length=500)
    type: str = Field(max_length=100)
    sort_order: int = Field(default=0)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

class Option(OptionBase, table=True):
    __tablename__ = "options"

class OptionCreate(SQLModel):
    module: str = Field(max_length=50, description="Código del módulo")
    code: str = Field(max_length=50, description="Código único de la opción")
    name: str = Field(max_length=100, description="Nombre de la opción")
    description: Optional[str] = Field(default=None, max_length=500, description="Descripción de la opción")
    path: Optional[str] = Field(default=None, max_length=500, description="Ruta de la opción")
    icon: Optional[str] = Field(default=None, max_length=500, description="Icono de la opción")
    type: str = Field(max_length=100, description="Tipo de opción")
    sort_order: Optional[int] = Field(default=0, description="Orden de visualización")
    is_active: Optional[bool] = Field(default=True, description="Indica si la opción está activa")

class OptionUpdate(SQLModel):
    name: Optional[str] = Field(default=None, max_length=100, description="Nombre de la opción")
    description: Optional[str] = Field(default=None, max_length=500, description="Descripción de la opción")
    path: Optional[str] = Field(default=None, max_length=500, description="Ruta de la opción")
    icon: Optional[str] = Field(default=None, max_length=500, description="Icono de la opción")
    type: Optional[str] = Field(default=None, max_length=100, description="Tipo de opción")
    sort_order: Optional[int] = Field(default=None, description="Orden de visualización")
    is_active: Optional[bool] = Field(default=None, description="Indica si la opción está activa")

# Privileges Models
class PrivilegeBase(SQLModel):
    role: str = Field(sa_column=Column('role', String, ForeignKey('roles.code'), primary_key=True))
    module: str = Field(sa_column=Column('module', String(50), primary_key=True))
    option: str = Field(sa_column=Column('option', String(50), primary_key=True))
    can_edit: bool = Field(default=True)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

class Privilege(PrivilegeBase, table=True):
    __tablename__ = "privileges"

class PrivilegeCreate(SQLModel):
    role: str = Field(max_length=50, description="Código del rol")
    module: str = Field(max_length=50, description="Código del módulo")
    option: str = Field(max_length=50, description="Código de la opción")
    can_edit: Optional[bool] = Field(default=True, description="Indica si puede editar")
    is_active: Optional[bool] = Field(default=True, description="Indica si el privilegio está activo")

class PrivilegeUpdate(SQLModel):
    can_edit: Optional[bool] = Field(default=None, description="Indica si puede editar")
    is_active: Optional[bool] = Field(default=None, description="Indica si el privilegio está activo")

