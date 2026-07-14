import logging

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select

from ..internal.models import (
    BugReport, BugReportCreate, BugReportRead,
    MAX_DESCRIPTION_LENGTH, MAX_ATTACHMENTS, MAX_IMAGE_DATA_URL_LENGTH,
)
from ...internal.dependencies import get_db_session
from ...auth.routes import current_active_user, current_superuser
from ...admin.internal.models import User
from ...mail.service import send_message
from ...core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/support", tags=["support"])


def _validate_caps(payload: BugReportCreate) -> None:
    if len(payload.description) > MAX_DESCRIPTION_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Description must be at most {MAX_DESCRIPTION_LENGTH} characters",
        )
    if payload.screenshot and len(payload.screenshot) > MAX_IMAGE_DATA_URL_LENGTH:
        raise HTTPException(status_code=400, detail="Screenshot is too large")
    if payload.attachments:
        if len(payload.attachments) > MAX_ATTACHMENTS:
            raise HTTPException(
                status_code=400,
                detail=f"At most {MAX_ATTACHMENTS} attachments are allowed",
            )
        for attachment in payload.attachments:
            if len(attachment) > MAX_IMAGE_DATA_URL_LENGTH:
                raise HTTPException(status_code=400, detail="Attachment is too large")


async def _notify_ops(report: BugReport, reporter: User) -> None:
    """Best-effort ops notification — a failed/disabled send must never fail
    the request (mail is send-only and silently logs when SMTP is unset)."""
    try:
        await send_message(
            profile="ops",
            subject=f"New bug report #{report.id}",
            recipients=[settings.ops_email],
            template_name="bug_report.html",
            context={
                "report_id": report.id,
                "reporter": reporter.username,
                "description": report.description,
                "page_url": report.page_url,
            },
        )
    except Exception:  # pragma: no cover - defensive, mail is best-effort
        logger.exception("Failed to send bug report notification email")


@router.post("/reports", response_model=BugReport, status_code=201)
async def create_bug_report(
    payload: BugReportCreate,
    session: Session = Depends(get_db_session),
    current: User = Depends(current_active_user),
) -> BugReport:
    """
    Submit a bug report (description + optional screenshot/attachments).

    - **description**: What went wrong (required)
    - **page_url** / **user_agent**: Context captured client-side
    - **screenshot**: Base64 data-URL of the (optionally annotated) screenshot
    - **attachments**: Up to 3 extra base64 data-URL images
    """
    _validate_caps(payload)

    report = BugReport(
        user_id=current.id,
        description=payload.description,
        page_url=payload.page_url,
        user_agent=payload.user_agent,
        screenshot=payload.screenshot,
        attachments=payload.attachments,
    )
    session.add(report)
    session.commit()
    session.refresh(report)
    logger.info(f"Bug report created: {report.id} by user {current.id}")

    await _notify_ops(report, current)
    return report


@router.get("/reports", response_model=list[BugReportRead])
def list_bug_reports(
    skip: int = 0, limit: int = 100,
    session: Session = Depends(get_db_session),
    _: User = Depends(current_superuser),
) -> list[BugReport]:
    """
    List bug reports (superuser-only), newest first. Excludes the heavy
    screenshot/attachments blobs — fetch a single report for those.

    - **skip** / **limit**: pagination
    """
    return session.exec(
        select(BugReport).where(BugReport.is_active == True)
        .order_by(BugReport.created_at.desc(), BugReport.id.desc())
        .offset(skip).limit(limit)
    ).all()


@router.get("/reports/{id}", response_model=BugReport)
def get_bug_report(
    id: int,
    session: Session = Depends(get_db_session),
    _: User = Depends(current_superuser),
) -> BugReport:
    """Get a single bug report, including its screenshot/attachments (superuser-only)."""
    report = session.get(BugReport, id)
    if not report or not report.is_active:
        raise HTTPException(status_code=404, detail="Bug report not found")
    return report
