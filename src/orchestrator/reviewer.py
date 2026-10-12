"""
Reviewer: Deterministic Compliance & Guardrail Quality Gate.
Evaluates reply drafts against hard regulatory and factual rules before human exposure.
"""
import re
from typing import Dict, Any, List
from src.state import AgentGraphState, ReviewerOutput
from src.sanitizer import PIISanitizer
from src.orchestrator.orchestrator import count_sentences
from src.config import MAX_REPLY_SENTENCES, CANONICAL_NAV_DATE

BANNED_ADVICE_WORDS = [
    r"\bwe recommend\b",
    r"\byou should\b",
    r"\bconsider staying invested\b",
    r"\bbetter to sell\b",
    r"\bgood buy\b",
    r"\bexpect higher returns\b",
    r"\bwe suggest\b",
    r"\bguaranteed return\b"
]

def reviewer_node(state: AgentGraphState) -> Dict[str, Any]:
    """
    Reviewer Guardrail Node: Evaluates draft against hard rules.
    Hard Fails: Uncited facts, advice phrases, surviving PII, length > 3 sentences, missing date.
    """
    orchestrator = state.get("orchestrator")
    facts = state.get("facts")
    rework_count = state.get("rework_count", 0)

    if not orchestrator:
        return {
            "reviewer": {
                "passed": False,
                "failure_reasons": ["No orchestrator output found in state"],
                "review_attempt": rework_count + 1
            },
            "fired_agents_log": ["reviewer"]
        }

    draft = orchestrator.get("reply_draft", "")
    failures: List[str] = []

    # 1. Surviving PII check
    _, pii_check = PIISanitizer.sanitize(draft)
    if pii_check["has_pii"]:
        failures.append(f"Surviving PII detected in draft: {pii_check['detected_types']}")

    # 2. Advice Language Check
    for pattern in BANNED_ADVICE_WORDS:
        if re.search(pattern, draft, re.IGNORECASE):
            failures.append(f"Banned investment advice phrase detected: '{pattern}'")

    # 3. Sentence Count Check
    num_sentences = count_sentences(draft)
    if num_sentences > MAX_REPLY_SENTENCES:
        failures.append(f"Draft exceeds {MAX_REPLY_SENTENCES} sentences (found {num_sentences})")

    # 4. Mandatory Timestamp Check
    if CANONICAL_NAV_DATE not in draft:
        failures.append(f"Missing mandatory last checked verification date '{CANONICAL_NAV_DATE}'")

    # 5. Citation Check on Factual Claims
    if facts and facts.get("status") == "covered":
        source_url = facts.get("source_url")
        if not source_url or source_url not in draft:
            failures.append("Factual scheme claim missing canonical source_url citation link")

    passed = len(failures) == 0

    reviewer_output: ReviewerOutput = {
        "passed": passed,
        "failure_reasons": failures,
        "review_attempt": rework_count + 1
    }

    return {"reviewer": reviewer_output, "fired_agents_log": ["reviewer"]}
