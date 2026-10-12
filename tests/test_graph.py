"""
Unit tests for LangGraph Workflow Assembly, Routing, and Selective Refinement.
Validates parallel execution, conditional reviewer rework, quarantine, and refinement caps.
"""
from src.graph import create_support_graph, route_reviewer, apply_refinement, parse_refinement_intent
from src.config import CANONICAL_NAV_DATE, MAX_REWORK_ATTEMPTS, MAX_REFINEMENT_ATTEMPTS

def test_graph_compilation():
    graph = create_support_graph()
    assert graph is not None

def test_end_to_end_graph_execution_clean_fact():
    graph = create_support_graph()
    query = "Why was I charged an exit load on HDFC Large Cap Fund Direct Growth?"
    result = graph.invoke({"raw_input": query})

    assert result["sanitized_input"] == query
    assert result["pii_metadata"]["has_pii"] is False

    # Parallel specialists executed
    assert result["facts"] is not None
    assert result["facts"]["status"] == "covered"
    assert result["facts"]["scheme_id"] == "large_cap"
    assert "1%" in result["facts"]["extracted_text"]

    assert result["pattern"] is not None
    assert result["pattern"]["theme_id"] == "fees_brokerage"

    assert result["compliance"] is not None
    assert result["compliance"]["compliance_passed"] is True

    # Orchestrator & Reviewer executed
    assert result["orchestrator"] is not None
    assert result["orchestrator"]["sentence_count"] <= 3
    assert result["orchestrator"]["citation_url"] == "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth"
    assert CANONICAL_NAV_DATE in result["orchestrator"]["reply_draft"]

    assert result["reviewer"] is not None
    assert result["reviewer"]["passed"] is True

    # Check fired agents audit trail
    logs = result["fired_agents_log"]
    assert "sanitizer" in logs
    assert "facts_agent" in logs
    assert "pattern_agent" in logs
    assert "compliance_agent" in logs
    assert "orchestrator" in logs
    assert "reviewer" in logs
    assert "human_review" in logs

def test_end_to_end_out_of_scope_query():
    graph = create_support_graph()
    query = "What is the exit load on SBI Small Cap Fund?"
    result = graph.invoke({"raw_input": query})

    assert result["facts"]["status"] == "not_covered"
    assert "not covered in our verified scheme documents" in result["orchestrator"]["reply_draft"]
    assert result["reviewer"]["passed"] is True

def test_route_reviewer_logic():
    # 1. Passed -> human_review
    state_pass = {"reviewer": {"passed": True}, "rework_count": 0}
    assert route_reviewer(state_pass) == "human_review"

    # 2. Failed with rework_count = 0 -> orchestrator (increments to 1)
    state_fail_1 = {"reviewer": {"passed": False}, "rework_count": 0}
    assert route_reviewer(state_fail_1) == "orchestrator"
    assert state_fail_1["rework_count"] == 1

    # 3. Failed with rework_count >= 1 -> quarantine
    state_fail_2 = {"reviewer": {"passed": False}, "rework_count": 1}
    assert route_reviewer(state_fail_2) == "quarantine"

def test_parse_refinement_intent():
    assert parse_refinement_intent("Make this draft shorter and more concise") == "orchestrator"
    assert parse_refinement_intent("They are asking about HDFC Mid Cap, not Large Cap") == "facts"
    assert parse_refinement_intent("Check if this is the fee issue from last week") == "pattern"
    assert parse_refinement_intent("Rephrase slightly") == "orchestrator"

def test_selective_refinement_execution():
    graph = create_support_graph()
    initial_query = "Why was I charged exit load on HDFC Large Cap Direct Growth?"
    state = graph.invoke({"raw_input": initial_query})

    assert state["facts"]["scheme_id"] == "large_cap"
    initial_facts = state["facts"]
    initial_pattern = state["pattern"]

    # Refinement 1: "Make it shorter" -> Only orchestrator re-runs
    ref_state_1 = apply_refinement(state, "Make it shorter")
    assert ref_state_1["refinement_count"] == 1
    assert ref_state_1["active_refinement_target"] == "orchestrator"
    # Facts and pattern state preserved
    assert ref_state_1["facts"]["scheme_id"] == initial_facts["scheme_id"]
    assert ref_state_1["pattern"]["theme_id"] == initial_pattern["theme_id"]
    assert ref_state_1["reviewer"]["passed"] is True

    # Refinement 2: "They are asking about HDFC Mid Cap" -> Facts re-runs
    # Update sanitized input to Mid Cap query to simulate revised context
    ref_state_1["sanitized_input"] = "What is the exit load on HDFC Mid Cap Fund?"
    ref_state_2 = apply_refinement(ref_state_1, "They are asking about HDFC Mid Cap fund")
    assert ref_state_2["refinement_count"] == 2
    assert ref_state_2["active_refinement_target"] == "facts"
    assert ref_state_2["facts"]["scheme_id"] == "mid_cap"
    # Pattern preserved
    assert ref_state_2["pattern"]["theme_id"] == initial_pattern["theme_id"]

def test_refinement_budget_ceiling_max_5():
    graph = create_support_graph()
    state = graph.invoke({"raw_input": "Why was exit load charged on Large Cap?"})

    # Execute 5 consecutive refinements
    for i in range(5):
        state = apply_refinement(state, f"Adjustment round {i + 1}")
    assert state["refinement_count"] == 5

    # 6th attempt should be blocked and state preserved
    state_6 = apply_refinement(state, "Adjustment round 6")
    assert state_6["refinement_count"] == 5  # Still capped at 5
