"""
Unit tests for Specialist Agents (Facts, Pattern, Compliance).
Validates single-model-call classification, closed-set extraction, and fallback invariants.
"""
from src.agents.facts_agent import facts_agent_node
from src.agents.pattern_agent import pattern_agent_node
from src.agents.compliance_agent import compliance_agent_node
from src.config import CANONICAL_NAV_DATE, REVIEW_WINDOW, VALID_SCHEME_IDS

# Helper to construct minimal test state
def make_test_state(sanitized_input: str, pii_detected: bool = False, pii_types: list = None) -> dict:
    return {
        "raw_input": sanitized_input,
        "sanitized_input": sanitized_input,
        "pii_metadata": {
            "has_pii": pii_detected,
            "detected_types": pii_types or [],
            "redacted_text": sanitized_input
        }
    }

# ==============================================================================
# 1. FACTS AGENT TESTS
# ==============================================================================

def test_facts_agent_in_scope_large_cap_exit_load():
    state = make_test_state("Why was I charged an exit load on HDFC Large Cap Fund Direct Growth?")
    res = facts_agent_node(state)
    facts = res["facts"]

    assert facts["status"] == "covered"
    assert facts["scheme_id"] == "large_cap"
    assert facts["section_title"] == "Exit load"
    assert "1% if redeemed within 1 year" in facts["extracted_text"]
    assert facts["source_url"] == "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth"
    assert facts["last_checked_date"] == CANONICAL_NAV_DATE
    assert res["fired_agents_log"] == ["facts_agent"]

def test_facts_agent_in_scope_gold_fof():
    state = make_test_state("What is the exit load on HDFC Gold ETF Fund of Fund Direct Plan Growth?")
    res = facts_agent_node(state)
    facts = res["facts"]

    assert facts["status"] == "covered"
    assert facts["scheme_id"] == "gold_fof"
    assert "1%" in facts["extracted_text"]
    assert "15 days" in facts["extracted_text"]
    assert facts["source_url"] == "https://groww.in/mutual-funds/hdfc-gold-etf-fund-of-fund-direct-plan-growth"

def test_facts_agent_stamp_duty_and_tax():
    state = make_test_state("Tell me about the stamp duty and tax for HDFC Mid Cap Fund.")
    res = facts_agent_node(state)
    facts = res["facts"]

    assert facts["status"] == "covered"
    assert facts["scheme_id"] == "mid_cap"
    assert facts["section_title"] == "Stamp duty and tax"
    assert "0.005%" in facts["extracted_text"]
    assert "20%" in facts["extracted_text"]

def test_facts_agent_out_of_scope_scheme():
    state = make_test_state("What is the exit load for SBI Bluechip Fund Direct Growth?")
    res = facts_agent_node(state)
    facts = res["facts"]

    assert facts["status"] == "not_covered"
    assert facts["scheme_id"] is None
    assert facts["source_url"] is None
    assert "not covered in the verified scheme documents" in facts["extracted_text"]
    assert facts["searched_schemes"] == list(VALID_SCHEME_IDS)

def test_facts_agent_unparsed_attribute():
    state = make_test_state("What are the top 5 stock holdings in HDFC Small Cap Fund?")
    res = facts_agent_node(state)
    facts = res["facts"]

    assert facts["status"] == "not_covered"
    assert facts["scheme_id"] is None

# ==============================================================================
# 2. PATTERN AGENT TESTS
# ==============================================================================

def test_pattern_agent_fees_brokerage():
    state = make_test_state("Why was an unexpected exit load and brokerage fee charged?")
    res = pattern_agent_node(state)
    pattern = res["pattern"]

    assert pattern["theme_id"] == "fees_brokerage"
    assert pattern["theme_name"] == "Fees & brokerage"
    assert pattern["review_count"] == 136
    assert pattern["status"] == "recurring"
    assert pattern["review_window"] == REVIEW_WINDOW
    assert res["fired_agents_log"] == ["pattern_agent"]

def test_pattern_agent_money_movement():
    state = make_test_state("Money debited from bank account via UPI but deposit failed.")
    res = pattern_agent_node(state)
    pattern = res["pattern"]

    assert pattern["theme_id"] == "money_movement"
    assert pattern["review_count"] == 162
    assert pattern["status"] == "recurring"
    assert pattern["in_top_themes"] is True

def test_pattern_agent_trading_charts():
    state = make_test_state("Candlestick charts freeze during market hours when placing order.")
    res = pattern_agent_node(state)
    pattern = res["pattern"]

    assert pattern["theme_id"] == "trading_charts"
    assert pattern["review_count"] == 503
    assert pattern["status"] == "rising"

def test_pattern_agent_reliability():
    state = make_test_state("App crashed and fingerprint login stopped working.")
    res = pattern_agent_node(state)
    pattern = res["pattern"]

    assert pattern["theme_id"] == "reliability"
    assert pattern["review_count"] == 140
    assert pattern["status"] == "recurring"

def test_pattern_agent_other():
    state = make_test_state("I like the new app interface design and fonts.")
    res = pattern_agent_node(state)
    pattern = res["pattern"]

    assert pattern["theme_id"] == "other"
    assert pattern["review_count"] == 709

# ==============================================================================
# 3. COMPLIANCE AGENT TESTS
# ==============================================================================

def test_compliance_agent_detects_advice():
    state = make_test_state("Should I redeem my HDFC Small Cap units now or stay invested?")
    res = compliance_agent_node(state)
    comp = res["compliance"]

    assert comp["incoming_has_advice"] is True
    assert comp["compliance_passed"] is False
    assert res["fired_agents_log"] == ["compliance_agent"]

def test_compliance_agent_detects_performance_claim():
    state = make_test_state("What guaranteed return or CAGR will I get from this fund?")
    res = compliance_agent_node(state)
    comp = res["compliance"]

    assert comp["incoming_has_performance_claim"] is True
    assert comp["compliance_passed"] is False

def test_compliance_agent_clean_inquiry():
    state = make_test_state("What is the expense ratio of HDFC Large Cap Direct Growth?")
    res = compliance_agent_node(state)
    comp = res["compliance"]

    assert comp["incoming_has_advice"] is False
    assert comp["incoming_has_performance_claim"] is False
    assert comp["compliance_passed"] is True

def test_compliance_agent_pii_propagation():
    state = make_test_state("Why was load cut on account?", pii_detected=True, pii_types=["PAN", "PHONE"])
    res = compliance_agent_node(state)
    comp = res["compliance"]

    assert comp["pii_detected"] is True
    assert "PAN" in comp["detected_pii_types"]
    assert "PHONE" in comp["detected_pii_types"]
