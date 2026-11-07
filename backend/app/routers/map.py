"""One endpoint feeding the map. Every marker says what it is, how trustworthy it is, and whether the
UI should draw it with an ALERT icon (alert=true)."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..geo import nearby
from ..models import ContaminationReport, DiseaseReport, HealthcareFacility, ReportStatus, WaterQualityTest
from .facilities import directions_url

router = APIRouter(prefix="/api/map", tags=["map"])

LEGEND = {
    "confirmed_outbreak": {"label": "Confirmed by an authoritative source", "alert": True},
    "reported_incident": {"label": "Reported by media/officials - not independently verified by WaterGuard", "alert": True},
    "unverified_disease_report": {"label": "Unverified disease report", "alert": True},
    "water_contamination_report": {"label": "Citizen water-contamination report", "alert": True},
    "water_testing_location": {"label": "Water test location (alert if E. coli present)", "alert": False},
    "healthcare_facility": {"label": "Healthcare facility", "alert": False},
}
DISEASE_CATEGORY = {"verified": ("confirmed_outbreak", "Confirmed by authoritative source"),
                    "media_reported": ("reported_incident", "Reported by media/officials; not verified by WaterGuard")}


def _fetch(db, model, lat, lon, radius_km, limit, filters=()):
    if lat is not None and lon is not None:
        return [r for r, _ in nearby(db, model, lat, lon, radius_km, limit, filters)]
    return list(db.scalars(select(model).where(model.latitude.is_not(None), *filters).limit(limit)))


@router.get("/markers")
def markers(lat: float | None = Query(default=None, ge=-90, le=90), lon: float | None = Query(default=None, ge=-180, le=180),
            radius_km: float = Query(25, gt=0, le=200), limit: int = Query(200, ge=1, le=500),
            verified_only: bool = False, db: Session = Depends(get_db)):
    out = []
    for d in _fetch(db, DiseaseReport, lat, lon, radius_km, limit):
        if verified_only and d.verification_status != "verified":
            continue
        cat, label = DISEASE_CATEGORY.get(d.verification_status, ("unverified_disease_report", "Unverified"))
        out.append({"id": d.id, "category": cat, "alert": True, "title": d.disease.replace("_", " ").title(),
                    "locality": d.locality, "latitude": d.latitude, "longitude": d.longitude,
                    "verification_label": label, "date": d.reported_on.isoformat(), "source": d.source,
                    "source_url": d.source_url, "notes": d.notes, "cases": d.cases, "is_demo": d.is_demo})
    rejected = [ReportStatus.rejected]
    for r in _fetch(db, ContaminationReport, lat, lon, radius_km, limit, [ContaminationReport.status.not_in(rejected)]):
        reviewed = r.status in (ReportStatus.verified, ReportStatus.forwarded)
        if verified_only and not reviewed:
            continue
        out.append({"id": r.report_code, "category": "water_contamination_report", "alert": True,
                    "title": r.category.replace("_", " ").title(), "locality": r.locality,
                    # coordinates rounded (~100 m) and no reporter details: privacy by design
                    "latitude": round(r.latitude, 3), "longitude": round(r.longitude, 3),
                    "verification_label": "Verified by reviewer" if reviewed else "Unverified citizen report",
                    "date": r.observed_at.date().isoformat(), "source": "Citizen report", "water_source": r.water_source, "is_demo": r.is_demo})
    for t in _fetch(db, WaterQualityTest, lat, lon, radius_km, limit):
        if verified_only and t.verification_status != "laboratory_confirmed":
            continue
        out.append({"id": t.id, "category": "water_testing_location", "alert": t.ecoli_result == "present",
                    "title": f"Sample {t.sample_id}", "locality": t.locality, "latitude": t.latitude,
                    "longitude": t.longitude, "verification_label": t.verification_status.replace("_", " ").capitalize(),
                    "date": t.tested_at.date().isoformat(), "source": t.organization, "is_demo": t.is_demo})
    for f in _fetch(db, HealthcareFacility, lat, lon, radius_km, limit):
        out.append({"id": f.id, "category": "healthcare_facility", "alert": False, "title": f.name,
                    "locality": f.address, "latitude": f.latitude, "longitude": f.longitude,
                    "verification_label": "Source: " + f.source, "source": f.source, "phone": f.phone,
                    "directions_url": directions_url(f.latitude, f.longitude, lat, lon), "is_demo": f.is_demo})
    return {"markers": out, "legend": LEGEND, "contains_demo_data": any(m["is_demo"] for m in out),
            "note": "Markers are reports, not proof of an outbreak. Unverified items must be shown as unverified."}