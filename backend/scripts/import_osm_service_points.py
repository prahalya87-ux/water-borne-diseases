"""Import REAL public drinking-water points and water-treatment works from OpenStreetMap (needs internet).
    python -m scripts.import_osm_service_points --city "Bengaluru"
    python -m scripts.import_osm_service_points --bbox 12.83,77.45,13.14,77.76
OSM has no reliable tag for water-TESTING labs or municipal complaint desks: add those through the admin
endpoint POST /api/admin/service-points (e.g. NABL-accredited labs, your municipal corporation's helpline),
only from official sources. Data (c) OpenStreetMap contributors, ODbL."""
import argparse
import sys

import httpx

from app.database import Base, SessionLocal, engine
from app.models import ServicePoint

OVERPASS = "https://overpass-api.de/api/interpreter"
KINDS = {"public_water_point": '["amenity"="drinking_water"]', "purification_facility": '["man_made"="water_works"]'}


def query(kind_filter: str, city: str | None, bbox: str | None) -> str:
    if city:
        if '"' in city or "\\" in city:
            raise SystemExit("Invalid city name")
        return f'[out:json][timeout:90];area["name"="{city}"]["boundary"="administrative"]->.a;nwr{kind_filter}(area.a);out center tags;'
    s, w, n, e = [float(x) for x in bbox.split(",")]
    return f"[out:json][timeout:90];nwr{kind_filter}({s},{w},{n},{e});out center tags;"


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--city")
    g.add_argument("--bbox")
    a = ap.parse_args()
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        have = {s for (s,) in db.query(ServicePoint.source).all()}
        added = 0
        for category, flt in KINDS.items():
            try:
                r = httpx.post(OVERPASS, data={"data": query(flt, a.city, a.bbox)}, timeout=120,
                               headers={"User-Agent": "WaterGuardAI-college-project/0.1"})
                r.raise_for_status()
            except httpx.HTTPError as e:
                sys.exit(f"Overpass request failed ({e}). Retry in a minute or use a smaller --bbox.")
            for el in r.json().get("elements", []):
                t = el.get("tags", {})
                lat = el.get("lat") or (el.get("center") or {}).get("lat")
                lon = el.get("lon") or (el.get("center") or {}).get("lon")
                src = f"OpenStreetMap contributors (ODbL) - {el['type']}/{el['id']}"
                if lat is None or lon is None or src in have:
                    continue
                name = t.get("name") or ("Public drinking water point" if category == "public_water_point" else "Water works")
                db.add(ServicePoint(category=category, name=name[:200], address=None,
                                    opening_hours=(t.get("opening_hours") or None) and t["opening_hours"][:200],
                                    latitude=float(lat), longitude=float(lon), source=src, last_verified_on=None))
                have.add(src); added += 1
        db.commit()
        print(f"Imported {added} service points from OpenStreetMap.")
    finally:
        db.close()


if __name__ == "__main__":
    main()