from datetime import timedelta

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_roles
from app.core.time import today_local
from app.database import get_db
from app.models import ReviewStatus, TaskInstance, TaskStatus, UserRole
from app.schemas.base import CamelModel

router = APIRouter(prefix="/reports", tags=["reports"])

_read_roles = require_roles(UserRole.supervisor, UserRole.admin, UserRole.management)


class WeeklyReport(CamelModel):
    week_start: str
    week_end: str
    approved: int
    overdue: int
    rejected: int
    awaiting_review: int
    critical: int
    rows: list[dict]


@router.get("/weekly", response_model=WeeklyReport)
def weekly_report(db: Session = Depends(get_db), _user=Depends(_read_roles)) -> WeeklyReport:
    return _build_weekly(db)


@router.get("/weekly.pdf")
def weekly_report_pdf(db: Session = Depends(get_db), _user=Depends(_read_roles)) -> Response:
    report = _build_weekly(db)
    body = _pdf_bytes(report)
    return Response(
        content=body,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="weekly-maintenance.pdf"'},
    )


def _build_weekly(db: Session) -> WeeklyReport:
    today = today_local()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    instances = db.query(TaskInstance).all()
    approved = [
        ti
        for ti in instances
        if ti.review_status == ReviewStatus.approved
        and ti.reviewed_at is not None
        and week_start <= ti.reviewed_at.date() <= week_end
    ]
    overdue = [
        ti
        for ti in instances
        if ti.status != TaskStatus.done and ti.review_status != ReviewStatus.awaiting_review and ti.due_date < today
    ]
    rejected = [ti for ti in instances if ti.review_status == ReviewStatus.rejected]
    awaiting = [ti for ti in instances if ti.review_status == ReviewStatus.awaiting_review]
    critical = [ti for ti in awaiting if ti.exception_level.value == "critical"]

    rows: list[dict] = []
    for ti in approved + overdue + rejected + awaiting:
        task_type = ti.task_type
        machine = task_type.machine
        rows.append(
            {
                "machine": machine.name,
                "task": task_type.description,
                "dueDate": str(ti.due_date),
                "reviewStatus": ti.review_status.value,
                "status": ti.status.value,
                "exceptionLevel": ti.exception_level.value,
            }
        )

    return WeeklyReport(
        week_start=str(week_start),
        week_end=str(week_end),
        approved=len(approved),
        overdue=len(overdue),
        rejected=len(rejected),
        awaiting_review=len(awaiting),
        critical=len(critical),
        rows=rows,
    )


def _pdf_bytes(report: WeeklyReport) -> bytes:
    from fpdf import FPDF

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Kuberpack weekly maintenance")
    pdf.ln(10)
    pdf.set_font("Helvetica", size=11)
    pdf.cell(0, 8, f"Week {report.week_start} to {report.week_end}")
    pdf.ln(8)
    pdf.cell(
        0,
        8,
        (
            f"Approved: {report.approved}  Overdue: {report.overdue}  "
            f"Rejected: {report.rejected}  Waiting: {report.awaiting_review}  "
            f"Critical: {report.critical}"
        ),
    )
    pdf.ln(12)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(50, 7, "Machine")
    pdf.cell(70, 7, "Task")
    pdf.cell(30, 7, "Due")
    pdf.cell(40, 7, "Review")
    pdf.ln(7)
    pdf.set_font("Helvetica", size=8)
    for row in report.rows[:80]:
        pdf.cell(50, 6, str(row["machine"])[:28])
        pdf.cell(70, 6, str(row["task"])[:40])
        pdf.cell(30, 6, str(row["dueDate"]))
        pdf.cell(40, 6, str(row["reviewStatus"]))
        pdf.ln(6)
    return bytes(pdf.output())
