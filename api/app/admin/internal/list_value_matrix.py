"""List value matrix: one list's values with their label in every language.

Backs `/admin/list_items?list=CODE`, where an administrator edits a list's
values as one table (value, order, a label per language) instead of creating
`list_items` rows one by one, one language at a time.

A value is the set of its active rows, one per language. Saving replaces that
set in one transaction: missing rows are inserted, inactive ones reactivated,
labels and `sort_order` updated, and rows no longer present (a removed value,
or a blank label) deactivated (logical delete).
"""
from datetime import datetime
from typing import Dict, List, Tuple

from sqlmodel import Session, select

from .models import List as ListModel, ListItem, ListValueEntry, ListValueMatrix

MAX_LANG = 10
MAX_LABEL = 200


class ListNotFound(LookupError):
    pass


class InvalidMatrix(ValueError):
    pass


def _list(session: Session, list_code: str) -> ListModel:
    lst = session.get(ListModel, list_code)
    if not lst:
        raise ListNotFound(f"List with code '{list_code}' does not exist")
    return lst


def get_matrix(session: Session, list_code: str) -> ListValueMatrix:
    lst = _list(session, list_code)
    rows = session.exec(
        select(ListItem).where(ListItem.list == list_code, ListItem.is_active == True)
        .order_by(ListItem.sort_order, ListItem.value, ListItem.lang)
    ).all()
    values: Dict[str, ListValueEntry] = {}
    languages: List[str] = []
    for r in rows:
        entry = values.setdefault(r.value, ListValueEntry(value=r.value, sort_order=r.sort_order))
        entry.labels[r.lang] = r.label
        if r.lang not in languages:
            languages.append(r.lang)
    return ListValueMatrix(
        list=lst.code, list_name=lst.name,
        languages=sorted(languages, key=lambda lang: (lang != "en", lang)),
        values=list(values.values()),
    )


def save_matrix(session: Session, list_code: str, entries: List[ListValueEntry]) -> ListValueMatrix:
    """Replace the list's values and labels. Commits."""
    _list(session, list_code)

    wanted: Dict[Tuple[str, str], Tuple[str, int]] = {}
    seen = set()
    for e in entries:
        value = e.value.strip()
        if not value:
            raise InvalidMatrix("Every value needs a code")
        if value in seen:
            raise InvalidMatrix(f"Value '{value}' is listed more than once")
        seen.add(value)
        labels = {lang.strip(): (label or "").strip() for lang, label in e.labels.items()}
        labels = {lang: label for lang, label in labels.items() if label}
        if not labels:
            raise InvalidMatrix(f"Value '{value}' needs a label in at least one language")
        for lang, label in labels.items():
            if not lang or len(lang) > MAX_LANG:
                raise InvalidMatrix(f"Invalid language code '{lang}'")
            if len(label) > MAX_LABEL:
                raise InvalidMatrix(
                    f"The '{lang}' label of '{value}' is longer than {MAX_LABEL} characters")
            wanted[(value, lang)] = (label, e.sort_order)

    now = datetime.utcnow()
    existing = {
        (r.value, r.lang): r
        for r in session.exec(select(ListItem).where(ListItem.list == list_code)).all()
    }
    for key, row in existing.items():
        if key in wanted:
            label, order = wanted[key]
            if not row.is_active or row.label != label or row.sort_order != order:
                row.is_active = True
                row.label = label
                row.sort_order = order
                row.updated_at = now
                session.add(row)
        elif row.is_active:
            row.is_active = False
            row.updated_at = now
            session.add(row)
    for (value, lang), (label, order) in wanted.items():
        if (value, lang) not in existing:
            session.add(ListItem(list=list_code, lang=lang, value=value, label=label,
                                 sort_order=order, is_active=True))
    session.commit()
    return get_matrix(session, list_code)
