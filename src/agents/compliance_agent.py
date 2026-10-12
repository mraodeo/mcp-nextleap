"""
Compliance Agent: Anti-Advice and Regulatory Guardrail Analysis.
Classifies incoming inquiries for advice solicitation, performance claims, and attaches PII flags.
"""
from typing import Dict, Any
from src.state import AgentGraphState, ComplianceOutput

ADVICE_TRIGGERS = [
    "should i", "recommend", "suggest", "better to hold", "better to sell",
    "is it good", "worth investing", "stay invested", "future return",
    "where to invest", "good buy", "good to buy", "should we redeem"
]

PERFORMANCE_TRIGGERS = [
    "guaranteed return", "expected return", "how much will i make",
    "profit percentage", "cagr promise", "will it double", "guaranteed profit",
    "guaranteed", "promised return"
]

def mock_or_call_compliance_llm(sanitized_text: str) -> Dict[str, bool]:
    """
    Classifies incoming message for advice requests and performance promises.
    """
    text_lower = sanitized_text.lower()
    has_advice = any(trigger in text_lower for trigger in ADVICE_TRIGGERS)
    has_perf = any(trigger in text_lower for trigger in PERFORMANCE_TRIGGERS)
    return {
        "advice": has_advice,
        "performance_claim": has_perf
    }

def compliance_agent_node(state: AgentGraphState) -> Dict[str, Any]:
    """
    Compliance Agent Node: Runs concurrently in parallel fan-out.
    """
    sanitized_input = state["sanitized_input"]
    pii_metadata = state.get("pii_metadata", {
        "has_pii": False,
        "detected_types": [],
        "redacted_text": sanitized_input
    })

    # 1. Single classification call
    llm_result = mock_or_call_compliance_llm(sanitized_input)

    # Compliance passes if no advice was solicited and no performance claim was demanded
    compliance_passed = not (llm_result["advice"] or llm_result["performance_claim"])

    compliance_output: ComplianceOutput = {
        "incoming_has_advice": llm_result["advice"],
        "incoming_has_performance_claim": llm_result["performance_claim"],
        "pii_detected": pii_metadata["has_pii"],
        "detected_pii_types": pii_metadata["detected_types"],
        "compliance_passed": compliance_passed
    }

    return {"compliance": compliance_output, "fired_agents_log": ["compliance_agent"]}
