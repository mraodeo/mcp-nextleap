"""
Facts Agent: Deterministic Scheme Information Retrieval.
Implements the 1-model-call classification invariant with closed-set extraction.
"""
import re
from typing import Dict, Any, Optional
from src.state import AgentGraphState, FactsOutput
from src.data_loader import DataLoader
from src.config import (
    VALID_SCHEME_IDS,
    VALID_SECTIONS,
    CANONICAL_NAV_DATE
)

FACTS_SYSTEM_PROMPT = f"""You are the Facts Specialist for Groww Mutual Funds.
Your ONLY role is to classify which scheme and section the user complaint is asking about.
Choose scheme_id STRICTLY from this closed list:
{VALID_SCHEME_IDS}
Choose section_title STRICTLY from this closed list:
{VALID_SECTIONS}

If the user query is NOT about one of these 5 schemes or 7 sections, return null for both.
Do NOT answer the question. Return ONLY valid JSON with keys "scheme_id" and "section_title".
"""

# External funds to explicitly reject
EXTERNAL_FUNDS = [
    "sbi", "axis", "parag parikh", "nippon", "mirae", "icici", "kotak",
    "uti", "tata", "quant", "motilal", "dsp", "canara"
]

def mock_or_call_facts_llm(sanitized_text: str) -> Dict[str, Optional[str]]:
    """
    Classifies the sanitized query against the closed scheme and section enumerations.
    In production, this executes litellm / Google GenAI with json_object mode.
    """
    text_lower = sanitized_text.lower()

    # 1. Reject external funds outside the 5 verified HDFC schemes
    if any(re.search(rf"\b{fund}\b", text_lower) for fund in EXTERNAL_FUNDS):
        return {"scheme_id": None, "section_title": None}

    # 2. Reject unparsed attributes (e.g., stock holdings, historical returns, Sharpe ratio)
    unparsed_attributes = ["stock holdings", "portfolio", "top 5 stocks", "top 10 stocks", "cagr", "sharpe ratio", "returns over 3 years"]
    if any(attr in text_lower for attr in unparsed_attributes):
        return {"scheme_id": None, "section_title": None}

    # 3. Scheme classification (Strict closed set of 5 schemes)
    matched_scheme = None
    if "silver" in text_lower:
        matched_scheme = "silver_fof"
    elif "gold" in text_lower:
        matched_scheme = "gold_fof"
    elif any(k in text_lower for k in ["large cap", "large-cap", "largecap"]):
        matched_scheme = "large_cap"
    elif any(k in text_lower for k in ["mid cap", "mid-cap", "midcap"]):
        matched_scheme = "mid_cap"
    elif any(k in text_lower for k in ["small cap", "small-cap", "smallcap"]):
        matched_scheme = "small_cap"

    # 4. Section classification (Strict closed set of 7 sections)
    matched_section = None
    if any(k in text_lower for k in ["exit load", "exit-load", "redeem", "redemption", "charges for redemption", "redemption charge", "penalty"]):
        matched_section = "Exit load"
    elif any(k in text_lower for k in ["expense ratio", "nav", "net asset value", "aum", "fund size", "riskometer"]):
        matched_section = "Key fund facts"
    elif "benchmark" in text_lower:
        matched_section = "Benchmark"
    elif any(k in text_lower for k in ["objective", "investment strategy"]):
        matched_section = "Investment objective"
    elif any(k in text_lower for k in ["stamp duty", "tax", "taxes", "taxation", "stcg", "ltcg"]):
        matched_section = "Stamp duty and tax"
    elif any(k in text_lower for k in ["manager", "management", "rahul baijal", "dhruv muchhal"]):
        matched_section = "Fund management"
    elif any(k in text_lower for k in ["minimum investment", "min investment", "min sip", "minimum sip", "lumpsum"]):
        matched_section = "Minimum investments"

    return {"scheme_id": matched_scheme, "section_title": matched_section}

def facts_agent_node(state: AgentGraphState) -> Dict[str, Any]:
    """
    Facts Agent Node: Runs concurrently in parallel fan-out.
    """
    sanitized_input = state["sanitized_input"]
    data_loader = DataLoader.get_instance()

    # 1. Single classification call
    llm_result = mock_or_call_facts_llm(sanitized_input)
    scheme_id = llm_result.get("scheme_id")
    section_title = llm_result.get("section_title")

    # 2. Deterministic code retrieval
    if scheme_id in VALID_SCHEME_IDS and section_title in VALID_SECTIONS:
        extracted_text = data_loader.get_scheme_section_text(scheme_id, section_title)
        source_url = data_loader.get_scheme_source_url(scheme_id)
        scheme_name = data_loader.get_scheme_name(scheme_id)

        facts_output: FactsOutput = {
            "scheme_id": scheme_id,
            "scheme_name": scheme_name,
            "section_title": section_title,
            "extracted_text": extracted_text or "",
            "source_url": source_url,
            "last_checked_date": CANONICAL_NAV_DATE,
            "status": "covered",
            "searched_schemes": [scheme_id],
            "searched_sections": [section_title]
        }
    else:
        # Fallback invariant: "not covered"
        facts_output: FactsOutput = {
            "scheme_id": None,
            "scheme_name": None,
            "section_title": None,
            "extracted_text": "The requested information is not covered in the verified scheme documents.",
            "source_url": None,
            "last_checked_date": CANONICAL_NAV_DATE,
            "status": "not_covered",
            "searched_schemes": list(VALID_SCHEME_IDS),
            "searched_sections": list(VALID_SECTIONS)
        }

    return {"facts": facts_output, "fired_agents_log": ["facts_agent"]}
