"""Escalation rules. A report is escalated (reviewers + community health workers notified, and a DRAFT
advisory queued for admin approval) when ANY rule matches. Escalation is a prompt to investigate; it never
marks anything verified and never calls anything a confirmed outbreak."""
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import (AuditLog, ContaminationReport, OfficialAlert, ReportStatus, Role, User, WaterQualityTest)
from .notify import notify_users

NEAR_1KM = 0.009   # degrees, ~1 km
NEAR_2KM = 0.018


def escalation_reasons(db: Session, r: ContaminationReport) -> list[str]:
    reasons = []
    if r.category == "suspected_illness_cluster":
        reasons.append("A suspected illness cluster was reported")
    lo, hi = r.observed_at - timedelta(hours=48), r.observed_at + timedelta(hours=48)
    q = select(ContaminationReport).where(ContaminationReport.id != r.id, ContaminationReport.status != ReportStatus.rejected,
                                          ContaminationReport.observed_at >= lo, ContaminationReport.observed_at <= hi)
    near = 0
    for o in db.scalars(q):
        if r.latitude is not None and o.latitude is not None:
            if abs(o.latitude - r.latitude) < NEAR_1KM and abs(o.longitude - r.longitude) < NEAR_1KM:
                near += 1
        elif o.locality.strip().lower() == r.locality.strip().lower():
            near += 1
    if near + 1 >= 3:
        reasons.append(f"{near + 1} reports within about 1 km / the same locality in 48 hours")
    if r.latitude is not None:
        since = r.observed_at - timedelta(days=7)
        pos = db.scalar(select(func.count()).select_from(WaterQualityTest).where(
            WaterQualityTest.ecoli_result == "present", WaterQualityTest.tested_at >= since,
            WaterQualityTest.latitude.between(r.latitude - NEAR_2KM, r.latitude + NEAR_2KM),
            WaterQualityTest.longitude.between(r.longitude - NEAR_2KM, r.longitude + NEAR_2KM)))
        if pos:
            reasons.append("A water test with E. coli present was recorded within about 2 km in the past 7 days")
    return reasons


def maybe_escalate(db: Session, r: ContaminationReport) -> list[str]:
    """Call after the report is flushed. Caller commits."""
    if r.escalated_at:
        return []
    reasons = escalation_reasons(db, r)
    if not reasons:
        return []
    r.escalated_at = datetime.now(timezone.utc)
    r.escalation_reason = "; ".join(reasons)
    roles = [Role.administrator, Role.field_inspector, Role.healthcare_worker]
    ids = list(db.scalars(select(User.id).where(User.role.in_(roles), User.is_active.is_(True))))
    notify_users(db, ids, f"Escalated: potential water-safety concern in {r.locality}",
                 f"{r.escalation_reason}. Report {r.report_code} is UNVERIFIED. Please review; this is not a confirmed outbreak.",
                 "warning", f"/admin/reports/{r.report_code}")
    pending = db.scalar(select(OfficialAlert.id).where(OfficialAlert.locality == r.locality,
                                                       OfficialAlert.approval_status == "pending_approval"))
    if not pending:
        db.add(OfficialAlert(
            title=f"Potential water-safety concern reported in {r.locality} (unverified)", locality=r.locality,
            severity="advisory", description=f"{r.escalation_reason}. Based on unverified citizen reports; not a confirmed outbreak.",
            recommended_action="Field review and laboratory testing recommended. Public advisory only after verification.",
            source="WaterGuard escalation rules", verification_status="unverified_draft",
            approval_status="pending_approval", is_demo=r.is_demo))
    db.add(AuditLog(actor_id=None, action="report.escalated", entity="water_contamination_report",
                    entity_id=r.report_code, detail=r.escalation_reason))
    return reasons