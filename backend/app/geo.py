"""Nearby search. Uses PostGIS (ST_DWithin on geography) when running on PostgreSQL with the
extension installed; otherwise a bounding-box prefilter + haversine distance (works on SQLite)."""
import math

from sqlalchemy import select, text
from sqlalchemy.orm import Session


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371.0088 * math.asin(math.sqrt(a))


def _bbox(model, lat, lon, radius_km):
    deg = radius_km / 111.0
    cos = max(math.cos(math.radians(lat)), 0.01)
    return [model.latitude.between(lat - deg, lat + deg), model.longitude.between(lon - deg / cos, lon + deg / cos)]


def nearby(db: Session, model, lat: float, lon: float, radius_km: float = 10, limit: int = 50, filters=()):
    """Returns [(row, distance_km)] sorted by distance, within radius_km."""
    rows = None
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        try:
            postgis = text(
                "ST_DWithin(ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)::geography, "
                "ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography, :metres)"
            ).bindparams(lon=lon, lat=lat, metres=radius_km * 1000)
            rows = db.scalars(select(model).where(postgis, *filters)).all()
        except Exception:  # PostGIS not installed -> fall back
            db.rollback()
            rows = None
    if rows is None:
        rows = db.scalars(select(model).where(*_bbox(model, lat, lon, radius_km), *filters)).all()
    out = [(r, haversine_km(lat, lon, r.latitude, r.longitude)) for r in rows]
    out = [(r, d) for r, d in out if d <= radius_km]
    out.sort(key=lambda x: x[1])
    return out[:limit]