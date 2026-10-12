"""
Interactive CLI Runner for Groww Support Reply System.
Demonstrates:
- Pre-graph PII sanitization.
- Parallel specialist execution (Facts, Pattern, Compliance).
- Dual-channel orchestrator synthesis (Customer Draft + Internal Routing Note).
- Automated Reviewer guardrails.
- Selective human refinement.
- Approval-gated MCP execution (Document Append + Email Draft with ZERO auto-send).
"""
import sys
from typing import Optional
from src.graph import create_support_graph, apply_refinement
from src.mcp_tools import MCPExecutionGate

def run_ticket(query: str, auto_approve: bool = True, interactive: bool = False):
    """
    Runs a customer support complaint ticket through the complete multi-agent graph.
    """
    print("=" * 80)
    print(f"INCOMING SUPPORT TICKET: {query}")
    print("=" * 80)

    graph = create_support_graph()
    state = graph.invoke({"raw_input": query})

    # [1] PII SANITIZATION
    print(f"\n[1] PII SANITIZATION ENGINE:")
    print(f"    Redacted Text: \"{state['sanitized_input']}\"")
    pii_types = state['pii_metadata']['detected_types']
    print(f"    Detected PII:  {pii_types if pii_types else 'None (Clean Input)'}")

    # [2] PARALLEL SPECIALIST RESULTS
    print(f"\n[2] PARALLEL SPECIALIST FAN-OUT RESULTS:")
    facts = state.get('facts')
    pattern = state.get('pattern')
    comp = state.get('compliance')

    if facts:
        print(f"    - Facts Specialist:      Status={facts['status']} | Scheme={facts.get('scheme_id')} | Section={facts.get('section_title')}")
        if facts.get('source_url'):
            print(f"                             Citation={facts['source_url']}")
    if pattern:
        print(f"    - Pattern Specialist:    Theme={pattern['theme_name']} | Count={pattern['review_count']} reviews | Status={pattern['status']}")
    if comp:
        print(f"    - Compliance Specialist: AdviceFlag={comp['incoming_has_advice']} | PerfFlag={comp['incoming_has_performance_claim']} | PIIFlag={comp['pii_detected']}")

    # [3] ORCHESTRATOR OUTPUTS
    orch = state.get('orchestrator')
    print(f"\n[3] ORCHESTRATOR SYNTHESIS:")
    if orch:
        print(f"    Channel A: Customer Reply Draft ({orch['sentence_count']} sentences, Last checked: {orch['last_checked']}):")
        print(f"    \"{orch['reply_draft']}\"")
        print(f"\n    Channel B: Internal Routing Note:")
        for line in orch['routing_note'].split('\n'):
            print(f"    | {line}")

    # [4] AUTOMATED REVIEWER CHECK
    rev = state.get('reviewer')
    print(f"\n[4] AUTOMATED REVIEWER GUARDRAIL:")
    if rev:
        status_str = "PASSED" if rev["passed"] else "FAILED (REWORK / QUARANTINE)"
        print(f"    Status: {status_str} (Attempt #{rev['review_attempt']})")
        if not rev["passed"]:
            print(f"    Failure Reasons: {rev['failure_reasons']}")

    # [5] HUMAN APPROVAL & MCP TOOL EXECUTION
    if rev and rev["passed"]:
        approved = auto_approve
        if interactive:
            user_choice = input("\n[?] Approve and dispatch MCP actions? (y/n/edit): ").strip().lower()
            if user_choice.startswith("e"):
                feedback = input("    Enter refinement feedback: ")
                state = apply_refinement(state, feedback)
                print(f"\n    [Refined Draft]: {state['orchestrator']['reply_draft']}")
                approved = input("    Approve refined draft? (y/n): ").strip().lower() == "y"
            else:
                approved = (user_choice == "y")

        if approved:
            print("\n[5] APPROVAL-GATED MCP TOOL EXECUTION:")
            state["is_approved"] = True
            try:
                doc_res = MCPExecutionGate.append_record_to_doc(state)
                email_res = MCPExecutionGate.create_email_draft(state)
                print(f"    [OK] Document Append: Status={doc_res['status']} | Action={doc_res['action']}")
                print(f"    [OK] Email Draft:     Status={email_res['status']} | AutoSend={email_res['payload']['auto_send']} (DRAFT strictly enforced)")
            except Exception as e:
                print(f"    [FAIL] MCP Action Blocked: {e}")
        else:
            print("\n[5] APPROVAL GATE: Ticket pending human review. No external actions executed.")
    else:
        print("\n[5] APPROVAL GATE: Blocked by Reviewer. Ticket routed to quarantine.")

    print("=" * 80 + "\n")
    return state

def main():
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg == "--eval":
            from tests.eval_runner import MultiAgentEvaluator
            evaluator = MultiAgentEvaluator()
            results = evaluator.run_full_evaluation()
            print(results["report"])
            return
        elif arg == "--interactive":
            print("Entering interactive mode. Type 'quit' or 'exit' to end.\n")
            while True:
                user_q = input("Enter support query: ").strip()
                if user_q.lower() in ["quit", "exit"]:
                    break
                if user_q:
                    run_ticket(user_q, interactive=True)
            return
        else:
            # Custom query from CLI argument
            custom_query = " ".join(sys.argv[1:])
            run_ticket(custom_query, auto_approve=True)
            return

    # Default canonical demonstration suite
    test_queries = [
        "Why was I charged an exit load on HDFC Large Cap Fund Direct Growth?",
        "My phone number is 9876543210 and PAN is ABCDE1234F. Can you refund the exit load?",
        "Money was deducted from my account, please refund immediately!",
        "Should I redeem my gold fund now or hold for higher returns?",
        "What is the exit load for Parag Parikh Flexi Cap Fund?"
    ]

    print("=" * 80)
    print("GROWW COMPLIANCE-HARDENED MULTI-AGENT SUPPORT REPLY SYSTEM")
    print("Running 5 Canonical Acceptance Scenarios")
    print("=" * 80 + "\n")

    for q in test_queries:
        run_ticket(q, auto_approve=True)

if __name__ == "__main__":
    main()
