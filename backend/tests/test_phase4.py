from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.database import Base, SessionLocal, engine
from app.deps import reset_rate_limits
from app.main import app
from app.models import Role, User
from app.security import create_access_token

client = TestClient(app)
NOW = "2026-10-20T10:00:00Z"


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    reset_rate_limits()
    yield


def auth(t):
    return {"Authorization": f"Bearer {t}"}


def make_user(email, role=Role.citizen):
    r = client.post("/api/auth/register", json={"email": email, "full_name": "Test User", "password": "StrongPass1!"})
    uid = r.json()["user"]["id"]
    db = SessionLocal()
    db.get(User, uid).role = role
    db.commit(); db.close()
    return create_access_token(uid, role.value)


def report(token=None, **kw):
    body = {"category": "unusual_odor", "water_source": "tap", "description": "Strong smell from the tap water",
            "locality": "Kurla", "observed_at": NOW, "consent_given": True}
    body.update(kw)
    return client.post("/api/reports", json=body, headers=auth(token) if token else {})


# ---------------- Water quality risk checker ----------------

def test_checker_flags_exceedances_and_never_says_safe():
    r = client.post("/api/water-quality/check", json={"ph": 9.2, "turbidity_ntu": 7, "tds_mg_l": 2500,
                                                       "residual_chlorine_mg_l": 0.0, "ecoli": "absent"}).json()
    by = {p["parameter"]: p for p in r["parameters"]}
    assert r["overall"] == "caution"
    assert by["ph"]["status"] == by["turbidity_ntu"]["status"] == by["tds_mg_l"]["status"] == "exceeds_limit"
    assert by["residual_chlorine_mg_l"]["status"] == "below_recommended_minimum"
    assert "safe" not in r["overall"] and r["input_verified"] is False
    assert "BIS" in r["report_text"]


def test_ecoli_present_is_action_required_with_advice_and_lab():
    r = client.post("/api/water-quality/check", json={"ecoli": "present"}).json()
    assert r["overall"] == "action_required" and r["lab_test_recommended"] and r["advice"]


def test_missing_ecoli_always_recommends_lab_test():
    r = client.post("/api/water-quality/check", json={"ph": 7.2, "turbidity_ntu": 0.5, "tds_mg_l": 300}).json()
    assert r["overall"] == "no_exceedance_found" and r["lab_test_recommended"] is True
    assert any("E. coli" in x for x in r["lab_test_reasons"])


def test_all_good_with_ecoli_absent_does_not_force_lab():
    r = client.post("/api/water-quality/check", json={"ph": 7.2, "turbidity_ntu": 0.5, "tds_mg_l": 300,
                                                       "residual_chlorine_mg_l": 0.5, "ecoli": "absent"}).json()
    assert r["overall"] == "no_exceedance_found" and r["lab_test_recommended"] is False


def test_empty_check_and_invalid_values():
    assert client.post("/api/water-quality/check", json={}).json()["overall"] == "insufficient_data"
    assert client.post("/api/water-quality/check", json={"ph": 20}).status_code == 422
    assert client.get("/api/water-quality/standards").json()["standards"][0]["source"].startswith("BIS")


def test_record_test_roles_duplicates_and_no_verified_message():
    body = {"sample_id": "S-1", "locality": "Kurla", "tested_at": NOW, "organization": "Lab A", "ph": 7.1,
            "ecoli_result": "absent", "verification_status": "laboratory_confirmed"}
    citizen = make_user("c@example.com")
    assert client.post("/api/water-quality", json=body, headers=auth(citizen)).status_code == 403
    assert client.get("/api/water-quality").json()["message"] == "No verified test results available"
    insp = make_user("i@example.com", Role.field_inspector)
    assert client.post("/api/water-quality", json=body, headers=auth(insp)).status_code == 201
    assert client.post("/api/water-quality", json=body, headers=auth(insp)).status_code == 409
    assert client.get("/api/water-quality").json()["message"] is None


# ---------------- Report form ----------------

def test_report_with_pin_only_optional_description_and_validation():
    r = report(locality=None, pin_code="560001", description=None)
    assert r.status_code == 201 and r.json()["locality"] == "PIN 560001" and r.json()["water_source"] == "tap"
    assert report(locality=None).status_code == 422                       # no location at all
    assert report(pin_code="12345").status_code == 422                   # invalid PIN
    assert report(water_source="ocean").status_code == 422
    assert report(category="visible_contamination", water_source="river").status_code == 201


# ---------------- Escalation + alert approval ----------------

def test_illness_cluster_escalates_notifies_staff_and_queues_private_draft():
    admin = make_user("admin@example.com", Role.administrator)
    chw = make_user("chw@example.com", Role.healthcare_worker)
    code = report(category="suspected_illness_cluster").json()["report_code"]
    n = client.get("/api/notifications", headers=auth(chw)).json()
    assert any("Escalated" in x["title"] for x in n)
    pend = client.get("/api/admin/alerts/pending", headers=auth(admin)).json()
    assert len(pend) == 1 and pend[0]["verification_status"] == "unverified_draft"
    assert "not a confirmed outbreak" in pend[0]["description"]
    assert client.get("/api/alerts").json() == []                         # drafts are never public
    flagged = client.get("/api/admin/reports", params={"escalated_only": True}, headers=auth(admin)).json()
    assert [x["report_code"] for x in flagged] == [code]


def test_three_reports_same_locality_escalate():
    admin = make_user("admin@example.com", Role.administrator)
    for _ in range(2):
        report()
    assert client.get("/api/admin/alerts/pending", headers=auth(admin)).json() == []
    report()
    assert len(client.get("/api/admin/alerts/pending", headers=auth(admin)).json()) == 1


def test_alert_approval_flow_and_permissions():
    admin = make_user("admin@example.com", Role.administrator)
    insp = make_user("i@example.com", Role.field_inspector)
    sub = make_user("s@example.com")
    client.post("/api/subscriptions", json={"locality": "Kurla"}, headers=auth(sub))
    draft = {"title": "Boil water advice", "locality": "Kurla", "severity": "advisory",
             "description": "Draft written by an inspector", "recommended_action": "Boil water", "source": "Field team"}
    assert client.post("/api/alert-drafts", json=draft, headers=auth(sub)).status_code == 403
    d = client.post("/api/alert-drafts", json=draft, headers=auth(insp))
    assert d.status_code == 201 and d.json()["approval_status"] == "pending_approval"
    aid = d.json()["id"]
    assert client.post(f"/api/admin/alerts/{aid}/approve", headers=auth(insp)).status_code == 403
    assert client.get("/api/alerts").json() == []
    ok = client.post(f"/api/admin/alerts/{aid}/approve", headers=auth(admin))
    assert ok.status_code == 200 and ok.json()["approval_status"] == "approved"
    assert len(client.get("/api/alerts").json()) == 1
    assert any("UNVERIFIED" in n["title"] for n in client.get("/api/notifications", headers=auth(sub)).json())
    assert client.post(f"/api/admin/alerts/{aid}/approve", headers=auth(admin)).status_code == 409


def test_reject_alert_needs_reason():
    admin = make_user("admin@example.com", Role.administrator)
    insp = make_user("i@example.com", Role.field_inspector)
    draft = {"title": "Maybe issue", "locality": "Kurla", "severity": "info",
             "description": "Draft written by an inspector", "recommended_action": "Check", "source": "Field team"}
    aid = client.post("/api/alert-drafts", json=draft, headers=auth(insp)).json()["id"]
    assert client.post(f"/api/admin/alerts/{aid}/reject", json={"reason": "x"}, headers=auth(admin)).status_code == 422
    r = client.post(f"/api/admin/alerts/{aid}/reject", json={"reason": "Not enough evidence"}, headers=auth(admin))
    assert r.json()["approval_status"] == "rejected"


# ---------------- Admin dashboard ----------------

def test_dashboard_numbers_and_access():
    admin = make_user("admin@example.com", Role.administrator)
    citizen = make_user("c@example.com")
    assert client.get("/api/admin/dashboard", headers=auth(citizen)).status_code == 403
    code = report().json()["report_code"]
    report(locality="Dharavi")
    client.patch(f"/api/admin/reports/{code}", json={"status": "verified"}, headers=auth(admin))
    d = client.get("/api/admin/dashboard", headers=auth(admin)).json()
    assert d["reports"]["total"] == 2 and d["reports"]["verified"] == 1 and d["reports"]["pending_review"] == 1
    assert d["resolution"]["open"] == 2 and d["resolution"]["resolved"] == 0
    assert {x["locality"] for x in d["reports_by_location"]} == {"Kurla", "Dharavi"}
    for key in ("water_quality", "disease_trends", "alerts_awaiting_approval", "definitions"):
        assert key in d


# ---------------- Map verified_only ----------------

def test_map_verified_only_hides_unverified_reports():
    admin = make_user("admin@example.com", Role.administrator)
    a = report(latitude=19.07, longitude=72.88).json()["report_code"]
    report(latitude=19.08, longitude=72.89, category="unusual_color")
    client.patch(f"/api/admin/reports/{a}", json={"status": "verified"}, headers=auth(admin))
    allm = client.get("/api/map/markers").json()["markers"]
    ver = client.get("/api/map/markers", params={"verified_only": True}).json()["markers"]
    assert len(allm) == 2 and len(ver) == 1 and ver[0]["verification_label"] == "Verified by reviewer"


# ---------------- Service points ----------------

def test_service_points_admin_create_nearby_and_unverified_flag():
    admin = make_user("admin@example.com", Role.administrator)
    citizen = make_user("c@example.com")
    lab = {"category": "water_testing_lab", "name": "Example Water Lab", "latitude": 19.075, "longitude": 72.88,
           "source": "Example directory"}
    assert client.post("/api/admin/service-points", json=lab, headers=auth(citizen)).status_code == 403
    assert client.post("/api/admin/service-points", json=lab, headers=auth(admin)).status_code == 201
    desk = {"category": "municipal_complaint", "name": "Example Municipal Water Complaints",
            "coverage_area": "Example City", "source": "Example municipal site", "phone": "000"}
    client.post("/api/admin/service-points", json=desk, headers=auth(admin))
    r = client.get("/api/service-points", params={"lat": 19.0726, "lon": 72.8845, "radius_km": 5}).json()
    assert [x["name"] for x in r] == ["Example Water Lab", "Example Municipal Water Complaints"]
    assert r[0]["contact_verified"] is False and "destination=19.075,72.88" in r[0]["directions_url"]
    assert r[1]["directions_url"] is None
    only = client.get("/api/service-points", params={"category": "water_testing_lab", "lat": 19.0726, "lon": 72.8845}).json()
    assert len(only) == 1