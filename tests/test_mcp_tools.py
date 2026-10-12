"""
Unit tests for Approval-Gated MCP Tool Integration (src/mcp_tools.py).
Validates:
1. Hard permission blocking when is_approved is False.
2. Hard permission blocking when ticket is quarantined.
3. Successful execution when is_approved is True.
4. Physical invariant: auto_send is strictly False.
5. Idempotency protection against rapid double-clicks (EC-13).
6. Partial failure and retry handling.
7. LangGraph node wrapper behavior.
"""
try:
    import pytest
except ImportError:
    import contextlib
    class PytestFallback:
        class _ExcInfo:
            value = None
        @contextlib.contextmanager
        def raises(self, exc_cls):
            info = self._ExcInfo()
            try:
                yield info
            except exc_cls as e:
                info.value = e
            else:
                raise AssertionError(f"Expected exception {exc_cls.__name__} was not raised")
    pytest = PytestFallback()
from src.mcp_tools import MCPExecutionGate, mcp_execution_node
from src.state import AgentGraphState, OrchestratorOutput
from src.config import CANONICAL_NAV_DATE

def _create_mock_state(is_approved: bool = False, is_quarantined: bool = False) -> AgentGraphState:
    orch_output: OrchestratorOutput = {
        "reply_draft": f"As per official scheme terms for HDFC Large Cap Fund, exit load is 1% if redeemed within 1 year. You can verify at https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth. Last checked: {CANONICAL_NAV_DATE}.",
        "citation_url": "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
        "last_checked": CANONICAL_NAV_DATE,
        "sentence_count": 2,
        "routing_note": "Route to: Mutual Funds Operations | Priority: P3-Low\nPattern Context: General (0 reviews, status: one-off)",
        "target_team": "Mutual Funds Operations",
        "priority": "P3-Low",
        "discrepancy_flag": False,
        "discrepancy_details": None
    }

    return {
        "raw_input": "Why was exit load charged on HDFC Large Cap?",
        "sanitized_input": "Why was exit load charged on HDFC Large Cap?",
        "pii_metadata": {"has_pii": False, "detected_types": [], "redacted_text": "Why was exit load charged on HDFC Large Cap?"},
        "facts": None,
        "pattern": None,
        "compliance": None,
        "orchestrator": orch_output,
        "reviewer": {"passed": True, "failure_reasons": [], "review_attempt": 1},
        "rework_count": 0,
        "refinement_count": 0,
        "refinement_feedback": None,
        "active_refinement_target": None,
        "fired_agents_log": ["sanitizer", "orchestrator", "reviewer", "human_review"],
        "is_approved": is_approved,
        "is_quarantined": is_quarantined,
        "mcp_actions_executed": []
    }

def test_unapproved_append_blocks():
    MCPExecutionGate.reset_registry()
    state = _create_mock_state(is_approved=False)
    with pytest.raises(PermissionError) as exc_info:
        MCPExecutionGate.append_record_to_doc(state)
    assert "Human approval required" in str(exc_info.value)

def test_unapproved_email_blocks():
    MCPExecutionGate.reset_registry()
    state = _create_mock_state(is_approved=False)
    with pytest.raises(PermissionError) as exc_info:
        MCPExecutionGate.create_email_draft(state)
    assert "Human approval required" in str(exc_info.value)

def test_quarantined_ticket_blocks_even_if_approved():
    MCPExecutionGate.reset_registry()
    state = _create_mock_state(is_approved=True, is_quarantined=True)
    with pytest.raises(PermissionError) as exc_info:
        MCPExecutionGate.append_record_to_doc(state)
    assert "Quarantined ticket cannot be executed" in str(exc_info.value)

    with pytest.raises(PermissionError) as exc_info:
        MCPExecutionGate.create_email_draft(state)
    assert "Quarantined ticket cannot be executed" in str(exc_info.value)

def test_missing_orchestrator_raises():
    MCPExecutionGate.reset_registry()
    state = _create_mock_state(is_approved=True)
    state["orchestrator"] = None
    with pytest.raises(ValueError) as exc_info:
        MCPExecutionGate.append_record_to_doc(state)
    assert "Missing orchestrator output" in str(exc_info.value)

def test_approved_append_success():
    MCPExecutionGate.reset_registry()
    state = _create_mock_state(is_approved=True)
    result = MCPExecutionGate.append_record_to_doc(state)

    assert result["status"] == "success"
    assert result["action"] == "append_record_to_doc"
    assert "record" in result
    record = result["record"]
    assert "HDFC Large Cap Fund" in record["draft"]
    assert record["citation"] == "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth"
    assert record["timestamp"] == CANONICAL_NAV_DATE
    assert record["target_team"] == "Mutual Funds Operations"
    assert record["priority"] == "P3-Low"

def test_approved_email_draft_success():
    MCPExecutionGate.reset_registry()
    state = _create_mock_state(is_approved=True)
    result = MCPExecutionGate.create_email_draft(state)

    assert result["status"] == "success"
    assert result["action"] == "create_email_draft"
    assert "payload" in result
    payload = result["payload"]
    assert payload["status"] == "DRAFT"
    assert payload["auto_send"] is False
    assert payload["dispatch_allowed"] is False
    assert "HDFC Large Cap Fund" in payload["body"]

def test_zero_auto_send_invariant():
    MCPExecutionGate.reset_registry()
    state = _create_mock_state(is_approved=True)
    result = MCPExecutionGate.create_email_draft(state)
    payload = result["payload"]
    # Physical invariant: Under NO circumstance should auto_send be True
    assert payload["auto_send"] is False
    assert payload["status"] == "DRAFT"

def test_idempotency_prevents_duplicate_append():
    MCPExecutionGate.reset_registry()
    state = _create_mock_state(is_approved=True)
    
    # First invocation: success
    res1 = MCPExecutionGate.append_record_to_doc(state, idempotency_key="ticket_123")
    assert res1["status"] == "success"

    # Second invocation with same idempotency key: duplicate ignored
    res2 = MCPExecutionGate.append_record_to_doc(state, idempotency_key="ticket_123")
    assert res2["status"] == "duplicate_ignored"
    assert "already executed" in res2["message"]

def test_idempotency_prevents_duplicate_email_draft():
    MCPExecutionGate.reset_registry()
    state = _create_mock_state(is_approved=True)

    # First invocation: success
    res1 = MCPExecutionGate.create_email_draft(state, idempotency_key="ticket_123")
    assert res1["status"] == "success"

    # Second invocation with same idempotency key: duplicate ignored
    res2 = MCPExecutionGate.create_email_draft(state, idempotency_key="ticket_123")
    assert res2["status"] == "duplicate_ignored"
    assert "already executed" in res2["message"]

def test_execute_all_combined():
    MCPExecutionGate.reset_registry()
    state = _create_mock_state(is_approved=True)

    result = MCPExecutionGate.execute_all(state, idempotency_key="ticket_batch_456")
    assert result["status"] == "success"
    assert result["append_record"]["status"] == "success"
    assert result["email_draft"]["status"] == "success"

    # Retry should ignore both
    retry_result = MCPExecutionGate.execute_all(state, idempotency_key="ticket_batch_456")
    assert retry_result["append_record"]["status"] == "duplicate_ignored"
    assert retry_result["email_draft"]["status"] == "duplicate_ignored"

def test_mcp_node_integration():
    MCPExecutionGate.reset_registry()
    state = _create_mock_state(is_approved=True)
    node_output = mcp_execution_node(state)

    assert "mcp_actions_executed" in node_output
    assert "append_record_to_doc:success" in node_output["mcp_actions_executed"]
    assert "create_email_draft:success" in node_output["mcp_actions_executed"]
    assert "mcp_execution_gate" in node_output["fired_agents_log"]

def test_mcp_node_unapproved_does_not_execute():
    MCPExecutionGate.reset_registry()
    state = _create_mock_state(is_approved=False)
    node_output = mcp_execution_node(state)

    assert node_output["mcp_actions_executed"] == []
    assert "mcp_execution_gate" in node_output["fired_agents_log"]
