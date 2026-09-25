"""List-backed core field validation for initiatives.

Shared by Initiative Management's PUT and by the propose / modify workflow so
the same values are accepted everywhere. Raises ValueError (routes map to 400).
"""
from typing import Iterable

from sqlmodel import Session, select

from ...admin.internal.models import ListItem

# List-backed core fields and the list each value must come from.
LIST_FIELDS = {
    "type": "INITIATIVE_TYPE",
    "expected_impact": "EXPECTED_IMPACT",
    "priority_level": "PRIORITY_LEVEL",
}
REQUIRED_FIELDS = ("name", "expected_impact", "priority_level")


def validate_list_value(session: Session, list_code: str, value) -> None:
    """ValueError when `value` is not defined by `list_code` (any language row
    counts — values are language-independent). None is always accepted."""
    if value is None:
        return
    known = session.exec(
        select(ListItem.value).where(ListItem.list == list_code, ListItem.value == value)
    ).first()
    if known is None:
        raise ValueError(f"'{value}' is not a valid {list_code} value")


def validate_core_fields(
    session: Session, fields: dict, required: Iterable[str] = (),
) -> None:
    """Check the sent core fields: listed `required` ones must be non-blank, and
    every list-backed one must hold a value of its list."""
    for field in required:
        if field in fields and not (fields[field] or "").strip():
            raise ValueError(f"'{field}' cannot be blank")
    for field, list_code in LIST_FIELDS.items():
        if field in fields:
            validate_list_value(session, list_code, fields[field])
