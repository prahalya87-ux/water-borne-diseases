from datetime import date, datetime, timezone

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.database import Base, SessionLocal, engine
from app.deps import reset_rate_limits
from app.main import app
from app.models import DiseaseReport, HealthcareFacility, WaterQualityTest
from scripts.import_real_incidents import import_incidents

client = TestClient(app)


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    reset_rate_limits()
    yield


def test_real_incidents_import_is_sourced_unverified_and_idempotent():
    db = SessionLocal()
    first = import_incidents(db)
    second = import_incidents(db)
    rows = db.query(DiseaseReport).all()
    db.close()
    assert first == 4 and second == 0
    assert all(r.verification_status == "media_reported" and r.source_url and not r.is_demo for r in rows)
    reports = client.get("/api/disease-reports").json()
    incident = next(row for row in reports if row["verification_status"] == "media_reported")
    assert incident["source_url"].startswith("https://")
    assert incident["notes"]


def test_markers_alert_flags_directions_and_labels():
    db = SessionLocal()
    import_incidents(db)
    db.add(HealthcareFacility(name="H1", facility_type="hospital", latitude=22.72, longitude=75.86,
                              source="OpenStreetMap contributors (ODbL) - node/1"))
    db.add(WaterQualityTest(sample_id="S1", locality="Indore", latitude=22.72, longitude=75.86,
                            tested_at=datetime.now(timezone.utc), organization="Lab", ecoli_result="present",
                            verification_status="laboratory_confirmed"))
    db.commit(); db.close()
    r = client.get("/api/map/markers", params={"lat": 22.7196, "lon": 75.8577, "radius_km": 10}).json()
    by_cat = {m["category"]: m for m in r["markers"]}
    assert by_cat["reported_incident"]["alert"] is True
    assert "not verified" in by_cat["reported_incident"]["verification_label"].lower()
    assert by_cat["reported_incident"]["source_url"].startswith("https://")
    assert by_cat["reported_incident"]["notes"]
    assert by_cat["healthcare_facility"]["alert"] is False
    assert by_cat["healthcare_facility"]["directions_url"].startswith("https://www.google.com/maps/dir/?api=1&destination=22.72,75.86")
    assert "origin=22.7196,75.8577" in by_cat["healthcare_facility"]["directions_url"]
    assert by_cat["water_testing_location"]["alert"] is True
    assert r["contains_demo_data"] is False
    assert "confirmed_outbreak" in r["legend"]


def test_markers_radius_excludes_far_incidents():
    db = SessionLocal(); import_incidents(db); db.close()
    r = client.get("/api/map/markers", params={"lat": 22.7196, "lon": 75.8577, "radius_km": 10}).json()
    assert [m["locality"] for m in r["markers"]] == ["Bhagirathpura, Indore"]


def test_citizen_report_marker_is_rounded_and_hides_contact():
    body = {"category": "sewage_mixing", "description": "Sewage visible mixing near the tap",
            "locality": "Kurla", "latitude": 19.07261, "longitude": 72.88451, "contact_info": "me@example.com",
            "observed_at": "2026-10-20T10:00:00Z", "consent_given": True}
    assert client.post("/api/reports", json=body).status_code == 201
    m = [x for x in client.get("/api/map/markers").json()["markers"] if x["category"] == "water_contamination_report"][0]
    assert (m["latitude"], m["longitude"]) == (19.073, 72.885)
    assert "me@example.com" not in str(m) and m["verification_label"] == "Unverified citizen report"


def test_facility_nearby_has_directions_link(monkeypatch):
    monkeypatch.setattr("app.routers.facilities._osm_live_nearby", lambda *args, **kwargs: [])
    monkeypatch.setattr("app.routers.facilities._photon_live_nearby", lambda *args, **kwargs: [])
    db = SessionLocal()
    db.add(HealthcareFacility(name="H1", facility_type="hospital", latitude=19.075, longitude=72.88, source="t"))
    db.commit(); db.close()
    f = client.get("/api/facilities/nearby", params={"lat": 19.0726, "lon": 72.8845}).json()[0]
    assert "destination=19.075,72.88" in f["directions_url"] and "origin=19.0726,72.8845" in f["directions_url"]


def test_nearby_endpoint_returns_photon_hospital_names_and_directions(monkeypatch):
    from app.routers import facilities

    def photon_results(lat, lon, _radius_km, _limit):
        return [{
            "id": "photon:node:42",
            "name": "Nearby General Hospital",
            "facility_type": "hospital",
            "address": None,
            "phone": None,
            "opening_hours": None,
            "latitude": 19.075,
            "longitude": 72.88,
            "source": "OpenStreetMap contributors (ODbL) via Photon - node/42",
            "last_verified_on": None,
            "is_demo": False,
            "distance_km": 0.4,
            "beds": None,
            "directions_url": facilities.directions_url(19.075, 72.88, lat, lon),
        }]

    monkeypatch.setattr(facilities, "_photon_live_nearby", photon_results)
    monkeypatch.setattr(
        facilities, "_osm_live_nearby",
        lambda *_args, **_kwargs: pytest.fail("Overpass should not be needed when Photon returns hospitals"),
    )

    response = client.get("/api/facilities/nearby", params={"lat": 19.0726, "lon": 72.8845})

    assert response.status_code == 200
    result = response.json()[0]
    assert result["name"] == "Nearby General Hospital"
    assert "destination=19.075,72.88" in result["directions_url"]
    assert "origin=19.0726,72.8845" in result["directions_url"]


def test_nearby_returns_saved_results_when_live_source_is_unavailable(monkeypatch):
    def unavailable(*_args, **_kwargs):
        raise HTTPException(status_code=503, detail="Live hospital data is temporarily unavailable.")

    monkeypatch.setattr("app.routers.facilities._osm_live_nearby", unavailable)
    monkeypatch.setattr("app.routers.facilities._photon_live_nearby", unavailable)
    db = SessionLocal()
    db.add(HealthcareFacility(name="Saved Hospital", facility_type="hospital", latitude=19.075,
                              longitude=72.88, source="OpenStreetMap contributors (ODbL) - node/2"))
    db.commit()
    db.close()

    response = client.get("/api/facilities/nearby", params={"lat": 19.0726, "lon": 72.8845})

    assert response.status_code == 200
    assert [facility["name"] for facility in response.json()] == ["Saved Hospital"]


def test_nearby_reports_live_source_unavailable_without_saved_results(monkeypatch):
    def unavailable(*_args, **_kwargs):
        raise HTTPException(status_code=503, detail="Live hospital data is temporarily unavailable.")

    monkeypatch.setattr("app.routers.facilities._osm_live_nearby", unavailable)
    monkeypatch.setattr("app.routers.facilities._photon_live_nearby", unavailable)

    response = client.get("/api/facilities/nearby", params={"lat": 19.0726, "lon": 72.8845})

    assert response.status_code == 503
    assert "temporarily unavailable" in response.json()["error"]


def test_live_hospital_search_excludes_specialist_clinics(monkeypatch):
    from app.routers import facilities

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"elements": [
                {"type": "node", "id": 1, "lat": 19.075, "lon": 72.88,
                 "tags": {"name": "City General Hospital", "amenity": "hospital", "beds": "250"}},
                {"type": "node", "id": 2, "lat": 19.075, "lon": 72.88,
                 "tags": {"name": "Dental Hospital", "amenity": "hospital"}},
                {"type": "node", "id": 3, "lat": 19.075, "lon": 72.88,
                 "tags": {"name": "Local Clinic", "amenity": "clinic"}},
            ]}

    monkeypatch.setattr(facilities.httpx, "post", lambda *args, **kwargs: Response())
    rows = facilities._osm_live_nearby(19.0726, 72.8845, radius_km=10, limit=10)
    assert [row["name"] for row in rows] == ["City General Hospital"]
    assert rows[0]["beds"] == 250


def test_live_hospital_search_uses_longitude_adjusted_bbox(monkeypatch):
    from app.routers import facilities

    queries = []

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"elements": [
                {"type": "node", "id": 10, "lat": 60, "lon": 0.25,
                 "tags": {"name": "Nearby Hospital", "amenity": "hospital"}},
                {"type": "node", "id": 11, "lat": 60, "lon": 0.4,
                 "tags": {"name": "Distant Hospital", "amenity": "hospital"}},
            ]}

    def post(_endpoint, data, **_kwargs):
        queries.append(data["data"])
        return Response()

    monkeypatch.setattr(facilities.httpx, "post", post)
    rows = facilities._osm_live_nearby(60, 0, radius_km=15, limit=10)

    assert [row["name"] for row in rows] == ["Nearby Hospital"]
    assert "-0.270" in queries[0] and "0.270" in queries[0]


def test_live_hospital_search_retries_unusable_response(monkeypatch):
    from app.routers import facilities

    endpoints = []

    class Response:
        def __init__(self, payload):
            self.payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self.payload

    def post(endpoint, **_kwargs):
        endpoints.append(endpoint)
        if len(endpoints) == 1:
            return Response([])
        return Response({"elements": [
            {"type": "node", "id": 12, "lat": 19.075, "lon": 72.88,
             "tags": {"name": "Fallback Hospital", "amenity": "hospital"}},
        ]})

    monkeypatch.setattr(facilities, "OVERPASS_ENDPOINTS", ("unusable", "available"))
    monkeypatch.setattr(facilities.httpx, "post", post)
    rows = facilities._osm_live_nearby(19.0726, 72.8845, radius_km=10, limit=10)

    assert endpoints == ["unusable", "available"]
    assert [row["name"] for row in rows] == ["Fallback Hospital"]


def test_photon_hospital_search_returns_named_results_with_google_directions(monkeypatch):
    from app.routers import facilities

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"features": [
                {"type": "Feature", "properties": {
                    "osm_type": "W", "osm_id": 101, "osm_key": "amenity", "osm_value": "hospital",
                    "name": "City General Hospital", "street": "Main Road", "city": "Example City",
                }, "geometry": {"type": "Point", "coordinates": [20.13, 10.13]}},
                {"type": "Feature", "properties": {
                    "osm_type": "N", "osm_id": 102, "osm_key": "amenity", "osm_value": "hospital",
                    "name": "hospital",
                }, "geometry": {"type": "Point", "coordinates": [20.131, 10.131]}},
                {"type": "Feature", "properties": {
                    "osm_type": "N", "osm_id": 103, "osm_key": "amenity", "osm_value": "hospital",
                    "name": "Dental Hospital",
                }, "geometry": {"type": "Point", "coordinates": [20.132, 10.132]}},
                {"type": "Feature", "properties": {
                    "osm_type": "N", "osm_id": 104, "osm_key": "highway", "osm_value": "bus_stop",
                    "name": "Hospital Bus Stop",
                }, "geometry": {"type": "Point", "coordinates": [20.133, 10.133]}},
            ]}

    monkeypatch.setattr(facilities.httpx, "get", lambda *args, **kwargs: Response())
    facilities._photon_cache.pop((10.123, 20.123), None)

    rows = facilities._photon_live_nearby(10.1234, 20.1234, radius_km=5, limit=10)

    assert [row["name"] for row in rows] == ["City General Hospital"]
    assert rows[0]["address"] == "Main Road, Example City"
    assert rows[0]["source"].startswith("OpenStreetMap contributors")
    assert "destination=10.13,20.13" in rows[0]["directions_url"]
    assert "origin=10.1234,20.1234" in rows[0]["directions_url"]