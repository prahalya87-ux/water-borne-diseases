import pytest
from datetime import date, datetime, timezone
from fastapi.testclient import TestClient

from app.database import Base, SessionLocal, engine
from app.deps import reset_rate_limits
from app.main import app
from app.models import DiseaseReport, HealthcareFacility, RiskAssessment, Role, User, WaterQualityTest
from app.security import create_access_token

client = TestClient(app)
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 32


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    reset_rate_limits()
    yield


def auth(t):
    return {"Authorization": f"Bearer {t}"}


def register(email):
    r = client.post("/api/auth/register", json={"email": email, "full_name": "Test User", "password": "StrongPass1!"})
    assert r.status_code == 201, r.text
    return r.json()["access_token"], r.json()["user"]["id"]


def make_user(email, role):
    _, uid = register(email)
    db = SessionLocal()
    db.get(User, uid).role = role
    db.commit(); db.close()
    return create_access_token(uid, role.value)


def report(token=None, **kw):
    body = {"category": "unusual_odor", "description": "Strong sewage smell from tap water",
            "locality": "Kurla", "observed_at": "2026-10-20T10:00:00Z", "consent_given": True}
    body.update(kw)
    return client.post("/api/reports", json=body, headers=auth(token) if token else {})


def test_reviewers_notified_on_new_report():
    admin = make_user("admin@example.com", Role.administrator)
    code = report().json()["report_code"]
    notes = client.get("/api/notifications", headers=auth(admin)).json()
    assert any(code in n["body"] for n in notes)


def test_reporter_notified_on_status_change():
    admin = make_user("admin@example.com", Role.administrator)
    citizen, _ = register("c@example.com")
    code = report(citizen).json()["report_code"]
    client.patch(f"/api/admin/reports/{code}", json={"status": "verified"}, headers=auth(admin))
    notes = client.get("/api/notifications", headers=auth(citizen)).json()
    assert any("verified" in n["body"] for n in notes)


def test_photo_upload_and_admin_only_access():
    code = report().json()["report_code"]
    up = client.post(f"/api/reports/{code}/evidence", files={"file": ("x.png", PNG, "image/png")})
    assert up.status_code == 201, up.text
    ev_id = up.json()["evidence_id"]
    citizen, _ = register("c@example.com")
    assert client.get(f"/api/admin/evidence/{ev_id}", headers=auth(citizen)).status_code == 403
    assert client.get(f"/api/admin/evidence/{ev_id}").status_code == 401
    admin = make_user("admin@example.com", Role.administrator)
    dl = client.get(f"/api/admin/evidence/{ev_id}", headers=auth(admin))
    assert dl.status_code == 200 and dl.content == PNG


def test_upload_rejects_non_images_even_with_image_extension():
    code = report().json()["report_code"]
    r = client.post(f"/api/reports/{code}/evidence", files={"file": ("evil.png", b"<script>alert(1)</script>", "image/png")})
    assert r.status_code == 415


def test_upload_limit_three_per_report():
    code = report().json()["report_code"]
    codes = [client.post(f"/api/reports/{code}/evidence", files={"file": ("x.png", PNG, "image/png")}).status_code
             for _ in range(4)]
    assert codes == [201, 201, 201, 409]


def test_cannot_upload_to_someone_elses_report():
    owner, _ = register("owner@example.com")
    other, _ = register("other@example.com")
    code = report(owner).json()["report_code"]
    r = client.post(f"/api/reports/{code}/evidence", files={"file": ("x.png", PNG, "image/png")}, headers=auth(other))
    assert r.status_code == 403


def test_subscription_alert_delivers_notification_and_only_admin_can_create():
    sub, _ = register("sub@example.com")
    assert client.post("/api/subscriptions", json={"locality": "Kurla"}, headers=auth(sub)).status_code == 201
    assert client.post("/api/subscriptions", json={"locality": "kurla"}, headers=auth(sub)).status_code == 409
    alert = {"title": "Example advisory", "locality": "Kurla", "severity": "advisory",
             "description": "Water test results indicate elevated contamination.", "recommended_action": "Boil water",
             "source": "Test", "verification_status": "official"}
    assert client.post("/api/admin/alerts", json=alert, headers=auth(sub)).status_code == 403
    admin = make_user("admin@example.com", Role.administrator)
    r = client.post("/api/admin/alerts", json=alert, headers=auth(admin))
    assert r.status_code == 201 and r.json()["is_demo"] is False
    assert len(client.get("/api/notifications", headers=auth(sub)).json()) == 1
    assert len(client.get("/api/alerts").json()) == 1


def test_nearby_facilities_sorted_by_distance_and_no_invented_phone(monkeypatch):
    monkeypatch.setattr("app.routers.facilities._photon_live_nearby", lambda *args, **kwargs: [])
    monkeypatch.setattr("app.routers.facilities._osm_live_nearby", lambda *args, **kwargs: [])
    db = SessionLocal()
    for name, lat in [("Far", 19.20), ("Near", 19.075), ("Mid", 19.10)]:
        db.add(HealthcareFacility(name=name, facility_type="hospital", latitude=lat, longitude=72.88,
                                  source="test", is_demo=False))
    db.commit(); db.close()
    r = client.get("/api/facilities/nearby", params={"lat": 19.0726, "lon": 72.8845, "radius_km": 20})
    assert r.status_code == 200
    names = [f["name"] for f in r.json()]
    assert names == ["Near", "Mid", "Far"]
    assert all(f["phone"] is None for f in r.json())
    small = client.get("/api/facilities/nearby", params={"lat": 19.0726, "lon": 72.8845, "radius_km": 1}).json()
    assert [f["name"] for f in small] == ["Near"]


def test_nearby_validates_coordinates():
    assert client.get("/api/facilities/nearby", params={"lat": 200, "lon": 10}).status_code == 422


def test_observation_read_endpoints_return_existing_model_data():
    db = SessionLocal()
    db.add(DiseaseReport(
        disease="typhoid", cases=3, locality="Kurla", reported_on=date(2026, 10, 20),
        source="test", verification_status="unverified",
    ))
    db.add(WaterQualityTest(
        sample_id="TEST-WQ-1", locality="Kurla", tested_at=datetime(2026, 10, 20, tzinfo=timezone.utc),
        organization="Test lab", ecoli_result="not_tested", verification_status="user_submitted",
    ))
    db.add(RiskAssessment(
        locality="Kurla", category="insufficient_data", score=None, factors_json='["limited samples"]',
        confidence="low", limitations="Insufficient data",
    ))
    db.commit()
    db.close()

    disease = client.get("/api/disease-reports").json()
    assert disease[0]["locality"] == "Kurla"
    assert disease[0]["verification_status"] == "unverified"
    assert client.get("/api/disease-reports/trends").json() == [{"date": "2026-10-20", "count": 3}]
    quality = client.get("/api/water-quality").json()
    assert quality["items"][0]["sample_id"] == "TEST-WQ-1"
    assert quality["items"][0]["verification_status"] == "user_submitted"
    risk = client.get("/api/risk-assessments").json()
    assert risk[0]["factors"] == ["limited samples"]


def test_risk_page_returns_cautious_evidence_summary_without_saved_assessments():
    db = SessionLocal()
    db.add(DiseaseReport(
        disease="typhoid", cases=2, locality="Kurla", reported_on=date(2026, 10, 20),
        source="test", verification_status="unverified",
    ))
    db.commit()
    db.close()

    response = client.get("/api/risk-assessments")
    assert response.status_code == 200
    risk = response.json()[0]
    assert risk["location"] == "Kurla"
    assert risk["risk_category"] == "insufficient_data"
    assert risk["score"] is None
    assert "1 surveillance reports available" in risk["factors"]
    assert risk["method"] == "evidence_summary_no_score"