"""Import REAL hospitals/clinics from OpenStreetMap (Overpass API). Needs internet.
    python -m scripts.import_osm_facilities --city "Bengaluru"
    python -m scripts.import_osm_facilities --bbox 12.83,77.45,13.14,77.76     (south,west,north,east)
Data (c) OpenStreetMap contributors, ODbL. It is community-maintained: phone/address appear only when
someone tagged them, and nothing is invented. last_verified_on stays empty because WaterGuard has not
verified these entries, so the UI must tell users to confirm with the facility.
"""
import argparse
import sys

import httpx

from app.database import Base, SessionLocal, engine
from app.models import HealthcareFacility

OVERPASS = "https://overpass-api.de/api/interpreter"
TYPES = '"amenity"~"^(hospital|clinic)$"'


def build_query(city: str | None, bbox: str | None) -> str:
    if city:
        if '"' in city or "\\" in city:
            raise SystemExit("Invalid city name")
        return (f'[out:json][timeout:90];area["name"="{city}"]["boundary"="administrative"]->.a;'
                f"nwr[{TYPES}](area.a);out center tags;")
    s, w, n, e = [float(x) for x in bbox.split(",")]
    return f"[out:json][timeout:90];nwr[{TYPES}]({s},{w},{n},{e});out center tags;"


def to_facility(el: dict) -> HealthcareFacility | None:
    t = el.get("tags", {})
    name = t.get("name")
    lat = el.get("lat") or (el.get("center") or {}).get("lat")
    lon = el.get("lon") or (el.get("center") or {}).get("lon")
    if not name or lat is None or lon is None:
        return None
    lower = name.lower()
    ftype = "public_health_centre" if ("primary health" in lower or "health cent" in lower or "phc" in lower.split()) \
        else ("clinic" if t.get("amenity") == "clinic" else "hospital")
    parts = [t.get(k) for k in ("addr:housenumber", "addr:street", "addr:suburb", "addr:city", "addr:postcode")]
    address = ", ".join(p for p in parts if p) or None
    return HealthcareFacility(
        name=name[:200], facility_type=ftype, address=address[:300] if address else None,
        phone=(t.get("phone") or t.get("contact:phone") or None) and (t.get("phone") or t.get("contact:phone"))[:40],
        opening_hours=(t.get("opening_hours") or None) and t["opening_hours"][:200],
        latitude=float(lat), longitude=float(lon),
        source=f"OpenStreetMap contributors (ODbL) - {el['type']}/{el['id']}", last_verified_on=None, is_demo=False)


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--city")
    g.add_argument("--bbox")
    ap.add_argument("--limit", type=int, default=2000)
    a = ap.parse_args()
    try:
        r = httpx.post(OVERPASS, data={"data": build_query(a.city, a.bbox)}, timeout=120,
                       headers={"User-Agent": "WaterGuardAI-college-project/0.1"})
        r.raise_for_status()
    except httpx.HTTPError as e:
        sys.exit(f"Overpass request failed ({e}). Check your internet, wait a minute and retry, or use a smaller --bbox.")
    elements = r.json().get("elements", [])[: a.limit]
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        have = {s for (s,) in db.query(HealthcareFacility.source).all()}
        added = 0
        for el in elements:
            f = to_facility(el)
            if f and f.source not in have:
                db.add(f); have.add(f.source); added += 1
        db.commit()
        print(f"Imported {added} facilities from OpenStreetMap ({len(elements)} elements returned).")
    finally:
        db.close()


if __name__ == "__main__":
    main()