from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import audit, rate_limit, require_roles
from ..models import Role, User, WaterQualityTest
from ..water_standards import STANDARDS, build_report_text, classify_test, evaluate

router = APIRouter(tags=["water-quality"])


class CheckIn(BaseModel):
    ph: float | None = Field(default=None, ge=0, le=14)
    turbidity_ntu: float | None = Field(default=None, ge=0, le=1000)
    tds_mg_l: float | None = Field(default=None, ge=0, le=50000)
    residual_chlorine_mg_l: float | None = Field(default=None, ge=0, le=20)
    ecoli: Literal["absent", "present", "not_tested"] | None = None
    source_type: Literal["tap", "borewell", "tank", "river", "other"] | None = None
    from_laboratory_report: bool = False


@router.get("/api/water-quality/standards")
def standards():
    return {"standards": STANDARDS,
            "note": "Limits from BIS IS 10500:2012 and WHO guidance. Check bis.gov.in for newer editions or amendments."}


@router.post("/api/water-quality/check", dependencies=[Depends(rate_limit(30, 60))])
def check(body: CheckIn):
    """Public screening tool. Nothing is stored. Never returns 'safe'."""
    result = evaluate(body.ph, body.turbidity_ntu, body.tds_mg_l, body.residual_chlorine_mg_l, body.ecoli)
    result["report_text"] = build_report_text(result, body.source_type, body.from_laboratory_report)
    result["input_verified"] = False
    return result


class RecordIn(BaseModel):
    sample_id: str = Field(min_length=2, max_length=60)
    locality: str = Field(min_length=2, max_length=160)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    tested_at: datetime
    organization: str = Field(min_length=2, max_length=160)
    ph: float | None = Field(default=None, ge=0, le=14)
    turbidity_ntu: float | None = Field(default=None, ge=0, le=1000)
    tds_mg_l: float | None = Field(default=None, ge=0, le=50000)
    residual_chlorine_mg_l: float | None = Field(default=None, ge=0, le=20)
    ecoli_result: Literal["absent", "present", "not_tested"] = "not_tested"
    verification_status: Literal["laboratory_confirmed", "unverified_sensor"] = "unverified_sensor"


def _item(t: WaterQualityTest) -> dict:
    c = classify_test(t)
    return {"id": t.id, "sample_id": t.sample_id, "locality": t.locality, "latitude": t.latitude,
            "longitude": t.longitude, "tested_at": t.tested_at, "organization": t.organization, "ph": t.ph,
            "turbidity_ntu": t.turbidity_ntu, "tds_mg_l": t.tds_mg_l,
            "residual_chlorine_mg_l": t.residual_chlorine_mg_l, "ecoli_result": t.ecoli_result,
            "verification_status": t.verification_status, "is_demo": t.is_demo,
            "classification": c["overall"], "lab_test_recommended": c["lab_test_recommended"]}


@router.post("/api/water-quality", status_code=201)
def record_test(body: RecordIn, actor: User = Depends(require_roles(Role.administrator, Role.field_inspector)),
                db: Session = Depends(get_db)):
    if db.scalar(select(WaterQualityTest.id).where(WaterQualityTest.sample_id == body.sample_id)):
        raise HTTPException(status.HTTP_409_CONFLICT, "A test with this sample ID already exists")
    if (body.latitude is None) != (body.longitude is None):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Provide both latitude and longitude, or neither")
    t = WaterQualityTest(**body.model_dump(), recorded_by=actor.id)
    db.add(t)
    audit(db, actor, "water_test.recorded", "water_quality_test", body.sample_id, body.verification_status)
    db.commit()
    db.refresh(t)
    return _item(t)


@router.get("/api/water-quality")
def list_tests(locality: str | None = None, limit: int = 50, offset: int = 0, db: Session = Depends(get_db)):
    q = select(WaterQualityTest).order_by(WaterQualityTest.tested_at.desc()).limit(max(1, min(limit, 200))).offset(offset)
    if locality:
        q = q.where(WaterQualityTest.locality.ilike(locality.strip()))
    items = [_item(t) for t in db.scalars(q)]
    has_verified = any(i["verification_status"] == "laboratory_confirmed" for i in items)
    return {"items": items, "message": None if has_verified else "No verified test results available"}