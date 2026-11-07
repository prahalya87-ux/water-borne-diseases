from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import audit, require_admin
from ..geo import nearby
from ..models import ServicePoint, User
from .facilities import directions_url

router = APIRouter(tags=["service-points"])
Category = Literal["water_testing_lab", "public_water_point", "purification_facility", "municipal_complaint"]


class ServicePointIn(BaseModel):
    category: Category
    name: str = Field(min_length=2, max_length=200)
    address: str | None = Field(default=None, max_length=300)
    phone: str | None = Field(default=None, max_length=40)
    opening_hours: str | None = Field(default=None, max_length=200)
    website: str | None = Field(default=None, max_length=300)
    coverage_area: str | None = Field(default=None, max_length=200)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    source: str = Field(min_length=2, max_length=200)
    last_verified_on: date | None = None


def _out(p: ServicePoint, d: float | None = None, origin=None) -> dict:
    has_pos = p.latitude is not None and p.longitude is not None
    return {"id": p.id, "category": p.category, "name": p.name, "address": p.address, "phone": p.phone,
            "opening_hours": p.opening_hours, "website": p.website, "coverage_area": p.coverage_area,
            "latitude": p.latitude, "longitude": p.longitude, "source": p.source,
            "last_verified_on": p.last_verified_on, "contact_verified": p.last_verified_on is not None,
            "is_demo": p.is_demo, "distance_km": round(d, 2) if d is not None else None,
            "directions_url": directions_url(p.latitude, p.longitude, *(origin or (None, None))) if has_pos else None,
            "note": "If contact_verified is false, the phone/hours come from the source and have not been verified by WaterGuard. Confirm before relying on them."}


@router.get("/api/service-points")
def list_service_points(category: Category | None = None, lat: float | None = Query(default=None, ge=-90, le=90),
                        lon: float | None = Query(default=None, ge=-180, le=180),
                        radius_km: float = Query(10, gt=0, le=100), limit: int = Query(50, ge=1, le=200),
                        db: Session = Depends(get_db)):
    filters = [ServicePoint.category == category] if category else []
    if lat is None or lon is None:
        rows = db.scalars(select(ServicePoint).where(*filters).order_by(ServicePoint.name).limit(limit))
        return [_out(p) for p in rows]
    found = nearby(db, ServicePoint, lat, lon, radius_km, limit, filters)
    out = [_out(p, d, (lat, lon)) for p, d in found]
    # Services without coordinates (e.g. municipal complaint lines) are listed after nearby results.
    if category in (None, "municipal_complaint"):
        extra = db.scalars(select(ServicePoint).where(ServicePoint.latitude.is_(None),
                                                      ServicePoint.category == "municipal_complaint").limit(limit))
        out += [_out(p) for p in extra]
    return out


@router.post("/api/admin/service-points", status_code=201)
def create_service_point(body: ServicePointIn, actor: User = Depends(require_admin), db: Session = Depends(get_db)):
    if (body.latitude is None) != (body.longitude is None):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Provide both latitude and longitude, or neither")
    p = ServicePoint(**body.model_dump())
    db.add(p)
    db.flush()
    audit(db, actor, "service_point.created", "service_point", p.id, f"{p.category}: {p.name}")
    db.commit()
    db.refresh(p)
    return _out(p)