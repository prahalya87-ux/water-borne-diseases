from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.database import Base, SessionLocal, engine
from app.deps import reset_rate_limits
from app.main import app
from app.models import DiseaseReport, RiskAssessment, Role, User, WaterQualityTest
from app.security import create_access_token

client = TestClient(app)


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
    db = SessionLocal(); db.get(User, uid).role = role; db.commit(); db.close()
    return create_access_token(uid, role.value)


def now_iso():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def report(**kw):
    body = {"category": "unusual_odor", "water_source": "tap", "description": "Strong smell from tap water",
            "locality": "Kurla", "observed_at": now_iso(), "consent_given": True}
    body.update(kw)
    return client.post("/api/reports", json=body)


# ---------------- Risk model ----------------

def test_single_report_is_insufficient_data_with_limitations():
    admin = make_user("admin@example.com", Role.administrator)
    report()
    r = client.post("/api/admin/risk/run", headers=auth(admin)).json()
    item = r["items"][0]
    assert item["category"] == "insufficient_data" and item["score"] is None
    assert item["limitations"] and r["method"]["validated"] is False
    assert any("Rainfall" in m for m in item["missing_data"])


def test_strong_signals_give_high_with_explained_factors():
    admin = make_user("admin@example.com", Role.administrator)
    for _ in range(3):
        report()
    db = SessionLocal()
    db.add(WaterQualityTest(sample_id="R1", locality="Kurla", tested_at=datetime.now(timezone.utc), organization="Lab",
                            ecoli_result="present", verification_status="laboratory_confirmed"))
    db.add(DiseaseReport(disease="typhoid", cases=12, locality="Kurla", reported_on=date.today(), source="test"))
    db.commit(); db.close()
    item = client.post("/api/admin/risk/run", headers=auth(admin)).json()["items"][0]
    assert item["category"] == "high" and item["score"] >= 8
    assert any("E. coli" in f["factor"] for f in item["factors"])
    assert sum(f["points"] for f in item["factors"]) == item["score"]
    assert item["recommendation"]


def test_demo_records_and_demo_assessments_are_excluded():
    admin = make_user("demo-filter@example.com", Role.administrator)
    db = SessionLocal()
    db.add(WaterQualityTest(sample_id="DEMO-1", locality="Kurla", tested_at=datetime.now(timezone.utc),
                            organization="Demo", ecoli_result="present", is_demo=True))
    db.add(DiseaseReport(disease="cholera", cases=50, locality="Kurla", reported_on=date.today(),
                         source="Demo", is_demo=True))
    db.add(RiskAssessment(locality="Kurla", category="high", score=12, factors_json="{}",
                          period_start=date.today(), period_end=date.today(), is_demo=True))
    db.commit()
    db.close()

    got = client.get("/api/risk/assessments").json()
    assert got["items"] == []
    assert got["current_inputs"] == {
        "citizen_reports_14d": 0, "water_tests_30d": 0, "disease_reports_56d": 0,
    }

    result = client.post("/api/admin/risk/run", headers=auth(admin)).json()
    assert result["items"] == []
    assert result["current_inputs"] == got["current_inputs"]


def test_demo_assessment_does_not_hide_real_assessment_for_locality():
    db = SessionLocal()
    db.add(RiskAssessment(locality="Kurla", category="low", score=1, factors_json="{}",
                          period_start=date.today(), period_end=date.today(), is_demo=False,
                          analysed_at=datetime.now(timezone.utc) - timedelta(days=1)))
    db.add(RiskAssessment(locality="Kurla", category="high", score=12, factors_json="{}",
                          period_start=date.today(), period_end=date.today(), is_demo=True))
    db.commit()
    db.close()

    items = client.get("/api/risk/assessments").json()["items"]
    assert len(items) == 1
    assert items[0]["category"] == "low"
    assert items[0]["is_demo"] is False


def test_disease_report_without_case_count_is_not_counted_as_one_case():
    admin = make_user("unknown-cases@example.com", Role.administrator)
    db = SessionLocal()
    db.add(DiseaseReport(disease="cholera", cases=None, locality="Kurla", reported_on=date.today(),
                         source="Media report", verification_status="media_reported"))
    db.commit()
    db.close()

    item = client.post("/api/admin/risk/run", headers=auth(admin)).json()["items"][0]
    assert item["category"] == "insufficient_data"
    assert item["score"] is None
    assert item["factors"] == [{
        "factor": "Disease reports with unspecified case counts",
        "points": 1,
        "detail": "1 report(s); case count not stated",
    }]


def test_run_requires_admin_and_get_returns_latest_only():
    citizen = make_user("c@example.com")
    assert client.post("/api/admin/risk/run", headers=auth(citizen)).status_code == 403
    assert client.post("/api/admin/risk/run").status_code == 401
    admin = make_user("admin@example.com", Role.administrator)
    report()
    client.post("/api/admin/risk/run", headers=auth(admin))
    client.post("/api/admin/risk/run", headers=auth(admin))
    got = client.get("/api/risk/assessments").json()
    assert len(got["items"]) == 1 and "not diagnoses" in got["disclaimer"]


# ---------------- Assistant ----------------

def chat(message, locality=None):
    return client.post("/api/assistant/chat", json={"message": message, "locality": locality}).json()


def test_emergency_words_send_to_emergency_care():
    r = chat("my child has blood in stool and is very weak")
    assert r["emergency"] is True and "112" in r["answer"]


def test_contaminated_source_answer_is_safe_and_linked():
    r = chat("What precautions should I take if my water source may be contaminated?")
    assert r["emergency"] is False and "boil" in r["answer"].lower()
    assert {l["to"] for l in r["links"]} >= {"/report"}
    assert "cannot diagnose" in r["disclaimer"]


def test_symptom_question_does_not_diagnose():
    r = chat("I have fever and diarrhoea, do I have typhoid?")
    assert r["topic"] == "symptoms" and "cannot tell which illness" in r["answer"]


@pytest.mark.parametrize(("message", "topic", "mention"), [
    ("I have very watery diarrhoea and vomiting", "possible_cholera", "can be seen with cholera"),
    ("Fever for 4 days with stomach pain and weakness", "possible_typhoid", "can be seen with typhoid"),
    ("My eyes are yellow and I have dark urine", "possible_hepatitis", "hepatitis A or E"),
])
def test_symptom_patterns_offer_cautious_possible_causes(message, topic, mention):
    r = chat(message)
    assert r["topic"] == topic and mention in r["answer"]
    assert r["emergency"] is False
    assert "cannot confirm" in r["answer"] or "cannot identify" in r["answer"]


@pytest.mark.parametrize(("message", "topic"), [
    ("What precautions can I take to prevent cholera?", "cholera_prevention"),
    ("How do I prevent typhoid?", "typhoid_prevention"),
    ("How can I avoid hepatitis A?", "hepatitis_prevention"),
])
def test_disease_specific_prevention_advice(message, topic):
    r = chat(message)
    assert r["topic"] == topic
    assert "safe" in r["answer"].lower()


@pytest.mark.parametrize(("message", "topic"), [
    ("How do I prepare ORS safely?", "diarrhoea_care"),
    ("What should I do after flooding?", "flood"),
    ("How do I care for dehydration from diarrhoea?", "diarrhoea_care"),
])
def test_suggested_assistant_questions_have_relevant_guidance(message, topic):
    assert chat(message)["topic"] == topic


def test_emergency_overrides_symptom_pattern():
    r = chat("Very watery diarrhoea with no urine and confusion")
    assert r["topic"] == "emergency" and r["emergency"] is True
    r = chat("Very watery diarrhoea and very little urine")
    assert r["topic"] == "emergency" and r["emergency"] is True


def test_unknown_question_falls_back_honestly():
    r = chat("zzxq blorp")
    assert r["topic"] == "fallback" and "don't have a specific answer" in r["answer"]


def test_local_context_never_invents_alerts():
    r = chat("what should I do during an advisory", "Nowhere")
    assert any("no published alert" in n for n in r["context_notes"])
    admin = make_user("admin@example.com", Role.administrator)
    alert = {"title": "Boil water notice", "locality": "Kurla", "severity": "advisory", "description": "Water test results indicate elevated contamination.",
             "recommended_action": "Boil water", "source": "Test", "verification_status": "official"}
    client.post("/api/admin/alerts", json=alert, headers=auth(admin))
    notes = chat("any advisory?", "Kurla")["context_notes"]
    assert any("Boil water notice" in n for n in notes)


def test_message_length_validated():
    assert client.post("/api/assistant/chat", json={"message": ""}).status_code == 422
    assert client.post("/api/assistant/chat", json={"message": "x" * 501}).status_code == 422               