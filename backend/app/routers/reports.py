import secrets
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import audit, get_current_user, get_current_user_optional, rate_limit, require_reviewer
from ..escalation import maybe_escalate
from ..models import ContaminationReport, ReportStatus, User
from ..notify import notify_users, reviewer_ids
from ..schemas import AdminReportOut, PublicReportOut, ReportIn, StatusUpdateIn

router = APIRouter(tags=["reports"])


def _new_code(db: Session) -> str:
    while True:
        code = "WG-" + secrets.token_hex(3).upper()
        if not db.scalar(select(ContaminationReport.id).where(ContaminationReport.report_code == code)):
            return code


def _find_duplicate(db: Session, body: ReportIn, locality: str) -> str | None:
    """Same category, within ~500 m (if coordinates given) or same locality, within 24 h."""
    lo, hi = body.observed_at - timedelta(hours=24), body.observed_at + timedelta(hours=24)
    q = select(ContaminationReport).where(
        ContaminationReport.category == body.category,
        ContaminationReport.observed_at >= lo, ContaminationReport.observed_at <= hi,
        ContaminationReport.status != ReportStatus.rejected)
    for r in db.scalars(q):
        if body.latitude is not None and r.latitude is not None:
            if abs(r.latitude - body.latitude) < 0.0045 and abs(r.longitude - body.longitude) < 0.0045:
                return r.report_code
        elif r.locality.strip().lower() == locality.lower():
            return r.report_code
    return None


@router.post("/api/reports", response_model=PublicReportOut, status_code=201,
             dependencies=[Depends(rate_limit(5, 60))])
def submit_report(body: ReportIn, db: Session = Depends(get_db),
                  user: User | None = Depends(get_current_user_optional)):
    if not body.consent_given:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Consent to the privacy notice is required")
    if (body.latitude is None) != (body.longitude is None):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Provide both latitude and longitude, or neither")
    loc_text = (body.locality or "").strip()
    if not (loc_text or body.pin_code or body.latitude is not None):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Provide a location, PIN code, or map position")
    locality = loc_text or (f"PIN {body.pin_code}" if body.pin_code else "Pinned location")
    report = ContaminationReport(
        report_code=_new_code(db), category=body.category, water_source=body.water_source,
        description=(body.description or "").strip(), locality=locality, pin_code=body.pin_code,
        latitude=body.latitude, longitude=body.longitude, observed_at=body.observed_at,
        contact_info=body.contact_info, consent_given=True, reporter_id=user.id if user else None,
        possible_duplicate_of=_find_duplicate(db, body, locality))
    db.add(report)
    db.flush()
    dup = f" (possible duplicate of {report.possible_duplicate_of})" if report.possible_duplicate_of else ""
    notify_users(db, reviewer_ids(db), "New water report to review",
                 f"{report.report_code}: {report.category.replace('_', ' ')} in {report.locality}{dup}. Unverified.",
                 "advisory", f"/admin/reports/{report.report_code}")
    maybe_escalate(db, report)
    db.commit()
    db.refresh(report)
    return report


@router.get("/api/reports/mine", response_model=list[PublicReportOut])
def my_reports(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = select(ContaminationReport).where(ContaminationReport.reporter_id == user.id) \
        .order_by(ContaminationReport.created_at.desc())
    return list(db.scalars(q))


@router.get("/api/reports/{report_code}", response_model=PublicReportOut)
def track_report(report_code: str, db: Session = Depends(get_db)):
    r = db.scalar(select(ContaminationReport).where(ContaminationReport.report_code == report_code.upper()))
    if not r:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report not found")
    return r


# ---- Reviewer / admin endpoints -------------------------------------------------

@router.get("/api/admin/reports", response_model=list[AdminReportOut])
def list_reports(status_filter: ReportStatus | None = None, escalated_only: bool = False, limit: int = 50,
                 offset: int = 0, _: User = Depends(require_reviewer), db: Session = Depends(get_db)):
    limit = max(1, min(limit, 200))
    q = select(ContaminationReport).order_by(ContaminationReport.created_at.desc()).limit(limit).offset(offset)
    if status_filter:
        q = q.where(ContaminationReport.status == status_filter)
    if escalated_only:
        q = q.where(ContaminationReport.escalated_at.is_not(None))
    return list(db.scalars(q))


@router.patch("/api/admin/reports/{report_code}", response_model=AdminReportOut)
def update_status(report_code: str, body: StatusUpdateIn, actor: User = Depends(require_reviewer),
                  db: Session = Depends(get_db)):
    r = db.scalar(select(ContaminationReport).where(ContaminationReport.report_code == report_code.upper()))
    if not r:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report not found")
    if body.status == ReportStatus.rejected and not (body.rejection_reason or "").strip():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "A reason is required when rejecting a report")
    old = r.status
    r.status = body.status
    r.rejection_reason = body.rejection_reason if body.status == ReportStatus.rejected else None
    audit(db, actor, "report.status_changed", "water_contamination_report", r.report_code,
          f"{old.value} -> {body.status.value}")
    if r.reporter_id:
        notify_users(db, [r.reporter_id], f"Update on your report {r.report_code}",
                     f"Status changed to: {body.status.value.replace('_', ' ')}."
                     + (f" Reason: {body.rejection_reason}" if body.status == ReportStatus.rejected else ""),
                     "info", f"/track/{r.report_code}")
    db.commit()
    db.refresh(r)
    return r