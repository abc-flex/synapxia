"""Rules for process links (Process Management, spec FR-013 / FR-013a / FR-013b).

Process → process relations use the dedicated PROCESS_RELATION_TYPE list, whose
values map to BPMN connecting objects so the Value Chain and the Process Map can
draw them (PRECEDES = sequence flow, TRIGGERS = event start, CALLS = call
activity, FEEDS_INTO = data association, INTERACTS_WITH = message flow,
SUPPORTS / GOVERNS = association). Process → asset / initiative links use the
shared RELATION_TYPE list.

Two compatibility rules keep the Value Chain coherent:
- SUPPORTS only from a SUPPORT process to a PRIMARY one;
- PRECEDES only between two processes of the same type.

``RULES`` is the single definition: the services enforce it and
``GET /api/processes/form-options`` publishes it so the UI target picker filters
with the same data instead of re-deriving it.
"""
from typing import Dict, List, Tuple

from sqlmodel import Session, or_, select

from .models import Process, RelatedProcess

PROCESS_RELATION_LIST = "PROCESS_RELATION_TYPE"
ASSET_INIT_RELATION_LIST = "RELATION_TYPE"

SUPPORTS = "SUPPORTS"
PRECEDES = "PRECEDES"
INTERACTS_WITH = "INTERACTS_WITH"

# Relation types without a direction: (A, B) and (B, A) are the same link.
UNDIRECTED = {INTERACTS_WITH}

RULES: Dict[str, Dict] = {
    SUPPORTS: {"source": ["SUPPORT"], "target": ["PRIMARY"]},
    PRECEDES: {"same_type": True},
}


def is_compatible(rel_type: str, source_type: str, target_type: str) -> bool:
    rule = RULES.get(rel_type)
    if not rule:
        return True
    if rule.get("same_type") and source_type != target_type:
        return False
    if "source" in rule and source_type not in rule["source"]:
        return False
    if "target" in rule and target_type not in rule["target"]:
        return False
    return True


def check_compatible(rel_type: str, source_type: str, target_type: str) -> None:
    """ValueError naming the rule when the link would break it."""
    if is_compatible(rel_type, source_type, target_type):
        return
    if rel_type == SUPPORTS:
        raise ValueError(
            f"Supports goes only from a SUPPORT process to a PRIMARY process "
            f"(here {source_type} → {target_type}).")
    raise ValueError(
        f"Precedes links two processes of the same type "
        f"(here {source_type} → {target_type}).")


def pair_key(source: str, target: str, rel_type: str) -> Tuple[str, str, str]:
    """Identity of a link: unordered for undirected types, ordered otherwise."""
    if rel_type in UNDIRECTED:
        a, b = sorted((source, target))
        return (a, b, rel_type)
    return (source, target, rel_type)


def incompatible_links_after_type_change(
    session: Session, code: str, new_type: str
) -> List[RelatedProcess]:
    """Active SUPPORTS / PRECEDES links touching ``code`` (either direction)
    that would break if the process became ``new_type``."""
    rows = session.exec(
        select(RelatedProcess).where(
            RelatedProcess.is_active == True,  # noqa: E712
            RelatedProcess.type.in_(list(RULES)),
            or_(RelatedProcess.source == code, RelatedProcess.target == code),
        )
    ).all()
    if not rows:
        return []
    others = {r.target if r.source == code else r.source for r in rows}
    types = {
        p.code: p.type
        for p in session.exec(select(Process).where(Process.code.in_(list(others)))).all()
    }
    broken = []
    for r in rows:
        source_type = new_type if r.source == code else types.get(r.source, "")
        target_type = new_type if r.target == code else types.get(r.target, "")
        if not is_compatible(r.type, source_type, target_type):
            broken.append(r)
    return broken
