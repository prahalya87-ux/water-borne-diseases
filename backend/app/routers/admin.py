from collections import Counter, defaultdict
from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_admin
from ..models import (AuditLog, ContaminationReport, DiseaseReport, OfficialAlert, ReportStatus, User,
                      WaterQualityTest)
from ..risk import (LIMITATIONS, METHOD, current_input_counts, historical_context, latest_per_locality,
                    run_assessments, to_dict)
from ..water_standards import classify_test

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _risk_response(rows):
    items = []
    last_analysis = None
    for row in rows:
        item = row if isinstance(row, dict) else {
            "id": row.id,
            "locality": row.locality,
            "category": row.category,
            "score": row.score,
            "confidence": row.confidence,
            "factors": row.factors,
            "missing_data": row.missing_data,
            "recommendation": row.recommendation,
            "limitations": row.limitations,
            "is_demo": row.is_demo,
            "analysed_at": row.analysed_at,
            "period_start": row.period_start,
            "period_end": row.period_end,
        }
        items.append(item)
        value = item.get("analysed_at") if isinstance(item, dict) else item.analysed_at
        if value is not None:
            last_analysis = max(last_analysis, value) if last_analysis is not None else value
    return {
        "items": items,
        "method": {
            "name": METHOD["name"],
            "validated": METHOD["validated"],
            "description": METHOD["description"],
            "rules": METHOD["rules"],
            "categories": METHOD["categories"],
        },
        "limitations": LIMITATIONS,
        "disclaimer": "These are screening estimates that help staff decide where to investigate first. They are not diagnoses, probabilities, or confirmed outbreaks, and the method has not been validated against real outbreaks.",
        "last_analysis": last_analysis.isoformat() if hasattr(last_analysis, "isoformat") else last_analysis,
    }


@router.post("/risk/run")
def run_risk_analysis(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    rows = run_assessments(db)
    db.commit()
    response = _risk_response([to_dict(r) for r in rows])
    response["current_inputs"] = current_input_counts(db)
    response["historical_context"] = historical_context(db)
    return response


@router.get("/risk/run")
def get_risk_analysis(db: Session = Depends(get_db)):
    rows = latest_per_locality(db)
    response = _risk_response([to_dict(r) for r in rows])
    response["current_inputs"] = current_input_counts(db)
    response["historical_context"] = historical_context(db)
    return response


@router.get("/dashboard")
def dashboard(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    counts = dict(db.execute(select(ContaminationReport.status, func.count()).group_by(ContaminationReport.status)).all())
    st = {s.value: counts.get(s, 0) for s in ReportStatus}
    total = sum(st.values())
    pending = st["submitted"] + st["under_review"] + st["verification_required"]
    verified = st["verified"] + st["forwarded_to_authority"]
    resolvable = total - st["rejected"]

    by_loc = db.execute(select(ContaminationReport.locality, func.count()).where(
        ContaminationReport.status != ReportStatus.rejected).group_by(ContaminationReport.locality)
        .order_by(func.count().desc()).limit(10)).all()
    escalated = db.scalar(select(func.count()).select_from(ContaminationReport)
                          .where(ContaminationReport.escalated_at.is_not(None)))

    tests = list(db.scalars(select(WaterQualityTest).order_by(WaterQualityTest.tested_at.desc()).limit(100)))
    cls = Counter(classify_test(t)["overall"] for t in tests)
    recent_tests = [{"sample_id": t.sample_id, "locality": t.locality, "tested_at": t.tested_at,
                     "verification_status": t.verification_status, "classification": classify_test(t)["overall"],
                     "is_demo": t.is_demo} for t in tests[:10]]

    since = date.today() - timedelta(days=84)
    weekly = defaultdict(lambda: {"records": 0, "cases": 0})
    by_disease, by_ver = Counter(), Counter()
    for d in db.scalars(select(DiseaseReport).where(DiseaseReport.reported_on >= since)):
        wk = (d.reported_on - timedelta(days=d.reported_on.weekday())).isoformat()
        weekly[wk]["records"] += 1
        weekly[wk]["cases"] += d.cases or 0
        by_disease[d.disease] += d.cases or 0
        by_ver[d.verification_status] += 1

    pend_alerts = list(db.scalars(select(OfficialAlert).where(OfficialAlert.approval_status == "pending_approval")
                                  .order_by(OfficialAlert.created_at.desc())))
    return {
        "reports": {"total": total, "pending_review": pending, "verified": verified,
                    "escalated": escalated or 0, "by_status": st},
        "resolution": {"resolved": st["resolved"], "open": total - st["resolved"] - st["rejected"],
                       "rejected": st["rejected"],
                       "resolution_rate": round(st["resolved"] / resolvable, 3) if resolvable else None},
        "reports_by_location": [{"locality": loc, "count": n} for loc, n in by_loc],
        "water_quality": {"recent": recent_tests, "classification_counts": dict(cls),
                          "laboratory_confirmed": sum(1 for t in tests if t.verification_status == "laboratory_confirmed")},
        "disease_trends": {"weeks": [{"week_start": k, **v} for k, v in sorted(weekly.items())],
                           "cases_by_disease": dict(by_disease), "records_by_verification": dict(by_ver)},
        "alerts_awaiting_approval": {"count": len(pend_alerts),
                                     "items": [{"id": a.id, "title": a.title, "locality": a.locality,
                                                "severity": a.severity, "created_at": a.created_at} for a in pend_alerts[:10]]},
        "definitions": {"pending_review": "submitted + under_review + verification_required",
                        "verified": "verified + forwarded_to_authority",
                        "note": "Counts include unverified citizen reports and are not confirmed cases."},
    }


@router.get("/audit-logs")
def audit_logs(limit: int = 100, offset: int = 0, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    limit = max(1, min(limit, 500))
    rows = db.scalars(select(AuditLog).order_by(AuditLog.id.desc()).limit(limit).offset(offset))
    return [{"id": a.id, "actor_id": a.actor_id, "action": a.action, "entity": a.entity,
             "entity_id": a.entity_id, "detail": a.detail, "created_at": a.created_at} for a in rows]