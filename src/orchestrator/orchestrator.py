"""
Orchestrator: Dual-Channel Synthesis and Internal Ticket Routing.
Merges specialist outputs into a customer reply draft (<= 3 sentences) and internal routing note.
"""
import re
from typing import Dict, Any, List
from src.state import AgentGraphState, OrchestratorOutput
from src.config import MAX_REPLY_SENTENCES, CANONICAL_NAV_DATE

def count_sentences(text: str) -> int:
    """
    Regex-aware sentence segmentation.
    Protects URLs, decimal numbers (e.g. NAV 1217.44), currency codes, and common abbreviations.
    """
    if not text:
        return 0

    # 1. Protect URLs while preserving trailing sentence punctuation
    def _clean_url(m: re.Match) -> str:
        url_str = m.group(0)
        stripped = url_str.rstrip('.!?')
        trailing = url_str[len(stripped):]
        return '[URL]' + trailing

    cleaned = re.sub(r'https?://\S+', _clean_url, text.strip())

    # 2. Protect currency amounts and decimal numbers
    cleaned = re.sub(r'\bRs\.\s*', 'Rs ', cleaned)
    cleaned = re.sub(r'\b\d+\.\d+\b', '[NUM]', cleaned)

    # 3. Protect abbreviations
    cleaned = re.sub(r'\b(yr|yrs|etc|vs|e\.g|i\.e)\.\s*', r'\1 ', cleaned, flags=re.IGNORECASE)

    # 4. Split on terminating punctuation (. ! ?)
    sentences = [s.strip() for s in re.split(r'[.!?]+(?:\s+|$)', cleaned) if s.strip()]
    return len(sentences)

def orchestrator_node(state: AgentGraphState) -> Dict[str, Any]:
    """
    Fan-in node: merges facts, pattern, and compliance into draft & routing note.
    """
    facts = state.get("facts")
    pattern = state.get("pattern")
    compliance = state.get("compliance")

    # =========================================================================
    # CHANNEL A: USER REPLY DRAFT (<= 3 sentences, 1 citation, last checked date)
    # =========================================================================
    has_advice = compliance and compliance.get("incoming_has_advice")

    if facts and facts.get("status") == "covered":
        scheme_name = facts.get("scheme_name", "the scheme")
        extracted_sentence = facts.get("extracted_text", "").strip()
        citation = facts.get("source_url")
        citation_url = citation

        if has_advice:
            # Sentence 1: Advice disclaimer
            # Sentence 2: Scheme factual clause
            # Sentence 3: Verification link and last checked date combined
            reply_draft = (
                f"Groww does not provide personalized investment advice or redemption recommendations. "
                f"As per the official scheme terms for {scheme_name}, {extracted_sentence}. "
                f"You can verify this at {citation} (last checked: {CANONICAL_NAV_DATE})."
            )
        else:
            # Sentence 1: Factual rule from scheme
            # Sentence 2: Citation link
            # Sentence 3: Last checked date
            reply_draft = (
                f"As per the official scheme terms for {scheme_name}, {extracted_sentence}. "
                f"You can verify this in the scheme document at {citation}. "
                f"Last checked: {CANONICAL_NAV_DATE}."
            )
    else:
        # Out-of-scope query handling
        searched = ", ".join(facts.get("searched_schemes", [])[:3]) if facts else "verified funds"
        citation_url = None

        if has_advice:
            reply_draft = (
                f"Groww does not provide personalized investment advice or return projections. "
                f"The requested detail is not covered in our verified scheme documents for {searched}. "
                f"Last checked: {CANONICAL_NAV_DATE}."
            )
        else:
            reply_draft = (
                f"The requested detail is not covered in our verified scheme documents for {searched}. "
                f"Groww support replies strictly reference public scheme disclosures without speculation. "
                f"Last checked: {CANONICAL_NAV_DATE}."
            )

    # Enforce strict sentence budget constraint (<= MAX_REPLY_SENTENCES)
    num_sentences = count_sentences(reply_draft)
    if num_sentences > MAX_REPLY_SENTENCES:
        # Split and preserve the first 2 sentences and append mandatory citation/date as third sentence
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', reply_draft) if s.strip()]
        kept = sentences[:2]
        if citation_url:
            third_sentence = f"Verify at {citation_url} (last checked: {CANONICAL_NAV_DATE})."
        else:
            third_sentence = f"Last checked: {CANONICAL_NAV_DATE}."
        reply_draft = " ".join(kept) + " " + third_sentence
        num_sentences = count_sentences(reply_draft)

    # =========================================================================
    # CHANNEL B: INTERNAL ROUTING NOTE (Team, Priority, Discrepancy Declaration)
    # =========================================================================
    target_team = "Mutual Funds Operations"
    priority = "P3-Low"
    discrepancy = False
    discrepancy_details = None

    if pattern:
        theme_id = pattern.get("theme_id", "other")
        theme_name = pattern.get("theme_name", "Other feedback")
        review_count = pattern.get("review_count", 0)
        status = pattern.get("status", "one-off")

        if theme_id == "fees_brokerage":
            target_team = "Billing & Brokerage Operations"
            priority = "P1-High" if status == "recurring" else "P2-Medium"
        elif theme_id == "money_movement":
            target_team = "Banking & Payments Desk"
            priority = "P1-High"
        elif theme_id == "trading_charts":
            target_team = "Trading Platform Engineering"
            priority = "P2-Medium"
        elif theme_id == "reliability":
            target_team = "Core App Reliability & SRE"
            priority = "P1-High"

        # Discrepancy Protocol: Clean facts coexisting with high complaint pattern
        if facts and facts.get("status") == "covered" and status == "recurring":
            discrepancy = True
            priority = "P1-High"
            discrepancy_details = (
                f"Discrepancy Detected: Scheme terms explain the fee/rule cleanly, but {review_count} "
                f"users reported recurring friction in '{theme_name}'. "
                f"Flagged for operational review rather than routine closure."
            )

    routing_lines = [
        f"Route to: {target_team} | Priority: {priority}",
        f"Pattern Context: {pattern.get('theme_name', 'General') if pattern else 'General'} "
        f"({pattern.get('review_count', 0) if pattern else 0} reviews, status: {pattern.get('status', 'one-off') if pattern else 'one-off'})",
        f"Compliance Status: PII Redacted={compliance.get('pii_detected', False) if compliance else False}, "
        f"Advice Refused={compliance.get('incoming_has_advice', False) if compliance else False}"
    ]
    if discrepancy and discrepancy_details:
        routing_lines.append(f"Warning: {discrepancy_details}")

    routing_note = "\n".join(routing_lines)

    orchestrator_output: OrchestratorOutput = {
        "reply_draft": reply_draft,
        "citation_url": citation_url,
        "last_checked": CANONICAL_NAV_DATE,
        "sentence_count": num_sentences,
        "routing_note": routing_note,
        "target_team": target_team,
        "priority": priority,
        "discrepancy_flag": discrepancy,
        "discrepancy_details": discrepancy_details
    }

    return {"orchestrator": orchestrator_output, "fired_agents_log": ["orchestrator"]}
