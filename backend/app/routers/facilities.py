import math
import threading
import time
from datetime import date

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..geo import haversine_km, nearby
from ..models import HealthcareFacility

router = APIRouter(prefix="/api/facilities", tags=["facilities"])
OVERPASS_ENDPOINTS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
)
PHOTON_ENDPOINT = "https://photon.komoot.io/api/"
PHOTON_CACHE_TTL_SECONDS = 300
_photon_cache: dict[tuple[float, float], tuple[float, list[dict]]] = {}
_photon_cache_lock = threading.Lock()


def directions_url(lat: float, lon: float, origin_lat: float | None = None, origin_lon: float | None = None) -> str:
    """Opens turn-by-turn directions in Google Maps (documented URL format). Origin is optional."""
    url = f"https://www.google.com/maps/dir/?api=1&destination={lat},{lon}&travelmode=driving"
    if origin_lat is not None and origin_lon is not None:
        url += f"&origin={origin_lat},{origin_lon}"
    return url


class FacilityOut(BaseModel):
    id: str
    name: str
    facility_type: str
    address: str | None
    phone: str | None          # None means "not available" - never guessed
    opening_hours: str | None
    contact_verified: bool     # True only if WaterGuard verified it (last_verified_on is set)
    latitude: float
    longitude: float
    source: str
    last_verified_on: date | None
    is_demo: bool
    distance_km: float | None = None
    beds: int | None = None
    directions_url: str
    note: str = ("Contact details appear only if present in the source. Straight-line distance shown; "
                 "confirm with the facility before travelling.")


def _out(f: HealthcareFacility, d: float | None = None, origin: tuple[float, float] | None = None) -> FacilityOut:
    o_lat, o_lon = origin if origin else (None, None)
    return FacilityOut(id=f.id, name=f.name, facility_type=f.facility_type, address=f.address, phone=f.phone, opening_hours=f.opening_hours,
                       contact_verified=f.last_verified_on is not None,
                       latitude=f.latitude, longitude=f.longitude, source=f.source,
                       last_verified_on=f.last_verified_on, is_demo=f.is_demo,
                       distance_km=round(d, 2) if d is not None else None,
                       directions_url=directions_url(f.latitude, f.longitude, o_lat, o_lon))


def _osm_live_nearby(lat: float, lon: float, radius_km: float = 10, limit: int = 20):
    lat_delta = radius_km / 111.0
    lon_delta = radius_km / (111.0 * max(abs(math.cos(math.radians(lat))), 0.01))
    min_lat, max_lat = max(-90, lat - lat_delta), min(90, lat + lat_delta)
    min_lon, max_lon = max(-180, lon - lon_delta), min(180, lon + lon_delta)
    bounds = f"{min_lat},{min_lon},{max_lat},{max_lon}"
    selectors = (
        f'node["name"]["amenity"="hospital"]({bounds});'
        f'way["name"]["amenity"="hospital"]({bounds});'
        f'relation["name"]["amenity"="hospital"]({bounds});'
        f'node["name"]["healthcare"="hospital"]({bounds});'
        f'way["name"]["healthcare"="hospital"]({bounds});'
        f'relation["name"]["healthcare"="hospital"]({bounds});'
    )
    q = f"[out:json][timeout:15];({selectors});out center tags;"
    response = None
    for endpoint in OVERPASS_ENDPOINTS:
        try:
            response = httpx.post(
                endpoint,
                data={"data": q},
                timeout=8,
                headers={"User-Agent": "WaterGuardAI/1.0", "Accept": "application/json"},
            )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict) or not isinstance(payload.get("elements", []), list):
                response = None
                continue
            elements = payload.get("elements", [])
            break
        except (httpx.HTTPError, ValueError):
            response = None
    if response is None:
        raise HTTPException(
            status_code=503,
            detail="Live hospital data is temporarily unavailable. Please try again shortly.",
        )
    out = []
    specialist_terms = (
        "dental", "dentist", "eye hospital", "ophthalm", "piles", "orthopedic",
        "orthopaedic", "fertility", "ivf", "maternity", "women's hospital",
        "cancer hospital", "cardiac", "heart institute", "veterinary", "animal hospital",
        "diagnostic", "physiotherapy",
    )
    for el in elements:
        if not isinstance(el, dict):
            continue
        tags = el.get("tags") or {}
        if not isinstance(tags, dict):
            continue
        name = tags.get("name")
        if not isinstance(name, str) or not name.strip() or not (tags.get("amenity") == "hospital" or tags.get("healthcare") == "hospital"):
            continue
        specialties = " ".join(
            str(tags.get(key, "")) for key in ("healthcare:speciality", "healthcare:specialty", "speciality")
        ).lower()
        if any(term in name.lower() or term in specialties for term in specialist_terms):
            continue
        lat2 = el.get("lat") if "lat" in el else (el.get("center") or {}).get("lat")
        lon2 = el.get("lon") if "lon" in el else (el.get("center") or {}).get("lon")
        if lat2 is None or lon2 is None:
            continue
        try:
            lat2, lon2 = float(lat2), float(lon2)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(lat2) or not math.isfinite(lon2) or not (-90 <= lat2 <= 90 and -180 <= lon2 <= 180):
            continue
        d = haversine_km(lat, lon, lat2, lon2)
        if d > radius_km:
            continue
        address = ", ".join(v for v in [tags.get("addr:housenumber"), tags.get("addr:street"), tags.get("addr:suburb"), tags.get("addr:city"), tags.get("addr:postcode")] if v)
        try:
            beds = int(tags.get("beds") or tags.get("capacity:beds"))
        except (TypeError, ValueError):
            beds = None
        out.append({
            "id": f"osm:{el.get('type')}:{el.get('id')}",
            "name": name[:200],
            "facility_type": "hospital",
            "address": address[:300] if address else None,
            "phone": (tags.get("phone") or tags.get("contact:phone") or None)[:40] if (tags.get("phone") or tags.get("contact:phone")) else None,
            "opening_hours": (tags.get("opening_hours") or None)[:200] if tags.get("opening_hours") else None,
            "latitude": float(lat2),
            "longitude": float(lon2),
            "source": f"OpenStreetMap contributors (ODbL) - {el.get('type')}/{el.get('id')}",
            "last_verified_on": None,
            "is_demo": False,
            "distance_km": round(d, 2),
            "beds": beds,
            "directions_url": directions_url(float(lat2), float(lon2), lat, lon),
        })
    return sorted(out, key=lambda x: (x["distance_km"], x["beds"] is None, -(x["beds"] or 0)))[:limit]


def _photon_live_nearby(lat: float, lon: float, radius_km: float = 10, limit: int = 20):
    cache_key = (round(lat, 3), round(lon, 3))
    now = time.monotonic()
    with _photon_cache_lock:
        cached = _photon_cache.get(cache_key)
        if cached and now - cached[0] < PHOTON_CACHE_TTL_SECONDS:
            features = cached[1]
        else:
            features = None

    if features is None:
        try:
            response = httpx.get(
                PHOTON_ENDPOINT,
                params={
                    "q": "hospital",
                    "lat": lat,
                    "lon": lon,
                    "limit": 50,
                    "osm_tag": "amenity:hospital",
                },
                timeout=8,
                headers={"User-Agent": "WaterGuardAI/1.0", "Accept": "application/json"},
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise HTTPException(
                status_code=503,
                detail="Live hospital data is temporarily unavailable. Please try again shortly.",
            ) from exc
        if not isinstance(payload, dict) or not isinstance(payload.get("features"), list):
            raise HTTPException(
                status_code=503,
                detail="Live hospital data returned an invalid response. Please try again shortly.",
            )
        features = payload["features"]
        with _photon_cache_lock:
            expired = [key for key, value in _photon_cache.items()
                       if now - value[0] >= PHOTON_CACHE_TTL_SECONDS]
            for key in expired:
                _photon_cache.pop(key, None)
            if len(_photon_cache) >= 256:
                _photon_cache.pop(next(iter(_photon_cache)))
            _photon_cache[cache_key] = (now, features)

    out = []
    specialist_terms = (
        "dental", "dentist", "eye hospital", "ophthalm", "piles", "orthopedic",
        "orthopaedic", "fertility", "ivf", "maternity", "women's hospital",
        "cancer hospital", "cardiac", "heart institute", "veterinary", "animal hospital",
        "diagnostic", "physiotherapy",
    )
    for feature in features:
        if not isinstance(feature, dict):
            continue
        properties = feature.get("properties")
        geometry = feature.get("geometry")
        coordinates = geometry.get("coordinates") if isinstance(geometry, dict) else None
        if not isinstance(properties, dict) or not isinstance(coordinates, list) or len(coordinates) < 2:
            continue
        if properties.get("osm_key") != "amenity" or properties.get("osm_value") != "hospital":
            continue
        name = properties.get("name")
        if not isinstance(name, str) or not name.strip() or name.strip().lower() == "hospital":
            continue
        try:
            lon2, lat2 = float(coordinates[0]), float(coordinates[1])
        except (TypeError, ValueError):
            continue
        if not math.isfinite(lat2) or not math.isfinite(lon2) or not (-90 <= lat2 <= 90 and -180 <= lon2 <= 180):
            continue
        distance = haversine_km(lat, lon, lat2, lon2)
        if distance > radius_km or any(term in name.lower() for term in specialist_terms):
            continue

        address = ", ".join(
            str(properties[key]) for key in ("housenumber", "street", "locality", "city", "postcode")
            if properties.get(key)
        )
        osm_type = {"N": "node", "W": "way", "R": "relation"}.get(properties.get("osm_type"), "feature")
        osm_id = properties.get("osm_id")
        out.append({
            "id": f"photon:{osm_type}:{osm_id}",
            "name": name[:200],
            "facility_type": "hospital",
            "address": address[:300] if address else None,
            "phone": None,
            "opening_hours": None,
            "latitude": lat2,
            "longitude": lon2,
            "source": f"OpenStreetMap contributors (ODbL) via Photon - {osm_type}/{osm_id}",
            "last_verified_on": None,
            "is_demo": False,
            "distance_km": round(distance, 2),
            "beds": None,
            "directions_url": directions_url(lat2, lon2, lat, lon),
        })
    return sorted(out, key=lambda item: item["distance_km"])[:limit]


@router.get("", response_model=list[FacilityOut])
def list_facilities(facility_type: str | None = None, limit: int = 50, offset: int = 0, db: Session = Depends(get_db)):
    q = select(HealthcareFacility).order_by(HealthcareFacility.name).limit(max(1, min(limit, 200))).offset(offset)
    if facility_type:
        q = q.where(HealthcareFacility.facility_type == facility_type)
    return [_out(f) for f in db.scalars(q)]


@router.get("/nearby", response_model=list[FacilityOut])
def nearby_facilities(lat: float = Query(ge=-90, le=90), lon: float = Query(ge=-180, le=180),
                      radius_km: float = Query(10, gt=0, le=100), facility_type: str | None = None,
                      limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    filters = [HealthcareFacility.facility_type == facility_type] if facility_type else []
    db_hits = [_out(f, d, (lat, lon)) for f, d in nearby(db, HealthcareFacility, lat, lon, radius_km, limit, filters)]
    live_hits = []
    overpass_tried = False
    try:
        live_results = _photon_live_nearby(lat, lon, radius_km, limit)
    except HTTPException:
        overpass_tried = True
        try:
            live_results = _osm_live_nearby(lat, lon, radius_km, limit)
        except HTTPException:
            if not db_hits:
                raise
            live_results = []
    if not live_results and not overpass_tried:
        overpass_tried = True
        try:
            live_results = _osm_live_nearby(lat, lon, radius_km, limit)
        except HTTPException:
            live_results = []
    for item in live_results:
        live_hits.append(FacilityOut(
            id=item["id"], name=item["name"], facility_type=item["facility_type"], address=item["address"],
            phone=item["phone"], opening_hours=item["opening_hours"], contact_verified=False,
            latitude=item["latitude"], longitude=item["longitude"], source=item["source"],
            last_verified_on=None, is_demo=False, distance_km=item["distance_km"],
            beds=item["beds"],
            directions_url=item["directions_url"], note=("Contact details appear only if present in the source. Straight-line distance shown; "
                                                       "confirm with the facility before travelling.")))
    seen = set()
    combined = []
    for item in db_hits + live_hits:
        key = (item.name, round(item.latitude, 5), round(item.longitude, 5))
        if key in seen:
            continue
        seen.add(key)
        combined.append(item)
    combined.sort(key=lambda x: (x.distance_km if x.distance_km is not None else float("inf"),
                                 x.beds is None, -(x.beds or 0)))
    return combined[:limit]