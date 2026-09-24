"""Diagnosis Questions read model (Initiative Management).

One row per diagnosis criterion — every active criterion, plus any inactive
criterion the initiative already has an answer for (so a deactivated question
never silently rewrites a past diagnosis) — with the proposer's and reviewer's
answers resolved to labels of that criterion's own scale (``criterias.list`` →
``list_items``) in the requested language, falling back to English and then to
the raw value. Three queries regardless of criterion count (no N+1).
"""
from typing import Dict, Optional, Tuple

from sqlalchemy import or_
from sqlmodel import Session, select

from .models import Criteria, Diagnostic, DiagnosticRow, DiagnosticsResponse, Initiative
from ...admin.internal.models import ListItem

DEFAULT_LANG = "en"


def get_diagnostics(session: Session, initiative: Initiative, lang: str) -> DiagnosticsResponse:
    diags: Dict[str, Diagnostic] = {
        d.criteria: d
        for d in session.exec(
            select(Diagnostic).where(
                Diagnostic.init == initiative.id,
                Diagnostic.is_active == True,  # noqa: E712
            )
        ).all()
    }

    criteria_rows = session.exec(
        select(Criteria).where(or_(
            Criteria.is_active == True,  # noqa: E712
            Criteria.code.in_(list(diags) or [""]),
        )).order_by(Criteria.created_at, Criteria.code)
    ).all()

    lists = {c.list for c in criteria_rows if c.list}
    langs = {lang, DEFAULT_LANG}
    labels: Dict[Tuple[str, str, str], str] = {}
    if lists:
        for item in session.exec(
            select(ListItem).where(
                ListItem.list.in_(list(lists)),
                ListItem.lang.in_(list(langs)),
            )
        ).all():
            labels[(item.list, item.lang, item.value)] = item.label

    def label(list_code: Optional[str], score: Optional[int]) -> Optional[str]:
        if score is None:
            return None
        value = str(score)
        if list_code:
            for code in (lang, DEFAULT_LANG):
                hit = labels.get((list_code, code, value))
                if hit:
                    return hit
        return value

    items = []
    for c in criteria_rows:
        d = diags.get(c.code)
        items.append(DiagnosticRow(
            criteria=c.code,
            name=c.name,
            description=c.description,
            list=c.list,
            is_active_criteria=c.is_active,
            creator_score=d.creator_score if d else None,
            creator_label=label(c.list, d.creator_score) if d else None,
            reviewer_score=d.reviewer_score if d else None,
            reviewer_label=label(c.list, d.reviewer_score) if d else None,
            rationale=d.rationale if d else None,
        ))

    return DiagnosticsResponse(init=initiative.id, score=initiative.score, items=items)
