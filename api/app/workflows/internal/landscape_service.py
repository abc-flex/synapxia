"""The process landscape read by the Value Chain and the Process Map.

specs/010-process-landscape-views (HU-PR05 / HU-PR06). Read-only: nothing here
writes or commits.

- **Shown** (FR-002): active processes that are not DEPRECATED. Relations count
  only when both ends are shown; asset / initiative links only when the link and
  its target are active.
- **Tree**: ``display_parent`` is the nearest *shown* ancestor, so a process
  under a Deprecated parent hangs from the next one up (or the top level).
- **Counts** (FR-001, FR-007): ``own_*`` are the process's own distinct links;
  ``assets`` / ``inits`` are distinct over the process and every shown
  descendant (sets, since one asset may be linked at several levels).
  ``is_opportunity`` = no rolled-up asset and no rolled-up initiative.
- **Order** (FR-006): ``chain_order`` over PRECEDES, the single definition both
  views draw with (research R3).
- **Bound**: at most ``LANDSCAPE_MAX_PROCESSES`` processes by code, flagged
  ``truncated``; a constant number of queries, never one per process.
"""
import logging
from collections import defaultdict
from typing import Dict, Iterable, List, Optional, Set, Tuple

from sqlmodel import Session, select

from . import process_service, relation_rules
from .models import (
    LandscapeAssetLink, LandscapeInitLink, LandscapeProcess, LandscapeProcessDetail,
    LandscapeRelation, LandscapeRelationDetail, Process, ProcessAsset, ProcessInit,
    ProcessLandscape, RelatedProcess,
)
from ...admin.internal.models import BusinessUnit, User
from ...inits.internal.models import Initiative
from ...internal.permissions import has_privilege
from ...lib.internal.models import Asset

logger = logging.getLogger(__name__)

LANDSCAPE_MAX_PROCESSES = 2000
HIDDEN_STATUSES = ("DEPRECATED",)
PRIMARY, SUPPORT = "PRIMARY", "SUPPORT"
# Guard for the walk up through hidden ancestors (the hierarchy is acyclic).
_MAX_PARENT_HOPS = 50


# ── Order ────────────────────────────────────────────────────────────────────


def chain_order(codes: Iterable[str], edges: Iterable[Tuple[str, str]]) -> List[str]:
    """Order ``codes`` along PRECEDES ``edges`` (source, target).

    Codes touched by an edge inside the group come first, each after every code
    that precedes it, the smallest code first among those ready. A cycle is
    entered at its smallest remaining code. Codes with no edge follow, by code.
    Edges with an end outside the group are ignored.
    """
    group = set(codes)
    links = {(s, t) for s, t in edges if s in group and t in group and s != t}
    successors: Dict[str, List[str]] = defaultdict(list)
    indegree: Dict[str, int] = defaultdict(int)
    connected: Set[str] = set()
    for source, target in sorted(links):
        successors[source].append(target)
        indegree[target] += 1
        connected.update((source, target))

    remaining = set(connected)
    ordered: List[str] = []
    while remaining:
        ready = [c for c in remaining if indegree[c] == 0]
        node = min(ready) if ready else min(remaining)
        remaining.discard(node)
        ordered.append(node)
        for target in successors[node]:
            if target in remaining:
                indegree[target] -= 1
    return ordered + sorted(group - connected)


# ── The shown set and its tree ───────────────────────────────────────────────


def _shown_rows(session: Session) -> Tuple[List, bool]:
    """Shown processes by code, capped; the second value is ``truncated``."""
    rows = session.exec(
        select(Process.code, Process.name, Process.type, Process.status, Process.unit,
               Process.owner, Process.parent)
        .where(Process.is_active == True)  # noqa: E712
        .where(Process.status.not_in(HIDDEN_STATUSES))
        .order_by(Process.code)
        .limit(LANDSCAPE_MAX_PROCESSES + 1)
    ).all()
    truncated = len(rows) > LANDSCAPE_MAX_PROCESSES
    return list(rows[:LANDSCAPE_MAX_PROCESSES]), truncated


def _display_parents(session: Session, rows) -> Dict[str, Optional[str]]:
    """Nearest shown ancestor per shown code. Parents that are not shown are
    looked up a level at a time (one query per hierarchy level, not per row)."""
    shown = {r.code for r in rows}
    parent_of: Dict[str, Optional[str]] = {r.code: r.parent for r in rows}
    missing = {p for p in parent_of.values() if p and p not in parent_of}
    hops = 0
    while missing and hops < _MAX_PARENT_HOPS:
        found = session.exec(
            select(Process.code, Process.parent).where(Process.code.in_(missing))).all()
        for code, parent in found:
            parent_of[code] = parent
        for code in missing:
            parent_of.setdefault(code, None)   # dangling reference: stop there
        missing = {p for _, p in found if p and p not in parent_of}
        hops += 1

    result: Dict[str, Optional[str]] = {}
    for code in shown:
        current, seen = parent_of.get(code), {code}
        while current and current not in shown and current not in seen:
            seen.add(current)
            current = parent_of.get(current)
        result[code] = current if current in shown else None
    return result


def _children(codes: Iterable[str], display_parent: Dict[str, Optional[str]]) -> Dict[str, List[str]]:
    kids: Dict[str, List[str]] = defaultdict(list)
    for code in sorted(codes):
        parent = display_parent.get(code)
        if parent:
            kids[parent].append(code)
    return kids


def _subtree(code: str, kids: Dict[str, List[str]]) -> List[str]:
    out, stack = [], [code]
    while stack:
        node = stack.pop()
        out.append(node)
        stack.extend(kids.get(node, []))
    return out


def _link_pairs(session: Session, codes: Set[str]):
    """(process, asset) and (process, init) pairs over active links to active targets."""
    if not codes:
        return [], []
    assets = session.exec(
        select(ProcessAsset.process, ProcessAsset.asset)
        .join(Asset, Asset.id == ProcessAsset.asset)
        .where(ProcessAsset.is_active == True, Asset.is_active == True)  # noqa: E712
        .where(ProcessAsset.process.in_(codes))
    ).all()
    inits = session.exec(
        select(ProcessInit.process, ProcessInit.init)
        .join(Initiative, Initiative.id == ProcessInit.init)
        .where(ProcessInit.is_active == True, Initiative.is_active == True)  # noqa: E712
        .where(ProcessInit.process.in_(codes))
    ).all()
    return assets, inits


def _names(session: Session, units: Set[str], owners: Set[int]):
    unit_names = dict(session.exec(
        select(BusinessUnit.code, BusinessUnit.name).where(BusinessUnit.code.in_(units))
    ).all()) if units else {}
    owner_names = {
        u.id: process_service.full_name(u)
        for u in session.exec(select(User).where(User.id.in_(owners))).all()
    } if owners else {}
    return unit_names, owner_names


def _validate_unit(session: Session, unit: Optional[str]) -> Optional[str]:
    if unit is None or not unit.strip():
        return None
    unit = unit.strip()
    row = session.get(BusinessUnit, unit)
    if not row or not row.is_active:
        raise ValueError(f"Unknown business unit '{unit}'.")
    return unit


# ── Landscape ────────────────────────────────────────────────────────────────


def build_landscape(session: Session, user: User, unit: Optional[str] = None) -> ProcessLandscape:
    """Everything both views draw, in one bounded read (FR-001)."""
    unit = _validate_unit(session, unit)
    rows, truncated = _shown_rows(session)
    display_parent = _display_parents(session, rows)

    context: Set[str] = set()
    if unit:
        members = {r.code for r in rows if r.unit == unit}
        keep = set(members)
        for code in members:
            parent = display_parent[code]
            while parent and parent not in keep:
                keep.add(parent)
                context.add(parent)
                parent = display_parent[parent]
        rows = [r for r in rows if r.code in keep]
    codes = {r.code for r in rows}
    kids = _children(codes, display_parent)

    relations = session.exec(
        select(RelatedProcess.source, RelatedProcess.target, RelatedProcess.type)
        .where(RelatedProcess.is_active == True)  # noqa: E712
        .where(RelatedProcess.source.in_(codes), RelatedProcess.target.in_(codes))
        .order_by(RelatedProcess.source, RelatedProcess.target, RelatedProcess.type)
    ).all() if codes else []
    precedes = [(s, t) for s, t, kind in relations if kind == relation_rules.PRECEDES]

    asset_pairs, init_pairs = _link_pairs(session, codes)
    own_assets: Dict[str, Set[int]] = defaultdict(set)
    own_inits: Dict[str, Set[int]] = defaultdict(set)
    for process, asset in asset_pairs:
        own_assets[process].add(asset)
    for process, init in init_pairs:
        own_inits[process].add(init)

    # Post-order roll-up: a node's sets are its own plus its children's.
    all_assets: Dict[str, Set[int]] = {}
    all_inits: Dict[str, Set[int]] = {}
    roots = sorted(c for c in codes if display_parent[c] is None)
    for root in roots:
        for node in reversed(_subtree(root, kids)):
            assets, inits = set(own_assets[node]), set(own_inits[node])
            for child in kids.get(node, []):
                assets |= all_assets[child]
                inits |= all_inits[child]
            all_assets[node], all_inits[node] = assets, inits

    depth: Dict[str, int] = {}
    for root in roots:
        stack = [(root, 0)]
        while stack:
            node, level = stack.pop()
            depth[node] = level
            stack.extend((child, level + 1) for child in kids.get(node, []))

    unit_names, owner_names = _names(
        session, {r.unit for r in rows if r.unit}, {r.owner for r in rows})
    processes = [
        LandscapeProcess(
            code=r.code, name=r.name, type=r.type, status=r.status,
            unit=r.unit, unit_name=unit_names.get(r.unit), owner_name=owner_names.get(r.owner),
            parent=r.parent, display_parent=display_parent[r.code], depth=depth[r.code],
            child_order=chain_order(kids.get(r.code, []), precedes),
            context=r.code in context,
            own_assets=len(own_assets[r.code]), own_inits=len(own_inits[r.code]),
            assets=len(all_assets[r.code]), inits=len(all_inits[r.code]),
            is_opportunity=not all_assets[r.code] and not all_inits[r.code],
        )
        for r in rows
    ]
    type_of = {r.code: r.type for r in rows}
    if truncated:
        logger.info("process landscape truncated", extra={"cap": LANDSCAPE_MAX_PROCESSES})
    return ProcessLandscape(
        processes=processes,
        relations=[
            LandscapeRelation(source=s, target=t, type=kind,
                              directed=kind not in relation_rules.UNDIRECTED)
            for s, t, kind in relations
        ],
        primary_order=chain_order([c for c in roots if type_of[c] == PRIMARY], precedes),
        support_order=sorted(c for c in roots if type_of[c] == SUPPORT),
        unit=unit,
        truncated=truncated,
        can_value_chain=has_privilege(session, user, "PROC", "VALUE_CHAIN"),
        can_map=has_privilege(session, user, "PROC", "MAP"),
        can_manage=has_privilege(session, user, "PROC", "PROCESSES"),
    )


# ── Detail panel ─────────────────────────────────────────────────────────────


def build_detail(session: Session, code: str) -> LandscapeProcessDetail:
    """One shown process with its relations both ways and the asset /
    initiative links of it and its shown descendants (FR-014)."""
    rows, _ = _shown_rows(session)
    by_code = {r.code: r for r in rows}
    code = (code or "").strip().upper()
    if code not in by_code:
        raise LookupError(f"Process '{code}' not found")
    process = session.get(Process, code)
    display_parent = _display_parents(session, rows)
    kids = _children(by_code, display_parent)
    subtree = set(_subtree(code, kids))

    outgoing: Dict[Tuple[str, str], LandscapeRelationDetail] = {}
    incoming: Dict[Tuple[str, str], LandscapeRelationDetail] = {}
    relations = session.exec(
        select(RelatedProcess)
        .where(RelatedProcess.is_active == True)  # noqa: E712
        .where((RelatedProcess.source == code) | (RelatedProcess.target == code))
    ).all()
    for rel in relations:
        other = rel.target if rel.source == code else rel.source
        if other not in by_code or other == code:
            continue
        undirected = rel.type in relation_rules.UNDIRECTED
        bucket = outgoing if rel.source == code or undirected else incoming
        bucket.setdefault((rel.type, other), LandscapeRelationDetail(
            other=other, other_name=by_code[other].name, other_type=by_code[other].type,
            type=rel.type, rationale=rel.rationale, directed=not undirected))

    via = lambda holder: None if holder == code else holder  # noqa: E731
    asset_rows = session.exec(
        select(ProcessAsset, Asset.name, Asset.category)
        .join(Asset, Asset.id == ProcessAsset.asset)
        .where(ProcessAsset.is_active == True, Asset.is_active == True)  # noqa: E712
        .where(ProcessAsset.process.in_(subtree))
    ).all()
    init_rows = session.exec(
        select(ProcessInit, Initiative.name)
        .join(Initiative, Initiative.id == ProcessInit.init)
        .where(ProcessInit.is_active == True, Initiative.is_active == True)  # noqa: E712
        .where(ProcessInit.process.in_(subtree))
    ).all()
    assets = sorted(
        (LandscapeAssetLink(asset=link.asset, asset_name=name, category=category, type=link.type,
                            rationale=link.rationale, via=via(link.process))
         for link, name, category in asset_rows),
        key=lambda a: (a.via is not None, a.via or "", (a.asset_name or "").lower(), a.type))
    inits = sorted(
        (LandscapeInitLink(init=link.init, init_name=name, type=link.type,
                           rationale=link.rationale, via=via(link.process))
         for link, name in init_rows),
        key=lambda i: (i.via is not None, i.via or "", (i.init_name or "").lower(), i.type))

    unit_names, owner_names = _names(
        session, {process.unit} if process.unit else set(), {process.owner})
    parent = session.get(Process, process.parent) if process.parent else None
    order =lambda items: sorted(items.values(), key=lambda r: (r.type, r.other))  # noqa: E731
    return LandscapeProcessDetail(
        code=process.code, name=process.name, description=process.description,
        type=process.type, parent=process.parent,
        parent_name=parent.name if parent else None,
        unit=process.unit, unit_name=unit_names.get(process.unit),
        owner_name=owner_names.get(process.owner), reference=process.reference,
        status=process.status, tags=process.tags,
        outgoing=order(outgoing), incoming=order(incoming), assets=assets, inits=inits,
    )
