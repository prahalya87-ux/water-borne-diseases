import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import ContaminationReport, DiseaseReport, RiskAssessment, WaterQualityTest
from ..risk import LIMITATIONS, METHOD, latest_per_locality, to_dict

router = APIRouter(tags=["observations"])


def _page(limit: int, offset: int):
    return max(1, min(limit, 200)), max(0, offset)


@router.get("/api/disease-reports")
def list_disease_reports(limit: int = 100, offset: int = 0, db: Session = Depends(get_db)):
    limit, offset = _page(limit, offset)
    rows = db.scalars(
        select(DiseaseReport).order_by(DiseaseReport.reported_on.desc()).limit(limit).offset(offset)
    )
    return [
        {
            "id": row.id,
            "disease": row.disease,
            "cases": row.cases,
            "locality": row.locality,
            "district": row.district,
            "latitude": row.latitude,
            "longitude": row.longitude,
            "reported_on": row.reported_on,
            "source": row.source,
            "source_url": row.source_url,
            "notes": row.notes,
            "verification_status": row.verification_status,
            "is_demo": row.is_demo,
        }
        for row in rows
    ]


@router.get("/api/disease-reports/trends")
def disease_report_trends(limit: int = 90, db: Session = Depends(get_db)):
    limit, _ = _page(limit, 0)
    rows = db.execute(
        select(DiseaseReport.reported_on, func.sum(DiseaseReport.cases))
        .group_by(DiseaseReport.reported_on)
        .order_by(DiseaseReport.reported_on.desc())
        .limit(limit)
    )
    return [{"date": day, "count": count} for day, count in reversed(list(rows))]


@router.get("/api/risk/assessments")
def list_risk_assessments(limit: int = 100, offset: int = 0, db: Session = Depends(get_db)):
    rows = latest_per_locality(db)
    items = [to_dict(row) for row in rows]
    last_analysis = max((item["analysed_at"] for item in items), default=None)
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


@router.get("/api/risk-assessments")
def list_risk_assessments_legacy(limit: int = 100, offset: int = 0, db: Session = Depends(get_db)):
    return list_risk_assessments(limit=limit, offset=offset, db=db)
