import os
os.environ["DATABASE_URL"] = "sqlite:///./test_waterguard.db"

import pytest
from fastapi.testclient import TestClient

from app.database import Base, SessionLocal, engine
from app.deps import reset_rate_limits
from app.main import app
from app.models import Role, User

client = TestClient(app)
NOW = "2026-10-20T10:00:00Z"


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    reset_rate_limits()
    yield


def register(email="a@example.com"):
    r = client.post("/api/auth/register", json={"email": email, "full_name": "Test User", "password": "StrongPass1!"})
    assert r.status_code == 201, r.text
    return r.json()


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def make_admin(email="boss@example.com"):
    data = register(email)
    db = SessionLocal()
    u = db.get(User, data["user"]["id"])
    u.role = Role.administrator
    db.commit()
    user_id = u.id
    db.close()
    from app.security import create_access_token
    return create_access_token(user_id, "administrator")


def report_body(**kw):
    body = {"category": "unusual_odor", "description": "Strong sewage smell from tap water",
            "locality": "Kurla", "observed_at": NOW, "consent_given": True}
    body.update(kw)
    return body


def test_root_links_to_api_docs():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["docs"] == "/docs"


def test_register_login_me():
    data = register()
    assert data["user"]["role"] == "citizen"
    r = client.post("/api/auth/login", json={"email": "a@example.com", "password": "StrongPass1!"})
    assert r.status_code == 200
    me = client.get("/api/auth/me", headers=auth(r.json()["access_token"]))
    assert me.json()["email"] == "a@example.com"


def test_wrong_password_rejected():
    register()
    r = client.post("/api/auth/login", json={"email": "a@example.com", "password": "nope-nope-1"})
    assert r.status_code == 401


def test_me_requires_auth():
    assert client.get("/api/auth/me").status_code == 401


def test_citizen_cannot_access_admin_endpoints():
    token = register()["access_token"]
    assert client.get("/api/admin/dashboard", headers=auth(token)).status_code == 403
    assert client.get("/api/admin/audit-logs", headers=auth(token)).status_code == 403
    assert client.get("/api/admin/reports", headers=auth(token)).status_code == 403


def test_anonymous_cannot_access_admin_endpoints():
    assert client.get("/api/admin/dashboard").status_code == 401


def test_submit_and_track_report_hides_private_data():
    r = client.post("/api/reports", json=report_body(contact_info="secret@example.com"))
    assert r.status_code == 201
    code = r.json()["report_code"]
    assert "contact_info" not in r.json() and "reporter_id" not in r.json()
    t = client.get(f"/api/reports/{code}")
    assert t.status_code == 200 and t.json()["status"] == "submitted"
    assert t.json()["verification_label"] == "Unverified citizen report"


def test_consent_required():
    r = client.post("/api/reports", json=report_body(consent_given=False))
    assert r.status_code == 422


def test_invalid_coordinates_rejected():
    assert client.post("/api/reports", json=report_body(latitude=120, longitude=10)).status_code == 422


def test_admin_status_update_requires_reason_for_reject_and_is_audited():
    code = client.post("/api/reports", json=report_body()).json()["report_code"]
    admin = make_admin()
    bad = client.patch(f"/api/admin/reports/{code}", json={"status": "rejected"}, headers=auth(admin))
    assert bad.status_code == 422
    ok = client.patch(f"/api/admin/reports/{code}", json={"status": "verified"}, headers=auth(admin))
    assert ok.status_code == 200 and ok.json()["status"] == "verified"
    logs = client.get("/api/admin/audit-logs", headers=auth(admin)).json()
    assert any(l["action"] == "report.status_changed" for l in logs)


def test_rate_limit_on_report_submission():
    codes = [client.post("/api/reports", json=report_body(locality=f"Area {i}")).status_code for i in range(7)]
    assert 429 in codes