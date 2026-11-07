"""Load REAL, sourced waterborne-disease incidents from data/real_incidents.json.
    python -m scripts.import_real_incidents
Each record keeps its source + URL and is stored as 'media_reported' (NOT 'verified'):
WaterGuard has not independently confirmed it. Safe to run repeatedly.
To add more, append to the JSON file. Official sources to check: IDSP outbreak reports, state health
department bulletins, and reputable news. Never add an incident without a source URL.
"""
import json
from datetime import date
from pathlib import Path

from app.database import Base, SessionLocal, engine
from app.models import DiseaseReport

DATA = Path(__file__).resolve().parent.parent / "data" / "real_incidents.json"


def load_incidents() -> list[dict]:
    items = json.loads(DATA.read_text(encoding="utf-8"))
    for i in items:
        if not i.get("source_url"):
            raise ValueError(f"Incident without source_url: {i.get('locality')}")
    return items


def import_incidents(db) -> int:
    added = 0
    for i in load_incidents():
        exists = db.query(DiseaseReport).filter_by(source_url=i["source_url"], locality=i["locality"]).first()
        if exists:
            continue
        db.add(DiseaseReport(
            disease=i["disease"], cases=i.get("cases"), locality=i["locality"], district=i.get("district"),
            latitude=i["latitude"], longitude=i["longitude"], reported_on=date.fromisoformat(i["reported_on"]),
            source=i["source"], source_url=i["source_url"], notes=i.get("notes"),
            verification_status="media_reported", is_demo=False))
        added += 1
    db.commit()
    return added


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    s = SessionLocal()
    try:
        print(f"Added {import_incidents(s)} real incident(s).")
    finally:
        s.close()