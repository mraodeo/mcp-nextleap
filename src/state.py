"""
Type-safe state definitions for LangGraph workflow.
"""
from typing import TypedDict, List, Optional, Literal, Dict, Any, Annotated
import operator

class PIIArtifact(TypedDict):
    has_pii: bool
    detected_types: List[str]
    redacted_text: str

class FactsOutput(TypedDict):
    scheme_id: Optional[str]
    scheme_name: Optional[str]
    section_title: Optional[str]
    extracted_text: str
    source_url: Optional[str]
    last_checked_date: str
    status: Literal["covered", "not_covered"]
    searched_schemes: List[str]
    searched_sections: List[str]

class PatternOutput(TypedDict):
    theme_id: str
    theme_name: str
    status: Literal["recurring", "rising", "one-off"]
    review_count: int
    review_window: str
    in_top_themes: bool

class ComplianceOutput(TypedDict):
    incoming_has_advice: bool
    incoming_has_performance_claim: bool
    pii_detected: bool
    detected_pii_types: List[str]
    compliance_passed: bool

class OrchestratorOutput(TypedDict):
    reply_draft: str
    citation_url: Optional[str]
    last_checked: str
    sentence_count: int
    routing_note: str
    target_team: str
    priority: Literal["P1-High", "P2-Medium", "P3-Low"]
    discrepancy_flag: bool
    discrepancy_details: Optional[str]

class ReviewerOutput(TypedDict, total=False):
    passed: bool
    status: str
    failure_reasons: List[str]
    review_attempt: int
    checks: Dict[str, bool]

class AgentGraphState(TypedDict):
    # Inputs & Sanitization
    raw_input: str
    sanitized_input: str
    pii_metadata: PIIArtifact

    # Parallel Specialist Outputs (Fan-Out)
    facts: Optional[FactsOutput]
    pattern: Optional[PatternOutput]
    compliance: Optional[ComplianceOutput]

    # Orchestration & Guardrail
    orchestrator: Optional[OrchestratorOutput]
    reviewer: Optional[ReviewerOutput]

    # Control Flow & Audit
    rework_count: int
    refinement_count: int
    refinement_feedback: Optional[str]
    active_refinement_target: Optional[Literal["orchestrator", "facts", "pattern"]]
    fired_agents_log: Annotated[List[str], operator.add]

    # Human-in-the-Loop & MCP
    is_approved: bool
    is_quarantined: bool
    mcp_actions_executed: Annotated[List[str], operator.add]
