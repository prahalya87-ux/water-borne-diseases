"""Transparent, rule-based risk screening. NOT a trained or validated model and NOT a probability.
It ranks places for further public-health investigation using the data WaterGuard holds. It never confirms an outbreak."""
import json
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import ContaminationReport, DiseaseReport, ReportStatus, RiskAssessment, WaterQualityTest
from .water_standards import classify_test

METHOD = {
    "name": "rule_based_v1", "validated": False,
    "description": ("Adds points for each risk signal found for a locality. Windows: citizen reports 14 days, water tests 30 days, "
                    "disease records 28 days (compared with the 28 days before), including source-reported records when recent. Synthetic/demo records are excluded. Score is a ranking aid, not a probability."),
    "rules": [
        {"factor": "Citizen reports (unverified unless reviewed)", "points": "1 per report, max 4"},
        {"factor": "Reviewer-verified reports", "points": "2 each, max 4"},
        {"factor": "Escalation rule triggered", "points": "2"},
        {"factor": "E. coli detected in a water test", "points": "4"},
        {"factor": "Other water-test values outside guidelines", "points": "1"},
        {"factor": "Disease cases: 1-9 / 10-49 / 50+", "points": "1 / 2 / 3"},
        {"factor": "Disease reports with unspecified case counts", "points": "1 per report, max 2"},
        {"factor": "Disease cases rising 50%+ vs previous 28 days (at least 5 cases)", "points": "1"},
    ],
    "categories": "8+ high, 4-7 moderate, 1-3 low, otherwise insufficient data (fewer than 3 data points and no strong signal)",
}
LIMITATIONS = ("Rule-based screening, not validated against real outbreak outcomes. Citizen reports and media-reported disease records may be unverified. Rainfall, flooding and "
               "population data are not used. Disease data may be delayed or incomplete. This is not a diagnosis and does not confirm an outbreak.")
RECOMMEND = {
    "high": "Prioritise field inspection and laboratory water testing; review reports; consider a public advisory only after verification.",
    "moderate": "Collect water samples, follow up open reports, and re-run the analysis after new data arrives.",
    "low": "Continue routine monitoring. Low does not mean safe.",
    "insufficient_data": "Collect more data (water tests, verified reports) before drawing conclusions.",
}


def _cases(d: DiseaseReport) -> int:
    return d.cases or 0


def run_assessments(db: Session) -> list[RiskAssessment]:
    now, today = datetime.now(timezone.utc), date.today()
    groups = defaultdict(lambda: {"name": None, "reports": [], "tests": [], "cur": [], "prev": []})
    rq = select(ContaminationReport).where(ContaminationReport.is_demo.is_(False),
                                           ContaminationReport.status != ReportStatus.rejected,
                                           ContaminationReport.observed_at >= now - timedelta(days=14))
    for r in db.scalars(rq):
        g = groups[r.locality.strip().lower()]; g["name"] = g["name"] or r.locality; g["reports"].append(r)
    for t in db.scalars(select(WaterQualityTest).where(
        WaterQualityTest.is_demo.is_(False), WaterQualityTest.tested_at >= now - timedelta(days=30)
    )):
        g = groups[t.locality.strip().lower()]; g["name"] = g["name"] or t.locality; g["tests"].append(t)
    for d in db.scalars(select(DiseaseReport).where(
        DiseaseReport.is_demo.is_(False), DiseaseReport.reported_on >= today - timedelta(days=56)
    )):
        g = groups[d.locality.strip().lower()]; g["name"] = g["name"] or d.locality
        g["cur" if d.reported_on >= today - timedelta(days=28) else "prev"].append(d)

    out = []
    for g in groups.values():
        factors, score = [], 0

        def add(label, pts, detail):
            nonlocal score
            factors.append({"factor": label, "points": pts, "detail": detail}); score += pts

        reports, tests = g["reports"], g["tests"]
        if reports:
            add("Citizen reports (last 14 days)", min(len(reports), 4), f"{len(reports)} report(s); unverified unless reviewed")
        rev = sum(1 for r in reports if r.status in (ReportStatus.verified, ReportStatus.forwarded))
        if rev:
            add("Reviewer-verified reports", min(rev, 2) * 2, f"{rev} verified")
        if any(r.escalated_at for r in reports):
            add("Escalation rule triggered", 2, "e.g. illness cluster or several reports close together")
        ecoli = sum(1 for t in tests if t.ecoli_result == "present")
        if ecoli:
            add("E. coli detected in water tests (last 30 days)", 4, f"{ecoli} test(s)")
        bad = sum(1 for t in tests if t.ecoli_result != "present" and classify_test(t)["overall"] in ("caution", "action_required"))
        if bad:
            add("Other test values outside guidelines", 1, f"{bad} test(s)")
        cur, prev = sum(_cases(d) for d in g["cur"]), sum(_cases(d) for d in g["prev"])
        if cur:
            add("Disease records (last 28 days)", 3 if cur >= 50 else 2 if cur >= 10 else 1, f"{cur} case(s) recorded (reporting may be delayed)")
        unspecified = sum(1 for d in g["cur"] if d.cases is None)
        if unspecified:
            add("Disease reports with unspecified case counts", min(unspecified, 2),
                f"{unspecified} report(s); case count not stated")
        if cur >= 5 and cur >= 1.5 * prev:
            add("Rising trend vs previous 28 days", 1, f"{cur} vs {prev}")

        points = len(reports) + len(tests) + len(g["cur"]) + len(g["prev"])
        strong = bool(ecoli or rev or any(r.escalated_at for r in reports))
        category = "insufficient_data" if (points < 3 and not strong) else "high" if score >= 8 else "moderate" if score >= 4 else "low"
        lab = any(t.verification_status == "laboratory_confirmed" for t in tests)
        confidence = "high" if points >= 10 and (lab or rev) else "medium" if points >= 5 else "low"
        missing = ["Rainfall and flood data are not integrated", "Population data is not used"]
        if not tests: missing.append("No water tests in the last 30 days")
        if not g["cur"] and not g["prev"]: missing.append("No disease records in the last 8 weeks")
        if not reports: missing.append("No citizen reports in the last 14 days")
        a = RiskAssessment(
            locality=g["name"], category=category, score=None if category == "insufficient_data" else float(score),
            factors_json=json.dumps({"factors": factors, "missing_data": missing, "recommendation": RECOMMEND[category]}),
            period_start=today - timedelta(days=28), period_end=today, confidence=confidence, limitations=LIMITATIONS,
            method=METHOD["name"], is_demo=False)
        db.add(a); out.append(a)
    db.flush()
    return out


def to_dict(a: RiskAssessment) -> dict:
    extra = json.loads(a.factors_json or "{}")
    return {"id": a.id, "locality": a.locality, "category": a.category, "score": a.score, "confidence": a.confidence,
            "factors": extra.get("factors", []), "missing_data": extra.get("missing_data", []),
            "recommendation": extra.get("recommendation", ""), "limitations": a.limitations, "method": a.method,
            "is_demo": a.is_demo, "analysed_at": a.analysed_at, "period_start": a.period_start, "period_end": a.period_end}


def latest_per_locality(db: Session) -> list[RiskAssessment]:
    seen, out = set(), []
    for a in db.scalars(select(RiskAssessment).where(
        RiskAssessment.is_demo.is_(False)
    ).order_by(RiskAssessment.analysed_at.desc())):
        k = a.locality.strip().lower()
        if k not in seen:
            seen.add(k); out.append(a)
    return out


def current_input_counts(db: Session) -> dict[str, int]:
    now, today = datetime.now(timezone.utc), date.today()
    return {
        "citizen_reports_14d": db.scalar(
            select(func.count()).select_from(ContaminationReport).where(
                ContaminationReport.is_demo.is_(False),
                ContaminationReport.status != ReportStatus.rejected,
                ContaminationReport.observed_at >= now - timedelta(days=14),
            )
        ) or 0,
        "water_tests_30d": db.scalar(
            select(func.count()).select_from(WaterQualityTest).where(
                WaterQualityTest.is_demo.is_(False),
                WaterQualityTest.tested_at >= now - timedelta(days=30),
            )
        ) or 0,
        "disease_reports_56d": db.scalar(
            select(func.count()).select_from(DiseaseReport).where(
                DiseaseReport.is_demo.is_(False),
                DiseaseReport.reported_on >= today - timedelta(days=56),
            )
        ) or 0,
    }


def historical_context(db: Session) -> dict[str, int]:
    return {
        "source_reported_incidents_on_file": db.scalar(
            select(func.count()).select_from(DiseaseReport).where(
                DiseaseReport.is_demo.is_(False),
                DiseaseReport.verification_status == "media_reported",
                DiseaseReport.source_url.is_not(None),
            )
        ) or 0,
        "disease_record_window_days": 56,
    }