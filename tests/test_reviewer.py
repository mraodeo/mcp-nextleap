"""
Unit tests for Orchestrator and Automated Reviewer guardrail node.
Validates dual-channel synthesis, discrepancy detection, hard-fail rules, and attempt counters.
"""
from src.orchestrator.orchestrator import orchestrator_node, count_sentences
from src.orchestrator.reviewer import reviewer_node
from src.config import CANONICAL_NAV_DATE

def make_orchestrator_state(
    facts_covered: bool = True,
    has_advice: bool = False,
    pattern_status: str = "recurring",
    theme_id: str = "fees_brokerage",
    rework_count: int = 0
) -> dict:
    if facts_covered:
        facts = {
            "scheme_id": "large_cap",
            "scheme_name": "HDFC Large Cap Fund Direct Growth",
            "section_title": "Exit load",
            "extracted_text": "Exit load of 1% if redeemed within 1 year",
            "source_url": "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
            "last_checked_date": CANONICAL_NAV_DATE,
            "status": "covered",
            "searched_schemes": ["large_cap"],
            "searched_sections": ["Exit load"]
        }
    else:
        facts = {
            "scheme_id": None,
            "scheme_name": None,
            "section_title": None,
            "extracted_text": "The requested information is not covered in the verified scheme documents.",
            "source_url": None,
            "last_checked_date": CANONICAL_NAV_DATE,
            "status": "not_covered",
            "searched_schemes": ["large_cap", "mid_cap", "small_cap", "gold_fof", "silver_fof"],
            "searched_sections": ["Exit load"]
        }

    pattern = {
        "theme_id": theme_id,
        "theme_name": "Fees & brokerage" if theme_id == "fees_brokerage" else "Other feedback",
        "status": pattern_status,
        "review_count": 136,
        "review_window": "2026-04-12 to 2026-07-04",
        "in_top_themes": False
    }

    compliance = {
        "incoming_has_advice": has_advice,
        "incoming_has_performance_claim": False,
        "pii_detected": False,
        "detected_pii_types": [],
        "compliance_passed": not has_advice
    }

    return {
        "raw_input": "Test input query",
        "sanitized_input": "Test input query",
        "pii_metadata": {"has_pii": False, "detected_types": [], "redacted_text": "Test input query"},
        "facts": facts,
        "pattern": pattern,
        "compliance": compliance,
        "rework_count": rework_count
    }

# ==============================================================================
# 1. ORCHESTRATOR SYNTHESIS & ROUTING TESTS
# ==============================================================================

def test_orchestrator_covered_synthesis():
    state = make_orchestrator_state(facts_covered=True, has_advice=False)
    res = orchestrator_node(state)
    orch = res["orchestrator"]

    assert orch["sentence_count"] <= 3
    assert "HDFC Large Cap Fund Direct Growth" in orch["reply_draft"]
    assert "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth" in orch["reply_draft"]
    assert CANONICAL_NAV_DATE in orch["reply_draft"]
    assert orch["citation_url"] == "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth"

def test_orchestrator_out_of_scope_synthesis():
    state = make_orchestrator_state(facts_covered=False, has_advice=False)
    res = orchestrator_node(state)
    orch = res["orchestrator"]

    assert orch["sentence_count"] <= 3
    assert "not covered in our verified scheme documents" in orch["reply_draft"]
    assert orch["citation_url"] is None
    assert CANONICAL_NAV_DATE in orch["reply_draft"]

def test_orchestrator_discrepancy_protocol():
    # When facts covered AND pattern is recurring (e.g. 136 fee complaints)
    state = make_orchestrator_state(facts_covered=True, pattern_status="recurring", theme_id="fees_brokerage")
    res = orchestrator_node(state)
    orch = res["orchestrator"]

    assert orch["discrepancy_flag"] is True
    assert orch["priority"] == "P1-High"
    assert "Discrepancy Detected" in orch["routing_note"]
    assert orch["target_team"] == "Billing & Brokerage Operations"

def test_orchestrator_advice_deflection():
    state = make_orchestrator_state(facts_covered=True, has_advice=True)
    res = orchestrator_node(state)
    orch = res["orchestrator"]

    assert orch["sentence_count"] <= 3
    assert "does not provide personalized investment advice" in orch["reply_draft"]
    assert CANONICAL_NAV_DATE in orch["reply_draft"]

def test_sentence_counter_protects_decimals_and_urls():
    text = (
        "NAV is Rs. 1217.44 on 25-Jun-2026. "
        "Check details at https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth. "
        "Last checked: 25-Jun-2026."
    )
    count = count_sentences(text)
    assert count == 3

# ==============================================================================
# 2. REVIEWER GUARDRAIL & HARD-FAIL TESTS
# ==============================================================================

def test_reviewer_passes_clean_orchestrated_draft():
    state = make_orchestrator_state(facts_covered=True)
    orch_res = orchestrator_node(state)
    state["orchestrator"] = orch_res["orchestrator"]

    rev_res = reviewer_node(state)
    rev = rev_res["reviewer"]

    assert rev["passed"] is True
    assert len(rev["failure_reasons"]) == 0
    assert rev["review_attempt"] == 1

def test_reviewer_passes_clean_out_of_scope_draft():
    state = make_orchestrator_state(facts_covered=False)
    orch_res = orchestrator_node(state)
    state["orchestrator"] = orch_res["orchestrator"]

    rev_res = reviewer_node(state)
    rev = rev_res["reviewer"]

    assert rev["passed"] is True
    assert len(rev["failure_reasons"]) == 0

def test_reviewer_catches_surviving_pii():
    state = make_orchestrator_state(facts_covered=True)
    orch_res = orchestrator_node(state)
    state["orchestrator"] = orch_res["orchestrator"]
    # Poison draft with raw PAN
    state["orchestrator"]["reply_draft"] += " Customer PAN is ABCDE1234F."

    rev_res = reviewer_node(state)
    rev = rev_res["reviewer"]

    assert rev["passed"] is False
    assert any("Surviving PII" in reason for reason in rev["failure_reasons"])

def test_reviewer_catches_advice_language():
    state = make_orchestrator_state(facts_covered=True)
    orch_res = orchestrator_node(state)
    state["orchestrator"] = orch_res["orchestrator"]
    # Poison draft with advice
    state["orchestrator"]["reply_draft"] = "We recommend staying invested in this fund. Last checked: 25-Jun-2026."

    rev_res = reviewer_node(state)
    rev = rev_res["reviewer"]

    assert rev["passed"] is False
    assert any("Banned investment advice" in reason for reason in rev["failure_reasons"])

def test_reviewer_catches_sentence_length_violation():
    state = make_orchestrator_state(facts_covered=True)
    state["orchestrator"] = {
        "reply_draft": "First sentence. Second sentence. Third sentence. Fourth sentence. Last checked: 25-Jun-2026.",
        "citation_url": "https://groww.in/test",
        "last_checked": CANONICAL_NAV_DATE
    }

    rev_res = reviewer_node(state)
    rev = rev_res["reviewer"]

    assert rev["passed"] is False
    assert any("Draft exceeds 3 sentences" in reason for reason in rev["failure_reasons"])

def test_reviewer_catches_missing_timestamp():
    state = make_orchestrator_state(facts_covered=True)
    state["orchestrator"] = {
        "reply_draft": "Exit load is 1% if redeemed within 1 year. See https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth.",
        "citation_url": "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
        "last_checked": ""
    }

    rev_res = reviewer_node(state)
    rev = rev_res["reviewer"]

    assert rev["passed"] is False
    assert any("Missing mandatory last checked verification date" in reason for reason in rev["failure_reasons"])

def test_reviewer_catches_missing_source_url():
    state = make_orchestrator_state(facts_covered=True)
    # Draft mentions the rule and date, but omits the citation URL
    state["orchestrator"] = {
        "reply_draft": "Exit load is 1% if redeemed within 1 year. Last checked: 25-Jun-2026.",
        "citation_url": None,
        "last_checked": CANONICAL_NAV_DATE
    }

    rev_res = reviewer_node(state)
    rev = rev_res["reviewer"]

    assert rev["passed"] is False
    assert any("missing canonical source_url" in reason for reason in rev["failure_reasons"])

def test_reviewer_attempt_tracking():
    state = make_orchestrator_state(facts_covered=True, rework_count=1)
    orch_res = orchestrator_node(state)
    state["orchestrator"] = orch_res["orchestrator"]

    rev_res = reviewer_node(state)
    assert rev_res["reviewer"]["review_attempt"] == 2
