"""Process links (Process Management, HU-PR02–04): read and replace one tab's set.

Each Related tab saves its whole desired set in one call. ``replace_*`` diffs it
against the stored rows inside the caller's transaction — it never commits, so
create (US5) can compose it with the new process:

- a stored active link missing from the set is deactivated (``is_active = False``);
- an identical inactive row is reactivated, never duplicated;
- a new link is inserted;
- a link whose rationale changed is updated.

Any invalid item raises ``ValueError`` before anything is touched, so the caller
rolls the whole tab back (→ 400).
"""
from datetime import datetime
from typing import Dict, List, Optional, Sequence, Tuple

from sqlmodel import Session, or_, select

from . import relation_rules as rules
from .models import (
    AssetLinkItem, InitLinkItem, Process, ProcessAsset, ProcessAssetRead, ProcessInit,
    ProcessInitRead, ProcessRelationRead, RelatedProcess, RelationItem,
)
from ...inits.internal.models import Initiative
from ...internal.list_values import validate_list_value
from ...lib.internal.models import Asset


def _clean(text: Optional[str]) -> Optional[str]:
    text = (text or "").strip()
    return text or None


def _require_type(list_code: str, session: Session, value: Optional[str]) -> str:
    value = (value or "").strip()
    if not value:
        raise ValueError("Each link needs a relation type.")
    validate_list_value(session, list_code, value)
    return value


def _touch(row, rationale: Optional[str], now: datetime) -> None:
    """Reactivate and/or update the rationale; stamp updated_at only on change."""
    changed = False
    if not row.is_active:
        row.is_active = True
        changed = True
    if (row.rationale or None) != rationale:
        row.rationale = rationale
        changed = True
    if changed:
        row.updated_at = now


# ── Process → process ────────────────────────────────────────────────────────


def _relation_rows(session: Session, code: str) -> List[RelatedProcess]:
    """Every row (active or not) this process owns: outgoing, plus undirected
    rows where it is the target."""
    return session.exec(
        select(RelatedProcess).where(
            or_(
                RelatedProcess.source == code,
                (RelatedProcess.target == code) & RelatedProcess.type.in_(list(rules.UNDIRECTED)),
            )
        )
    ).all()


def list_relations(session: Session, code: str) -> List[ProcessRelationRead]:
    rows = [r for r in _relation_rows(session, code) if r.is_active]
    others = {r.target if r.source == code else r.source for r in rows}
    procs = {
        p.code: p
        for p in session.exec(select(Process).where(Process.code.in_(list(others)))).all()
    } if others else {}
    out = []
    for r in rows:
        incoming = r.source != code
        other = r.source if incoming else r.target
        p = procs.get(other)
        out.append(ProcessRelationRead(
            source=r.source, target=other,
            target_name=p.name if p else None, target_type=p.type if p else None,
            target_active=bool(p and p.is_active), type=r.type, rationale=r.rationale,
            direction="incoming" if incoming else "outgoing",
        ))
    out.sort(key=lambda x: (x.type, x.target))
    return out


def replace_relations(
    session: Session, process: Process, items: Sequence[RelationItem]
) -> None:
    code = process.code
    targets = {(i.target or "").strip().upper() for i in items}
    procs = {
        p.code: p
        for p in session.exec(select(Process).where(Process.code.in_(list(targets)))).all()
    } if targets else {}

    desired: Dict[Tuple[str, str, str], Tuple[str, str, Optional[str]]] = {}
    for item in items:
        target = (item.target or "").strip().upper()
        if not target:
            raise ValueError("Each related process needs a target process.")
        if target == code:
            raise ValueError("A process cannot be related to itself.")
        other = procs.get(target)
        if not other or not other.is_active:
            raise ValueError(f"Process '{target}' does not exist or was removed.")
        rel_type = _require_type(rules.PROCESS_RELATION_LIST, session, item.type)
        rules.check_compatible(rel_type, process.type, other.type)
        key = rules.pair_key(code, target, rel_type)
        if key in desired:
            raise ValueError(
                f"'{target}' is already related with {rel_type}; each pair can be linked "
                "once per relation type.")
        desired[key] = (target, rel_type, _clean(item.rationale))

    now = datetime.utcnow()
    by_key: Dict[Tuple[str, str, str], List[RelatedProcess]] = {}
    for row in _relation_rows(session, code):
        by_key.setdefault(rules.pair_key(row.source, row.target, row.type), []).append(row)

    for key, rows in by_key.items():
        if key not in desired:
            for row in rows:
                if row.is_active:
                    row.is_active = False
                    row.updated_at = now
                    session.add(row)

    for key, (target, rel_type, rationale) in desired.items():
        rows = by_key.get(key, [])
        # Prefer the live row (keeps an incoming undirected link as stored), then
        # the inactive row in this orientation, then any inactive one.
        row = next((r for r in rows if r.is_active), None) \
            or next((r for r in rows if r.source == code), None) \
            or (rows[0] if rows else None)
        if row is None:
            session.add(RelatedProcess(
                source=code, target=target, type=rel_type, rationale=rationale))
            continue
        _touch(row, rationale, now)
        session.add(row)
    session.flush()


# ── Process → asset ──────────────────────────────────────────────────────────


def list_assets(session: Session, code: str) -> List[ProcessAssetRead]:
    rows = session.exec(
        select(ProcessAsset).where(ProcessAsset.process == code, ProcessAsset.is_active == True)  # noqa: E712
    ).all()
    ids = {r.asset for r in rows}
    assets = {
        a.id: a for a in session.exec(select(Asset).where(Asset.id.in_(list(ids)))).all()
    } if ids else {}
    out = [
        ProcessAssetRead(
            asset=r.asset,
            asset_name=assets[r.asset].name if r.asset in assets else None,
            category=assets[r.asset].category if r.asset in assets else None,
            asset_active=bool(r.asset in assets and assets[r.asset].is_active),
            type=r.type, rationale=r.rationale,
        )
        for r in rows
    ]
    out.sort(key=lambda x: ((x.asset_name or "").lower(), x.type))
    return out


def replace_assets(session: Session, process: Process, items: Sequence[AssetLinkItem]) -> None:
    ids = {i.asset for i in items}
    assets = {
        a.id: a for a in session.exec(select(Asset).where(Asset.id.in_(list(ids)))).all()
    } if ids else {}
    desired: Dict[Tuple[int, str], Optional[str]] = {}
    for item in items:
        asset = assets.get(item.asset)
        if not asset or not asset.is_active:
            raise ValueError(f"Asset {item.asset} does not exist or was removed.")
        rel_type = _require_type(rules.ASSET_INIT_RELATION_LIST, session, item.type)
        key = (item.asset, rel_type)
        if key in desired:
            raise ValueError(
                f"Asset '{asset.name}' is already related with {rel_type}; each pair can be "
                "linked once per relation type.")
        desired[key] = _clean(item.rationale)

    now = datetime.utcnow()
    existing = {
        (r.asset, r.type): r
        for r in session.exec(select(ProcessAsset).where(ProcessAsset.process == process.code)).all()
    }
    for key, row in existing.items():
        if key not in desired and row.is_active:
            row.is_active = False
            row.updated_at = now
            session.add(row)
    for (asset_id, rel_type), rationale in desired.items():
        row = existing.get((asset_id, rel_type))
        if row is None:
            session.add(ProcessAsset(
                process=process.code, asset=asset_id, type=rel_type, rationale=rationale))
            continue
        _touch(row, rationale, now)
        session.add(row)
    session.flush()


# ── Process → initiative ─────────────────────────────────────────────────────


def list_inits(session: Session, code: str) -> List[ProcessInitRead]:
    rows = session.exec(
        select(ProcessInit).where(ProcessInit.process == code, ProcessInit.is_active == True)  # noqa: E712
    ).all()
    ids = {r.init for r in rows}
    inits = {
        i.id: i for i in session.exec(select(Initiative).where(Initiative.id.in_(list(ids)))).all()
    } if ids else {}
    out = [
        ProcessInitRead(
            init=r.init,
            init_name=inits[r.init].name if r.init in inits else None,
            init_active=bool(r.init in inits and inits[r.init].is_active),
            type=r.type, rationale=r.rationale,
        )
        for r in rows
    ]
    out.sort(key=lambda x: ((x.init_name or "").lower(), x.type))
    return out


def replace_inits(session: Session, process: Process, items: Sequence[InitLinkItem]) -> None:
    ids = {i.init for i in items}
    inits = {
        i.id: i for i in session.exec(select(Initiative).where(Initiative.id.in_(list(ids)))).all()
    } if ids else {}
    desired: Dict[Tuple[int, str], Optional[str]] = {}
    for item in items:
        init = inits.get(item.init)
        if not init or not init.is_active:
            raise ValueError(f"Initiative {item.init} does not exist or was removed.")
        rel_type = _require_type(rules.ASSET_INIT_RELATION_LIST, session, item.type)
        key = (item.init, rel_type)
        if key in desired:
            raise ValueError(
                f"Initiative '{init.name}' is already related with {rel_type}; each pair can be "
                "linked once per relation type.")
        desired[key] = _clean(item.rationale)

    now = datetime.utcnow()
    existing = {
        (r.init, r.type): r
        for r in session.exec(select(ProcessInit).where(ProcessInit.process == process.code)).all()
    }
    for key, row in existing.items():
        if key not in desired and row.is_active:
            row.is_active = False
            row.updated_at = now
            session.add(row)
    for (init_id, rel_type), rationale in desired.items():
        row = existing.get((init_id, rel_type))
        if row is None:
            session.add(ProcessInit(
                process=process.code, init=init_id, type=rel_type, rationale=rationale))
            continue
        _touch(row, rationale, now)
        session.add(row)
    session.flush()
