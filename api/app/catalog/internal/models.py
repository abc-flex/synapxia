"""Models for Digital Assets module"""
from sqlmodel import Field, SQLModel, Column, String, ForeignKey
from sqlalchemy import JSON
from typing import Optional, List, Dict, Any
from datetime import datetime

# Categories Models
class CategoryBase(SQLModel):
    code: str = Field(max_length=50, primary_key=True)
    name: str = Field(max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    parent: Optional[str] = Field(default=None, foreign_key="categories.code")
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

class Category(CategoryBase, table=True):
    __tablename__ = "categories"

class CategoryCreate(SQLModel):
    code: str = Field(max_length=50, description="Código único de la categoría")
    name: str = Field(max_length=100, description="Nombre de la categoría")
    description: Optional[str] = Field(default=None, max_length=500, description="Descripción de la categoría")
    parent: Optional[str] = Field(default=None, max_length=50, description="Código de la categoría padre")
    is_active: Optional[bool] = Field(default=True, description="Indica si la categoría está activa")

class CategoryUpdate(SQLModel):
    name: Optional[str] = Field(default=None, max_length=100, description="Nombre de la categoría")
    description: Optional[str] = Field(default=None, max_length=500, description="Descripción de la categoría")
    parent: Optional[str] = Field(default=None, max_length=50, description="Código de la categoría padre")
    is_active: Optional[bool] = Field(default=None, description="Indica si la categoría está activa")

# Characteristics Models
class CharacteristicBase(SQLModel):
    code: str = Field(max_length=50, primary_key=True)
    name: str = Field(max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    type: str = Field(max_length=100)
    status: str = Field(max_length=100)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

class Characteristic(CharacteristicBase, table=True):
    __tablename__ = "characteristics"

class CharacteristicCreate(SQLModel):
    code: str = Field(max_length=50, description="Código único de la característica")
    name: str = Field(max_length=100, description="Nombre de la característica")
    description: Optional[str] = Field(default=None, max_length=500, description="Descripción de la característica")
    type: str = Field(max_length=100, description="Tipo de característica")
    status: str = Field(max_length=100, description="Estado de la característica")
    is_active: Optional[bool] = Field(default=True, description="Indica si la característica está activa")

class CharacteristicUpdate(SQLModel):
    name: Optional[str] = Field(default=None, max_length=100, description="Nombre de la característica")
    description: Optional[str] = Field(default=None, max_length=500, description="Descripción de la característica")
    type: Optional[str] = Field(default=None, max_length=100, description="Tipo de característica")
    status: Optional[str] = Field(default=None, max_length=100, description="Estado de la característica")
    is_active: Optional[bool] = Field(default=None, description="Indica si la característica está activa")

# Assets Models
class AssetBase(SQLModel):
    code: str = Field(max_length=50, primary_key=True)
    name: str = Field(max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    category: Optional[str] = Field(default=None, foreign_key="categories.code")
    reference: Optional[str] = Field(default=None, max_length=500)
    type: str = Field(max_length=100)
    status: str = Field(max_length=100)
    visibility: str = Field(max_length=100)
    tags: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column("tags", JSON))
    details: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column("details", JSON))
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

class Asset(AssetBase, table=True):
    __tablename__ = "assets"

class AssetCreate(SQLModel):
    code: str = Field(max_length=50, description="Código único del activo")
    name: str = Field(max_length=100, description="Nombre del activo")
    description: Optional[str] = Field(default=None, max_length=500, description="Descripción del activo")
    category: Optional[str] = Field(default=None, max_length=50, description="Código de la categoría")
    reference: Optional[str] = Field(default=None, max_length=500, description="Referencia del activo")
    type: str = Field(max_length=100, description="Tipo de activo")
    status: str = Field(max_length=100, description="Estado del activo")
    visibility: str = Field(max_length=100, description="Visibilidad del activo")
    tags: Optional[Dict[str, Any]] = Field(default=None, description="Tags del activo (JSON)")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Detalles del activo (JSON)")
    is_active: Optional[bool] = Field(default=True, description="Indica si el activo está activo")

class AssetUpdate(SQLModel):
    name: Optional[str] = Field(default=None, max_length=100, description="Nombre del activo")
    description: Optional[str] = Field(default=None, max_length=500, description="Descripción del activo")
    category: Optional[str] = Field(default=None, max_length=50, description="Código de la categoría")
    reference: Optional[str] = Field(default=None, max_length=500, description="Referencia del activo")
    type: Optional[str] = Field(default=None, max_length=100, description="Tipo de activo")
    status: Optional[str] = Field(default=None, max_length=100, description="Estado del activo")
    visibility: Optional[str] = Field(default=None, max_length=100, description="Visibilidad del activo")
    tags: Optional[Dict[str, Any]] = Field(default=None, description="Tags del activo (JSON)")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Detalles del activo (JSON)")
    is_active: Optional[bool] = Field(default=None, description="Indica si el activo está activo")

# Characterizations Models
class CharacterizationBase(SQLModel):
    asset: str = Field(sa_column=Column('asset', String, ForeignKey('assets.code'), primary_key=True))
    characteristic: str = Field(sa_column=Column('characteristic', String, ForeignKey('characteristics.code'), primary_key=True))
    value: str = Field(max_length=500)
    details: Optional[str] = Field(default=None, max_length=500)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

class Characterization(CharacterizationBase, table=True):
    __tablename__ = "characterizations"

class CharacterizationCreate(SQLModel):
    asset: str = Field(max_length=50, description="Código del activo")
    characteristic: str = Field(max_length=50, description="Código de la característica")
    value: str = Field(max_length=500, description="Valor de la caracterización")
    details: Optional[str] = Field(default=None, max_length=500, description="Detalles adicionales")
    is_active: Optional[bool] = Field(default=True, description="Indica si la caracterización está activa")

class CharacterizationUpdate(SQLModel):
    value: Optional[str] = Field(default=None, max_length=500, description="Valor de la caracterización")
    details: Optional[str] = Field(default=None, max_length=500, description="Detalles adicionales")
    is_active: Optional[bool] = Field(default=None, description="Indica si la caracterización está activa")

# Favorites Models
class FavoriteBase(SQLModel):
    user_id: int = Field(sa_column=Column('user_id', ForeignKey('users.id'), primary_key=True))
    asset: str = Field(sa_column=Column('asset', String, ForeignKey('assets.code'), primary_key=True))
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

class Favorite(FavoriteBase, table=True):
    __tablename__ = "favorites"

class FavoriteCreate(SQLModel):
    user_id: int = Field(description="ID del usuario")
    asset: str = Field(max_length=50, description="Código del activo")
    is_active: Optional[bool] = Field(default=True, description="Indica si el favorito está activo")

class FavoriteUpdate(SQLModel):
    is_active: Optional[bool] = Field(default=None, description="Indica si el favorito está activo")

# Actions Models
class ActionBase(SQLModel):
    asset: str = Field(max_length=50, foreign_key="assets.code")
    user_id: int = Field(foreign_key="users.id")
    type: str = Field(max_length=100)
    content: Optional[str] = Field(default=None, max_length=500)
    reference: Optional[str] = Field(default=None, max_length=500)
    parent: Optional[int] = Field(default=None, foreign_key="actions.id")
    details: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column("details", JSON))
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    measured_at: Optional[datetime] = None

class Action(ActionBase, table=True):
    __tablename__ = "actions"
    id: Optional[int] = Field(default=None, primary_key=True)

class ActionCreate(SQLModel):
    asset: str = Field(max_length=50, description="Código del activo")
    user_id: int = Field(description="ID del usuario")
    type: str = Field(max_length=100, description="Tipo de acción")
    content: Optional[str] = Field(default=None, max_length=500, description="Contenido de la acción")
    reference: Optional[str] = Field(default=None, max_length=500, description="Referencia de la acción")
    parent: Optional[int] = Field(default=None, description="ID de la acción padre")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Detalles de la acción (JSON)")
    is_active: Optional[bool] = Field(default=True, description="Indica si la acción está activa")

class ActionUpdate(SQLModel):
    content: Optional[str] = Field(default=None, max_length=500, description="Contenido de la acción")
    reference: Optional[str] = Field(default=None, max_length=500, description="Referencia de la acción")
    parent: Optional[int] = Field(default=None, description="ID de la acción padre")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Detalles de la acción (JSON)")
    is_active: Optional[bool] = Field(default=None, description="Indica si la acción está activa")

# Asset Relations Models
class AssetRelationBase(SQLModel):
    source: str = Field(sa_column=Column('source', String, ForeignKey('assets.code'), primary_key=True))
    target: str = Field(sa_column=Column('target', String, ForeignKey('assets.code'), primary_key=True))
    type: str = Field(max_length=100)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

class AssetRelation(AssetRelationBase, table=True):
    __tablename__ = "asset_relations"

class AssetRelationCreate(SQLModel):
    source: str = Field(max_length=50, description="Código del activo origen")
    target: str = Field(max_length=50, description="Código del activo destino")
    type: str = Field(max_length=100, description="Tipo de relación")
    is_active: Optional[bool] = Field(default=True, description="Indica si la relación está activa")

class AssetRelationUpdate(SQLModel):
    type: Optional[str] = Field(default=None, max_length=100, description="Tipo de relación")
    is_active: Optional[bool] = Field(default=None, description="Indica si la relación está activa")
