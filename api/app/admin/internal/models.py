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
    code: str = Field(max_length=50, description="Unique role code")
    name: str = Field(max_length=100, description="Role name")
    description: Optional[str] = Field(
        default=None, max_length=255, description="Role description")
    is_active: Optional[bool] = Field(
        default=True, description="Indicates if the role is active")


class RoleUpdate(SQLModel):
    name: Optional[str] = Field(
        default=None, max_length=100, description="Role name")
    description: Optional[str] = Field(
        default=None, max_length=255, description="Role description")
    is_active: Optional[bool] = Field(
        default=None, description="Indicates if the role is active")


class ModuleBase(SQLModel):
    code: str = Field(max_length=50, primary_key=True)
    name: str = Field(max_length=100)
    description: Optional[str] = Field(default=None, max_length=255)
    sort_order: int = Field(default=0)
    icon: Optional[str] = Field(
        default=None, max_length=500, description="Module icon")
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


class Module(ModuleBase, table=True):
    __tablename__ = "modules"


class ModuleCreate(SQLModel):
    code: str = Field(max_length=50, description="Unique module code")
    name: str = Field(max_length=100, description="Module name")
    description: Optional[str] = Field(
        default=None, max_length=255, description="Module description")
    icon: Optional[str] = Field(
        default=None, max_length=500, description="Module icon")
    sort_order: Optional[int] = Field(default=0, description="Display order")
    is_active: Optional[bool] = Field(
        default=True, description="Indicates if the module is active")


class ModuleUpdate(SQLModel):
    name: Optional[str] = Field(
        default=None, max_length=100, description="Module name")
    description: Optional[str] = Field(
        default=None, max_length=255, description="Module description")
    icon: Optional[str] = Field(
        default=None, max_length=500, description="Module icon")
    sort_order: Optional[int] = Field(
        default=None, description="Display order")
    is_active: Optional[bool] = Field(
        default=None, description="Indicates if the module is active")


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
    code: str = Field(max_length=50, description="Unique list code")
    name: str = Field(max_length=100, description="List name")
    description: Optional[str] = Field(
        default=None, max_length=255, description="List description")
    type: str = Field(max_length=100, description="List type")
    module: Optional[str] = Field(
        default=None, max_length=50, description="Associated module code")
    is_active: Optional[bool] = Field(
        default=True, description="Indicates if the list is active")


class ListUpdate(SQLModel):
    name: Optional[str] = Field(
        default=None, max_length=100, description="List name")
    description: Optional[str] = Field(
        default=None, max_length=255, description="List description")
    type: Optional[str] = Field(
        default=None, max_length=100, description="List type")
    module: Optional[str] = Field(
        default=None, max_length=50, description="Associated module code")
    is_active: Optional[bool] = Field(
        default=None, description="Indicates if the list is active")


class ListItemBase(SQLModel):
    list: str = Field(sa_column=Column(
        'list', String, ForeignKey('lists.code'), primary_key=True))
    value: str = Field(sa_column=Column(
        'value', String(100), primary_key=True))
    label: str = Field(max_length=150)
    sort_order: int = Field(default=0)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


class ListItem(ListItemBase, table=True):
    __tablename__ = "list_items"


class ListItemCreate(SQLModel):
    list: str = Field(max_length=50, description="List code")
    value: str = Field(max_length=100, description="Item value")
    label: str = Field(max_length=150, description="Item label")
    sort_order: Optional[int] = Field(default=0, description="Display order")
    is_active: Optional[bool] = Field(
        default=True, description="Indicates if the item is active")


class ListItemUpdate(SQLModel):
    label: Optional[str] = Field(
        default=None, max_length=150, description="Item label")
    sort_order: Optional[int] = Field(
        default=None, description="Display order")
    is_active: Optional[bool] = Field(
        default=None, description="Indicates if the item is active")


# ItemTranslations Models
class ItemTranslationBase(SQLModel):
    list: str = Field(sa_column=Column(
        'list', String, ForeignKey('lists.code'), primary_key=True))
    value: str = Field(sa_column=Column(
        'value', String(100), primary_key=True))
    lang: str = Field(sa_column=Column(
        'lang', String(10), primary_key=True))
    label: str = Field(max_length=200)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


class ItemTranslation(ItemTranslationBase, table=True):
    __tablename__ = "item_translations"


class ItemTranslationCreate(SQLModel):
    list: str = Field(max_length=50, description="List code")
    value: str = Field(max_length=100, description="Item value")
    lang: str = Field(max_length=10, description="Language code")
    label: str = Field(max_length=200, description="Translated label")
    is_active: Optional[bool] = Field(
        default=True, description="Indicates if the translation is active")


class ItemTranslationUpdate(SQLModel):
    label: Optional[str] = Field(
        default=None, max_length=200, description="Translated label")
    is_active: Optional[bool] = Field(
        default=None, description="Indicates if the translation is active")


# BusinessUnits Models


class BusinessUnitBase(SQLModel):
    code: str = Field(max_length=50, primary_key=True)
    name: str = Field(max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    type: Optional[str] = Field(
        default=None, max_length=50, sa_column_kwargs={"name": "type"})
    parent: Optional[str] = Field(
        default=None, max_length=50, foreign_key="business_units.code", sa_column_kwargs={"name": "parent"})
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


class BusinessUnit(BusinessUnitBase, table=True):
    __tablename__ = "business_units"


class BusinessUnitCreate(SQLModel):
    code: str = Field(max_length=50, description="Unique business_unit code")
    name: str = Field(max_length=100, description="Business_Unit name")
    description: Optional[str] = Field(
        default=None, max_length=500, description="Business_Unit description")
    type: Optional[str] = Field(
        default=None, max_length=50, description="Business_Unit type")
    parent: Optional[str] = Field(
        default=None, max_length=50, description="Parent business_unit code")
    is_active: Optional[bool] = Field(
        default=True, description="Indicates if the business_unit is active")


class BusinessUnitUpdate(SQLModel):
    name: Optional[str] = Field(
        default=None, max_length=100, description="Business_Unit name")
    description: Optional[str] = Field(
        default=None, max_length=500, description="Business_Unit description")
    type: Optional[str] = Field(
        default=None, max_length=50, description="Business_Unit type")
    parent: Optional[str] = Field(
        default=None, max_length=50, description="Parent business_unit code")
    is_active: Optional[bool] = Field(
        default=None, description="Indicates if the business_unit is active")

# Users Models


class UserBase(SQLModel):
    username: str = Field(max_length=50, unique=True)
    email: str = Field(max_length=100, unique=True)
    password_hash: str = Field(max_length=500)
    first_name: str = Field(max_length=100)
    last_name: str = Field(max_length=100)
    menu_role: str = Field(max_length=50, foreign_key="roles.code")
    business_unit: str = Field(max_length=50, foreign_key="business_units.code")
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None


class User(UserBase, table=True):
    __tablename__ = "users"
    id: Optional[int] = Field(default=None, primary_key=True)


class UserCreate(SQLModel):
    username: str = Field(max_length=50, description="Unique username")
    email: str = Field(max_length=100, description="Unique email address")
    password_hash: str = Field(max_length=500, description="Password hash")
    first_name: str = Field(max_length=100, description="First name")
    last_name: str = Field(max_length=100, description="Last name")
    menu_role: str = Field(max_length=50, description="Role code")
    business_unit: str = Field(max_length=50, description="Business_Unit code")
    is_active: Optional[bool] = Field(
        default=True, description="Indicates if the user is active")


class UserUpdate(SQLModel):
    email: Optional[str] = Field(
        default=None, max_length=100, description="Email address")
    password_hash: Optional[str] = Field(
        default=None, max_length=500, description="Password hash")
    first_name: Optional[str] = Field(
        default=None, max_length=100, description="First name")
    last_name: Optional[str] = Field(
        default=None, max_length=100, description="Last name")
    menu_role: Optional[str] = Field(
        default=None, max_length=50, description="Role code")
    business_unit: Optional[str] = Field(
        default=None, max_length=50, description="Business_Unit code")
    is_active: Optional[bool] = Field(
        default=None, description="Indicates if the user is active")
    is_superuser: Optional[bool] = Field(
        default=None, description="Indicates if the user is a superuser")
    last_login_at: Optional[datetime] = Field(
        default=None, description="Last login date")

# Options Models


class OptionBase(SQLModel):
    module: str = Field(sa_column=Column(
        'module', String, ForeignKey('modules.code'), primary_key=True))
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
    module: str = Field(max_length=50, description="Module code")
    code: str = Field(max_length=50, description="Unique option code")
    name: str = Field(max_length=100, description="Option name")
    description: Optional[str] = Field(
        default=None, max_length=500, description="Option description")
    path: Optional[str] = Field(
        default=None, max_length=500, description="Option path")
    icon: Optional[str] = Field(
        default=None, max_length=500, description="Option icon")
    type: str = Field(max_length=100, description="Option type")
    sort_order: Optional[int] = Field(default=0, description="Display order")
    is_active: Optional[bool] = Field(
        default=True, description="Indicates if the option is active")


class OptionUpdate(SQLModel):
    name: Optional[str] = Field(
        default=None, max_length=100, description="Option name")
    description: Optional[str] = Field(
        default=None, max_length=500, description="Option description")
    path: Optional[str] = Field(
        default=None, max_length=500, description="Option path")
    icon: Optional[str] = Field(
        default=None, max_length=500, description="Option icon")
    type: Optional[str] = Field(
        default=None, max_length=100, description="Option type")
    sort_order: Optional[int] = Field(
        default=None, description="Display order")
    is_active: Optional[bool] = Field(
        default=None, description="Indicates if the option is active")

# Privileges Models


class PrivilegeBase(SQLModel):
    role: str = Field(sa_column=Column(
        'role', String, ForeignKey('roles.code'), primary_key=True))
    module: str = Field(sa_column=Column(
        'module', String(50), primary_key=True))
    option: str = Field(sa_column=Column(
        'option', String(50), primary_key=True))
    can_edit: bool = Field(default=True)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


class Privilege(PrivilegeBase, table=True):
    __tablename__ = "privileges"


class PrivilegeCreate(SQLModel):
    role: str = Field(max_length=50, description="Role code")
    module: str = Field(max_length=50, description="Module code")
    option: str = Field(max_length=50, description="Option code")
    can_edit: Optional[bool] = Field(
        default=True, description="Indicates if can edit")
    is_active: Optional[bool] = Field(
        default=True, description="Indicates if the privilege is active")


class PrivilegeUpdate(SQLModel):
    can_edit: Optional[bool] = Field(
        default=None, description="Indicates if can edit")
    is_active: Optional[bool] = Field(
        default=None, description="Indicates if the privilege is active")
