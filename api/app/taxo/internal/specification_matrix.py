"""Specification matrix: one category's specification over the feature catalog.

Backs `/taxo/specifications?category=CODE`, where an administrator ticks the
features a category specifies (with default value, required, copyable and
order) instead of creating specification rows one by one.

The catalog is every active feature. Saving replaces the category's set over
that catalog in one transaction: missing rows are inserted, inactive ones
reactivated, fields updated, and rows no longer ticked deactivated (logical
delete). Specifications pointing at an inactive feature are outside the
catalog and left untouched.
"""
from datetime import datetime
from typing import Dict, List

from sqlmodel import Session, select

from ...internal.list_values import validate_list_value
from .models import (
    Category, Feature, Specification, SpecificationMatrix,
    SpecificationMatrixEntry, SpecificationMatrixFeature,
)


class CategoryNotFound(LookupError):
    pass


class InvalidMatrix(ValueError):
    pass


def _category(session: Session, category_code: str) -> Category:
    category = session.get(Category, category_code)
    if not category:
        raise CategoryNotFound(f"Category with code '{category_code}' does not exist")
    return category


def _catalog(session: Session) -> List[Feature]:
    return session.exec(
        select(Feature).where(Feature.is_active == True)
        .order_by(Feature.type, Feature.name, Feature.code)
    ).all()


def get_matrix(session: Session, category_code: str) -> SpecificationMatrix:
    category = _category(session, category_code)
    specs = {
        s.feature: s
        for s in session.exec(
            select(Specification).where(
                Specification.category == category_code, Specification.is_active == True)
        ).all()
    }
    features = []
    for f in _catalog(session):
        s = specs.get(f.code)
        features.append(SpecificationMatrixFeature(
            code=f.code, name=f.name, description=f.description, type=f.type, list=f.list,
            specified=s is not None,
            default_value=s.default_value if s else None,
            required=bool(s and s.required),
            copyable=bool(s and s.copyable),
            sort_order=s.sort_order if s else 0,
        ))
    return SpecificationMatrix(category=category.code, category_name=category.name,
                               features=features)


def save_matrix(session: Session, category_code: str,
                entries: List[SpecificationMatrixEntry]) -> SpecificationMatrix:
    """Replace the category's specifications over the catalog. Commits."""
    _category(session, category_code)
    catalog = {f.code: f for f in _catalog(session)}

    wanted: Dict[str, SpecificationMatrixEntry] = {}
    for e in entries:
        feature = catalog.get(e.feature)
        if feature is None:
            raise InvalidMatrix(f"Feature with code '{e.feature}' does not exist or is inactive")
        if e.feature in wanted:
            raise InvalidMatrix(f"Feature '{e.feature}' is listed more than once")
        value = (e.default_value or "").strip() or None
        if value is not None and feature.list:
            try:
                validate_list_value(session, feature.list, value)
            except ValueError as err:
                raise InvalidMatrix(f"Default value of '{e.feature}': {err}")
        wanted[e.feature] = e.model_copy(update={"default_value": value})

    now = datetime.utcnow()
    existing = {
        s.feature: s
        for s in session.exec(
            select(Specification).where(Specification.category == category_code)
        ).all()
    }
    fields = ("default_value", "required", "copyable", "sort_order")
    for code, row in existing.items():
        if code not in catalog:
            continue
        if code in wanted:
            e = wanted[code]
            if not row.is_active or any(getattr(row, k) != getattr(e, k) for k in fields):
                row.is_active = True
                for k in fields:
                    setattr(row, k, getattr(e, k))
                row.updated_at = now
                session.add(row)
        elif row.is_active:
            row.is_active = False
            row.updated_at = now
            session.add(row)
    for code, e in wanted.items():
        if code not in existing:
            session.add(Specification(category=category_code, feature=code, is_active=True,
                                      **{k: getattr(e, k) for k in fields}))
    session.commit()
    return get_matrix(session, category_code)
