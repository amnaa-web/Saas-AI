from fastapi.testclient import TestClient
from main import app
client=TestClient(app)

def test_health():
    assert client.get("/api/health").json()["status"]=="ok"

def test_match():
    r=client.post("/api/match",json={"description":"Need welder","required_skills":["welding"],"min_experience_years":4,"location":"Stockholm","verification_required":"document_checked"})
    assert r.status_code==200
    assert [x["candidate_id"] for x in r.json()["results"]]==["cand-001"]

def test_no_hallucination():
    r=client.post("/api/match",json={"description":"Need nuclear engineer","required_skills":["nuclear engineering"],"min_experience_years":1,"location":None,"verification_required":"any"})
    assert r.json()["results"]==[]

def test_verification():
    r=client.post("/api/verification/ver-001",json={"action":"request_info","note":"Need more evidence"})
    assert r.json()["status"]=="additional_info_requested"

def test_subscription():
    r=client.post("/api/subscription",json={"plan":"enterprise"})
    assert r.json()["company"]["contact_quota"]==500

def test_contract():
    r=client.post("/api/contracts",json={"template":"Business Agreement"})
    assert r.json()["external_send"] is False