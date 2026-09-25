"""Diagnosis answer validation (specs/005-explore-initiatives R10).

Every active criterion must be answered, with a value of that criterion's own
scale — the integer `list_items.value` rows of `criterias.list` (checked on
`lang='en'`; values are language-independent). Shared by propose, diagnosis
and modify so the three transitions cannot disagree on what "complete" means.
"""
from typing import Dict, List, Set

from sqlmodel import Session, select

from ...admin.internal.models import ListItem
from .models import Criteria, DiagnosisAnswer


def active_criteria(session: Session) -> List[Criteria]:
    return session.exec(
        select(Criteria).where(Criteria.is_active == True)  # noqa: E712
        .order_by(Criteria.code)
    ).all()


def scale_values(session: Session, criteria: List[Criteria]) -> Dict[str, Set[int]]:
    """criteria code → the integer values its scale defines (one query)."""
    lists = {c.list or c.code for c in criteria}
    if not lists:
        return {}
    rows = session.exec(
        select(ListItem.list, ListItem.value).where(
            ListItem.list.in_(lists), ListItem.lang == "en")
    ).all()
    by_list: Dict[str, Set[int]] = {}
    for list_code, value in rows:
        try:
            by_list.setdefault(list_code, set()).add(int(value))
        except (TypeError, ValueError):
            continue  # a non-numeric scale item can never be a valid score
    return {c.code: by_list.get(c.list or c.code, set()) for c in criteria}


def _check(session: Session, scores: Dict[str, int]) -> None:
    criteria = active_criteria(session)
    codes = {c.code for c in criteria}
    unknown = sorted(set(scores) - codes)
    if unknown:
        raise ValueError(f"Unknown or inactive criteria: {', '.join(unknown)}")
    missing = sorted(codes - set(scores))
    if missing:
        raise ValueError(f"Every criterion must be answered; missing: {', '.join(missing)}")
    scales = scale_values(session, criteria)
    for code, score in scores.items():
        if score not in scales.get(code, set()):
            raise ValueError(f"'{score}' is not a valid answer for criterion {code}")


def validate_creator_answers(
    session: Session, answers: Dict[str, DiagnosisAnswer],
) -> Dict[str, DiagnosisAnswer]:
    """Validate the proposer's answers; returns them with blank rationales → None."""
    _check(session, {code: a.score for code, a in answers.items()})
    return {
        code: DiagnosisAnswer(
            score=a.score, rationale=(a.rationale or "").strip() or None)
        for code, a in answers.items()
    }


def validate_reviewer_answers(session: Session, answers: Dict[str, int]) -> Dict[str, int]:
    """Validate the reviewer's scores (no rationale — feedback goes on the collaboration)."""
    _check(session, dict(answers))
    return dict(answers)
