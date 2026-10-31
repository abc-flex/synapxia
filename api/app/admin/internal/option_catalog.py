"""Option catalog: every active option of every active module.

Read here rather than through `GET /api/options/`, which is scoped to the
CALLER's own privileges (it drives the sidebar), so a non-superuser
administrator would otherwise see only the options their own profile holds.
Shared by the options admin page and the privilege matrix.
"""
from typing import Dict, List, Tuple

from sqlmodel import Session, select

from .models import Module, Option, OptionCatalogModule, OptionCatalogOption


def catalog(session: Session) -> Tuple[List[Module], Dict[str, List[Option]]]:
    """Active modules by sort order, and their active options by sort order."""
    modules = session.exec(
        select(Module).where(Module.is_active == True)
        .order_by(Module.sort_order, Module.code)
    ).all()
    codes = {m.code for m in modules}
    options: Dict[str, List[Option]] = {}
    for o in session.exec(
        select(Option).where(Option.is_active == True)
        .order_by(Option.module, Option.sort_order, Option.name)
    ).all():
        if o.module in codes:
            options.setdefault(o.module, []).append(o)
    return list(modules), options


def get_catalog(session: Session) -> List[OptionCatalogModule]:
    modules, options = catalog(session)
    return [
        OptionCatalogModule(
            code=m.code, name=m.name, description=m.description,
            icon=m.icon, sort_order=m.sort_order,
            options=[
                OptionCatalogOption(
                    code=o.code, name=o.name, description=o.description,
                    path=o.path, icon=o.icon, type=o.type, sort_order=o.sort_order,
                )
                for o in options.get(m.code, [])
            ],
        )
        for m in modules
    ]
