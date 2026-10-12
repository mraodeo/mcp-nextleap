"""
Launcher script for Groww Multi-Agent Support Web UI.
Starts Uvicorn ASGI server hosting the Starlette backend dashboard.
"""
import os
import sys
from pathlib import Path
import uvicorn

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

def start_server(host: str = "0.0.0.0", port: int = 8000):
    print("=" * 80)
    print("GROWW COMPLIANCE-HARDENED MULTI-AGENT OPERATIONS DASHBOARD")
    print("=" * 80)
    print(f"[*] Starting server on {host}:{port}")
    print("[*] Web UI features:")
    print("    - Real-time Multi-Agent Workflow State Visualizer")
    print("    - Live PII Redaction Before/After Inspector")
    print("    - Parallel Specialist Fan-Out Cards (Facts, Pattern, Compliance)")
    print("    - Dual-Channel Synthesis (Customer Draft & Internal Routing)")
    print("    - Automated Reviewer Guardrail Quality Checklist")
    print("    - Approval-Gated MCP Tool Dispatch & Selective Refinement")
    print("    - Automated 40-Scenario Benchmark Scorecard Tab")
    print("=" * 80)
    print("Press CTRL+C to stop the server.\n")

    uvicorn.run("src.web.server:app", host=host, port=port, reload=False, log_level="info")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        port = int(sys.argv[1])
    start_server(port=port)
