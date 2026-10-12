"""
LangGraph Workflow Assembly: Fan-out, Fan-in, Rework, and Refinement.
Compiles the state graph connecting sanitizer, parallel specialist agents, orchestrator, and reviewer.
"""
from typing import Literal, Dict, Any, Optional
from langgraph.graph import StateGraph, START, END

from src.state import AgentGraphState
from src.sanitizer import PIISanitizer
from src.agents.facts_agent import facts_agent_node
from src.agents.pattern_agent import pattern_agent_node
from src.agents.compliance_agent import compliance_agent_node
from src.orchestrator.orchestrator import orchestrator_node
from src.orchestrator.reviewer import reviewer_node
from src.config import MAX_REWORK_ATTEMPTS, MAX_REFINEMENT_ATTEMPTS

# ==============================================================================
# 1. NODE DEFINITIONS
# ==============================================================================

def sanitizer_node(state: AgentGraphState) -> Dict[str, Any]:
    """
    Entry Node: Redacts PII before state reaches specialist agents or model calls.
    """
    raw_input = state.get("raw_input", "")
    sanitized, pii_artifact = PIISanitizer.sanitize(raw_input)
    return {
        "sanitized_input": sanitized,
        "pii_metadata": pii_artifact,
        "rework_count": state.get("rework_count", 0),
        "refinement_count": state.get("refinement_count", 0),
        "is_approved": False,
        "is_quarantined": False,
        "fired_agents_log": ["sanitizer"]
    }

def quarantine_node(state: AgentGraphState) -> Dict[str, Any]:
    """
    Quarantine Node: Reached when reviewer fails twice (after 1 rework cycle).
    Blocks approval and flags the draft as rejected.
    """
    return {
        "is_quarantined": True,
        "is_approved": False,
        "fired_agents_log": ["quarantine"]
    }

def human_review_node(state: AgentGraphState) -> Dict[str, Any]:
    """
    Human Review Node: Draft passed all automated guardrails and is ready for human operator review.
    """
    return {
        "fired_agents_log": ["human_review"]
    }

# ==============================================================================
# 2. CONDITIONAL ROUTING FUNCTIONS
# ==============================================================================

def route_reviewer(state: AgentGraphState) -> Literal["human_review", "orchestrator", "quarantine"]:
    """
    Conditional router after Reviewer:
    - If passed -> human_review
    - If failed & rework_count < 1 -> orchestrator (increments rework_count)
    - If failed & rework_count >= 1 -> quarantine (locks send)
    """
    reviewer = state.get("reviewer")
    rework_count = state.get("rework_count", 0)

    if reviewer and reviewer.get("passed", False):
        return "human_review"

    if rework_count < MAX_REWORK_ATTEMPTS:
        # Increment rework counter in state
        state["rework_count"] = rework_count + 1
        return "orchestrator"

    return "quarantine"

def parse_refinement_intent(feedback: str) -> Literal["orchestrator", "facts", "pattern"]:
    """
    Parses human reviewer feedback to route ONLY to affected agents.
    Supports English and Hinglish operational keywords.
    """
    feedback_lower = feedback.lower()
    if any(k in feedback_lower for k in ["short", "shorter", "concise", "rephrase", "tone", "word", "length", "chhota", "polite"]):
        return "orchestrator"
    elif any(k in feedback_lower for k in [
        "scheme", "fund", "hdfc", "exit load", "nav", "tax", "load", "different scheme",
        "stamp duty", "clause", "galat", "sahi", "check karo"
    ]):
        return "facts"
    elif any(k in feedback_lower for k in [
        "pattern", "theme", "review", "trend", "fee issue", "frequency", "recurring",
        "cluster", "complaints", "shikayat", "volume"
    ]):
        return "pattern"
    return "orchestrator"

# ==============================================================================
# 3. BUILD & COMPILE GRAPH WORKFLOW
# ==============================================================================

def create_support_graph():
    """
    Builds and compiles the production LangGraph state machine.
    Structure:
    START -> sanitizer -> [facts, pattern, compliance] (in parallel) -> orchestrator -> reviewer
    reviewer -> (conditional) -> human_review | orchestrator | quarantine
    """
    workflow = StateGraph(AgentGraphState)

    # Register All Nodes
    workflow.add_node("sanitizer", sanitizer_node)
    workflow.add_node("facts", facts_agent_node)
    workflow.add_node("pattern", pattern_agent_node)
    workflow.add_node("compliance", compliance_agent_node)
    workflow.add_node("orchestrator", orchestrator_node)
    workflow.add_node("reviewer", reviewer_node)
    workflow.add_node("quarantine", quarantine_node)
    workflow.add_node("human_review", human_review_node)

    # 1. Entry to Sanitizer
    workflow.add_edge(START, "sanitizer")

    # 2. Strict Parallel Fan-Out: Fork from Sanitizer to 3 Specialists concurrently
    workflow.add_edge("sanitizer", "facts")
    workflow.add_edge("sanitizer", "pattern")
    workflow.add_edge("sanitizer", "compliance")

    # 3. Fan-In to Orchestrator: Orchestrator waits for all 3 specialists
    workflow.add_edge("facts", "orchestrator")
    workflow.add_edge("pattern", "orchestrator")
    workflow.add_edge("compliance", "orchestrator")

    # 4. Orchestrator to Reviewer Gate
    workflow.add_edge("orchestrator", "reviewer")

    # 5. Conditional Routing from Reviewer
    workflow.add_conditional_edges(
        "reviewer",
        route_reviewer,
        {
            "human_review": "human_review",
            "orchestrator": "orchestrator",
            "quarantine": "quarantine"
        }
    )

    # 6. Terminal Edges
    workflow.add_edge("quarantine", END)
    workflow.add_edge("human_review", END)

    return workflow.compile()

# ==============================================================================
# 4. SELECTIVE HUMAN REFINEMENT RUNNER
# ==============================================================================

def apply_refinement(state: AgentGraphState, feedback: str) -> AgentGraphState:
    """
    Executes selective refinement when human reviewer pushes back.
    Only affected agent(s) re-run; unaffected specialist state is preserved.
    Capped at MAX_REFINEMENT_ATTEMPTS (5).
    """
    current_refinements = state.get("refinement_count", 0)
    if current_refinements >= MAX_REFINEMENT_ATTEMPTS:
        # Refinement ceiling reached; lock further automated cycles
        return state

    target = parse_refinement_intent(feedback)
    state["refinement_count"] = current_refinements + 1
    state["refinement_feedback"] = feedback
    state["active_refinement_target"] = target

    # Selective agent execution
    if target == "facts":
        # Human asked about different scheme/facts
        facts_res = facts_agent_node(state)
        state["facts"] = facts_res["facts"]
        state["fired_agents_log"] = state.get("fired_agents_log", []) + ["facts_agent"]

    elif target == "pattern":
        # Human asked to recheck theme/pattern
        pattern_res = pattern_agent_node(state)
        state["pattern"] = pattern_res["pattern"]
        state["fired_agents_log"] = state.get("fired_agents_log", []) + ["pattern_agent"]

    # In all refinement cases, Orchestrator synthesizes the new draft
    orch_res = orchestrator_node(state)
    state["orchestrator"] = orch_res["orchestrator"]
    state["fired_agents_log"] = state.get("fired_agents_log", []) + ["orchestrator"]

    # Re-evaluate with Reviewer
    rev_res = reviewer_node(state)
    state["reviewer"] = rev_res["reviewer"]
    state["fired_agents_log"] = state.get("fired_agents_log", []) + ["reviewer"]

    return state
