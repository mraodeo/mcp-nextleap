"""
Approval-Gated MCP Tool Layer.
Ensures zero autonomous external write operations without explicit human approval.
Integrates idempotency keys, partial-failure tolerance, and strictly hardcoded zero-auto-send invariant.
"""
from typing import Dict, Any, Optional, Set, List
import hashlib
from src.state import AgentGraphState
from src.config import CANONICAL_NAV_DATE

class MCPExecutionGate:
    """
    Approval-Gated Model Context Protocol (MCP) Execution Barrier.
    Prevents unauthorized outbound emails or external record writes unless human approval is explicitly confirmed.
    """
    _executed_registry: Set[str] = set()

    @classmethod
    def reset_registry(cls) -> None:
        """Clears the in-memory idempotency registry (used for tests and lifecycle resets)."""
        cls._executed_registry.clear()

    @classmethod
    def get_executed_registry(cls) -> Set[str]:
        """Returns a copy of the executed action registry."""
        return set(cls._executed_registry)

    @classmethod
    def _generate_idempotency_key(
        cls,
        state: AgentGraphState,
        action: str,
        custom_key: Optional[str] = None
    ) -> str:
        if custom_key:
            return f"{custom_key}_{action}"
        
        # Build deterministic fingerprint from query, rework count, and refinement count
        raw_text = state.get("raw_input", "") or state.get("sanitized_input", "")
        text_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()[:12]
        rework = state.get("rework_count", 0)
        refinement = state.get("refinement_count", 0)
        return f"{text_hash}_rew{rework}_ref{refinement}_{action}"

    @classmethod
    def append_record_to_doc(
        cls,
        state: AgentGraphState,
        idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Appends approved reply, citation, routing note, and metadata to incident document.
        Raises PermissionError if human approval is not confirmed.
        Guarantees idempotency on repeated invocations.
        """
        if not state.get("is_approved"):
            raise PermissionError("Approval Gate Block: Human approval required before appending to doc.")

        if state.get("is_quarantined"):
            raise PermissionError("Approval Gate Block: Quarantined ticket cannot be executed.")

        orch = state.get("orchestrator")
        if not orch:
            raise ValueError("Cannot execute MCP tool: Missing orchestrator output in state.")

        key = cls._generate_idempotency_key(state, "append_record_to_doc", idempotency_key)

        # Idempotency check: Ignore duplicate executions (EC-13)
        if key in cls._executed_registry:
            return {
                "status": "duplicate_ignored",
                "action": "append_record_to_doc",
                "idempotency_key": key,
                "message": "Action already executed for this idempotency key."
            }

        # Structure document payload
        record = {
            "draft": orch.get("reply_draft", ""),
            "citation": orch.get("citation_url"),
            "routing": orch.get("routing_note", ""),
            "timestamp": orch.get("last_checked", CANONICAL_NAV_DATE),
            "target_team": orch.get("target_team"),
            "priority": orch.get("priority")
        }

        # Mark in idempotency registry
        cls._executed_registry.add(key)

        # Update state execution log if state is mutable
        if "mcp_actions_executed" in state and isinstance(state["mcp_actions_executed"], list):
            state["mcp_actions_executed"].append("append_record_to_doc:success")

        return {
            "status": "success",
            "action": "append_record_to_doc",
            "record": record,
            "idempotency_key": key
        }

    @classmethod
    def create_email_draft(
        cls,
        state: AgentGraphState,
        idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Creates a pending draft in customer support email client.
        Physical Invariant: Strictly hardcoded auto_send = False and dispatch_allowed = False.
        Under no circumstances does this trigger immediate SMTP dispatch.
        """
        if not state.get("is_approved"):
            raise PermissionError("Approval Gate Block: Human approval required before creating draft.")

        if state.get("is_quarantined"):
            raise PermissionError("Approval Gate Block: Quarantined ticket cannot be executed.")

        orch = state.get("orchestrator")
        if not orch:
            raise ValueError("Cannot execute MCP tool: Missing orchestrator output in state.")

        key = cls._generate_idempotency_key(state, "create_email_draft", idempotency_key)

        # Idempotency check: Ignore duplicate executions (EC-13)
        if key in cls._executed_registry:
            return {
                "status": "duplicate_ignored",
                "action": "create_email_draft",
                "idempotency_key": key,
                "message": "Action already executed for this idempotency key."
            }

        draft_payload = {
            "status": "DRAFT",
            "body": orch.get("reply_draft", ""),
            "citation": orch.get("citation_url"),
            "auto_send": False,           # Critical Invariant: Hardcoded False (never auto-send)
            "dispatch_allowed": False     # Physical block against direct transmission
        }

        # Mark in idempotency registry
        cls._executed_registry.add(key)

        # Update state execution log if state is mutable
        if "mcp_actions_executed" in state and isinstance(state["mcp_actions_executed"], list):
            state["mcp_actions_executed"].append("create_email_draft:success")

        return {
            "status": "success",
            "action": "create_email_draft",
            "payload": draft_payload,
            "idempotency_key": key
        }

    @classmethod
    def execute_all(
        cls,
        state: AgentGraphState,
        idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes both approval-gated actions with partial-failure tolerance.
        If an action already succeeded, only the pending action is attempted.
        """
        doc_result = cls.append_record_to_doc(state, idempotency_key=idempotency_key)
        email_result = cls.create_email_draft(state, idempotency_key=idempotency_key)

        return {
            "status": "success",
            "append_record": doc_result,
            "email_draft": email_result
        }


def mcp_execution_node(state: AgentGraphState) -> Dict[str, Any]:
    """
    Optional LangGraph execution node for approval dispatch.
    Wraps MCPExecutionGate and emits updates to mcp_actions_executed and fired_agents_log.
    """
    actions_executed: List[str] = []
    
    if state.get("is_approved"):
        doc_res = MCPExecutionGate.append_record_to_doc(state)
        actions_executed.append(f"append_record_to_doc:{doc_res['status']}")

        email_res = MCPExecutionGate.create_email_draft(state)
        actions_executed.append(f"create_email_draft:{email_res['status']}")

    return {
        "mcp_actions_executed": actions_executed,
        "fired_agents_log": ["mcp_execution_gate"]
    }
