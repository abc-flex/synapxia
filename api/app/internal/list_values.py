"""List-value validation shared by every domain (Constitution I).

A list-backed field stores a `list_items.value`. Values are language-independent,
so a value is valid when ANY language row of the list defines it. Each domain
keeps its own field → list map (``inits/internal/list_validation.py``,
``insights/internal/list_validation.py``) and calls this one check.
"""
from sqlmodel import Session, select

from ..admin.internal.models import ListItem


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
