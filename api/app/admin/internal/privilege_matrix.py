"""Privilege matrix: one profile's access over the whole option catalog.

Backs `/admin/privileges?profile=CODE`, where an administrator ticks the
options a profile may use instead of creating privilege rows one by one.

The catalog is every active option of every active module. It is read here
rather than through `GET /api/options/`, which is scoped to the CALLER's own
privileges (it drives the sidebar), so a non-superuser administrator would
otherwise see only the options their own profile holds.

Saving replaces the profile's set over that catalog in one transaction:
missing rows are inserted, inactive ones reactivated, `can_edit` updated, and
rows no longer ticked deactivated (logical delete). Privileges pointing at an
inactive or unknown option are outside the catalog and left untouched.
"""
from datetime import datetime
from typing import Dict, List, Tuple

from sqlmodel import Session, select

from .models import (
    Module, Option, Privilege, PrivilegeMatrix, PrivilegeMatrixEntry,
    PrivilegeMatrixModule, PrivilegeMatrixOption, Profile,
)

# The option that lets a profile manage privileges. A non-superuser saving
# their own profile must keep it with edit access, or they lock themselves out.
SELF_GUARD = ("ADMIN", "PRIVILEGES")


class ProfileNotFound(LookupError):
    pass


class InvalidMatrix(ValueError):
    pass


def _catalog(session: Session) -> Tuple[List[Module], Dict[str, List[Option]]]:
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


def _profile(session: Session, profile_code: str) -> Profile:
    profile = session.get(Profile, profile_code)
    if not profile:
        raise ProfileNotFound(f"Profile with code '{profile_code}' does not exist")
    return profile


def get_matrix(session: Session, profile_code: str) -> PrivilegeMatrix:
    profile = _profile(session, profile_code)
    modules, options = _catalog(session)
    granted = {
        (p.module, p.option): p.can_edit
        for p in session.exec(
            select(Privilege).where(
                Privilege.profile == profile_code, Privilege.is_active == True)
        ).all()
    }
    return PrivilegeMatrix(
        profile=profile.code,
        profile_name=profile.name,
        modules=[
            PrivilegeMatrixModule(
                code=m.code, name=m.name, icon=m.icon,
                options=[
                    PrivilegeMatrixOption(
                        code=o.code, name=o.name, description=o.description,
                        path=o.path, type=o.type,
                        granted=(m.code, o.code) in granted,
                        can_edit=granted.get((m.code, o.code), False),
                    )
                    for o in options.get(m.code, [])
                ],
            )
            for m in modules
        ],
    )


def save_matrix(session: Session, profile_code: str, entries: List[PrivilegeMatrixEntry],
                actor) -> PrivilegeMatrix:
    """Replace the profile's privileges over the catalog. Commits."""
    _profile(session, profile_code)
    modules, options = _catalog(session)
    catalog = {(o.module, o.code) for opts in options.values() for o in opts}

    wanted: Dict[Tuple[str, str], bool] = {}
    for e in entries:
        key = (e.module, e.option)
        if key not in catalog:
            raise InvalidMatrix(
                f"Option with module '{e.module}' and code '{e.option}' does not exist or is inactive")
        if key in wanted:
            raise InvalidMatrix(f"Option '{e.module}/{e.option}' is listed more than once")
        wanted[key] = bool(e.can_edit)

    if (not actor.is_superuser and actor.profile == profile_code
            and SELF_GUARD in catalog and not wanted.get(SELF_GUARD)):
        raise InvalidMatrix(
            "You cannot remove edit access to Privileges from your own profile")

    now = datetime.utcnow()
    existing = {
        (p.module, p.option): p
        for p in session.exec(
            select(Privilege).where(Privilege.profile == profile_code)
        ).all()
    }
    for key, row in existing.items():
        if key not in catalog:
            continue
        if key in wanted:
            if not row.is_active or row.can_edit != wanted[key]:
                row.is_active = True
                row.can_edit = wanted[key]
                row.updated_at = now
                session.add(row)
        elif row.is_active:
            row.is_active = False
            row.updated_at = now
            session.add(row)
    for (module, option), can_edit in wanted.items():
        if (module, option) not in existing:
            session.add(Privilege(profile=profile_code, module=module, option=option,
                                  can_edit=can_edit, is_active=True))
    session.commit()
    return get_matrix(session, profile_code)
