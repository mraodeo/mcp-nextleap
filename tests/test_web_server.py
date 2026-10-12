"""
Unit tests for the Starlette Web Server API (src/web/server.py).
Validates HTTP endpoints: index, scenarios, process, refine, approve, and benchmark.
"""
from starlette.testclient import TestClient
from src.web.server import app

client = TestClient(app)

def test_web_index_view():
    response = client.get("/")
    assert response.status_code == 200
    assert "Groww Multi-Agent Operations Portal" in response.text

def test_web_get_scenarios():
    response = client.get("/api/scenarios")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert len(data["scenarios"]) >= 5
    assert any(s["id"] == "branch_a" for s in data["scenarios"])

def test_web_process_ticket_covered():
    response = client.post("/api/process", json={"raw_input": "Why was exit load charged on HDFC Large Cap Fund Direct Growth?"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    state = data["state"]
    assert state["facts"]["status"] == "covered"
    assert "1%" in state["facts"]["extracted_text"]
    assert state["reviewer"]["passed"] is True
    assert state["orchestrator"]["sentence_count"] <= 3

def test_web_process_ticket_pii():
    response = client.post("/api/process", json={"raw_input": "My PAN is ABCDE1234F. Exit load for Mid Cap?"})
    assert response.status_code == 200
    data = response.json()
    state = data["state"]
    assert state["pii_metadata"]["has_pii"] is True
    assert "ABCDE1234F" not in state["sanitized_input"]
    assert "ABCDE1234F" not in state["orchestrator"]["reply_draft"]

def test_web_refine_ticket():
    # Process first
    proc_res = client.post("/api/process", json={"raw_input": "Why was exit load charged on HDFC Large Cap?"})
    state = proc_res.json()["state"]

    refine_res = client.post("/api/refine", json={"state": state, "feedback": "make it shorter"})
    assert refine_res.status_code == 200
    updated_state = refine_res.json()["state"]
    assert updated_state["refinement_count"] == 1
    assert updated_state["active_refinement_target"] == "orchestrator"

from src.mcp_tools import MCPExecutionGate

def test_web_approve_ticket():
    MCPExecutionGate.reset_registry()
    proc_res = client.post("/api/process", json={"raw_input": "Web API unique ticket: Why exit load on Large Cap?"})
    state = proc_res.json()["state"]

    approve_res = client.post("/api/approve", json={"state": state})
    assert approve_res.status_code == 200
    app_data = approve_res.json()
    assert app_data["status"] == "success"
    assert app_data["email_draft"]["payload"]["auto_send"] is False
    assert app_data["email_draft"]["payload"]["status"] == "DRAFT"

def test_web_reviewer_checks_and_discrepancy_schema():
    res = client.post("/api/process", json={"raw_input": "Why was exit load charged on HDFC Large Cap Fund Direct Growth?"})
    assert res.status_code == 200
    state = res.json()["state"]
    # Verify Reviewer contract
    rev = state["reviewer"]
    assert rev["passed"] is True
    assert rev["status"] == "PASS"
    assert "checks" in rev
    assert rev["checks"]["no_advice_violation"] is True
    assert rev["checks"]["has_grounded_timestamp"] is True
    assert rev["checks"]["within_sentence_limit"] is True
    assert rev["checks"]["no_pii_leakage"] is True

    # Verify Discrepancy flag
    orch = state["orchestrator"]
    assert "discrepancy_flag" in orch
    assert "target_team" in orch
    assert "priority" in orch

def test_web_benchmark_schema():
    res = client.get("/api/benchmark")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["total_runs"] >= 5
    scorecard = data["scorecard"]
    assert "compliance_safety_rate" in scorecard
    assert "pii_protection_rate" in scorecard
    assert "verification_date_grounding_rate" in scorecard
    assert scorecard["compliance_safety_rate"] == 1.0
    assert scorecard["pii_protection_rate"] == 1.0
