# Groww Multi-Agent Operations Portal
### SEBI-Compliant, Dual-Channel Customer Support Reply & Escalation Engine

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![LangGraph](https://img.shields.io/badge/orchestration-LangGraph%200.2-green.svg)](https://github.com/langchain-ai/langgraph)
[![Tests Passing](https://img.shields.io/badge/tests-75%2F75%20passed-brightgreen.svg)](tests/)
[![Compliance](https://img.shields.io/badge/compliance-SEBI%20RA%202014-orange.svg)](#compliance--sebi-regulatory-guardrails)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📌 Executive Summary & Problem Context

In high-volume FinTech applications like **Groww**, customer support tickets regarding mutual fund deductions (e.g., *"Why was I charged an exit load on my redemption?"*) cannot be handled by a naive generic Large Language Model (LLM).

### The Three-Way Tension in Financial Support:
1. **The Statutory Fact**: Lives inside legal Scheme Information Documents (SIDs) and Key Information Memorandums (KIMs). Hallucinating terms or providing outdated exit load percentages creates immediate financial liability.
2. **The Voice-of-Customer Pattern**: Whether 40 other users reported identical UPI deductions or order glitches this morning dictates whether this ticket is an isolated informational inquiry or a systemic production incident requiring urgent engineering escalation.
3. **The Regulatory Compliance Barrier**: Under **SEBI (Research Analysts) Regulations, 2014**, unauthorized investment advice, return forecasts, or speculative advice (*"you may want to hold your fund longer"*) are strictly prohibited. Furthermore, customer PII (PAN, Mobile, Aadhaar, OTP) must never be retained, logged, or reflected back in customer replies.

### The Multi-Agent Solution:
A naive single-prompt LLM attempts to address the fact, forgets compliance, leaks PII, and hallucinates speculative advice.

This system implements a **LangGraph-orchestrated multi-agent architecture** featuring:
- **Pre-Graph Deterministic PII Redaction** (Regex + Checksums before graph state creation)
- **Parallel Specialist Fan-Out** (`Facts Specialist`, `Pattern Specialist`, `Compliance Specialist`)
- **Dual-Channel Synthesis** (Channel A: Customer Support Reply $\le 3$ sentences, 1 citation link, `25-Jun-2026` verification date; Channel B: Internal Ops Routing Note with Discrepancy Detection)
- **Automated Reviewer Quality Gate** (Hard 1-rework cap with quarantine failsafe)
- **Selective Human Refinement Engine** (Targeted re-execution capped at 5 rounds)
- **Approval-Gated MCP Tool Dispatch** (Zero autonomous SMTP dispatch; hardcoded `auto_send = False`)

---

## 🏛️ System Architecture

```
                                ┌──────────────────────────────────────┐
                                │       Incoming Customer Ticket       │
                                └──────────────────┬───────────────────┘
                                                   │
                                                   ▼
                                ┌──────────────────────────────────────┐
                                │   Deterministic Pre-Graph Redactor   │
                                │    (PAN, Phone, Aadhaar, OTP, Email) │
                                └──────────────────┬───────────────────┘
                                                   │ Clean Sanitized State
                                                   ▼
                         ┌─────────────────────────────────────────────────────┐
                         │               LangGraph Parallel Fan-Out            │
                         └───────┬───────────────────┬───────────────────┬─────┘
                                 │                   │                   │
                                 ▼                   ▼                   ▼
                     ┌──────────────────────┐ ┌──────────────┐ ┌───────────────────┐
                     │   Facts Specialist   │ │Pattern Agent │ │ Compliance Agent  │
                     │  (Scheme SID Sourcing│ │ (VoC Cluster │ │(Anti-Advice/Return│
                     │   & Exact Clause Cit)│ │  & Freq/Sev) │ │ Guardrail Checks) │
                     └───────────┬──────────┘ └──────┬───────┘ └─────────┬─────────┘
                                 │                   │                   │
                                 └───────────────────┼───────────────────┘
                                                     ▼
                                      ┌──────────────────────────────┐
                                      │ Orchestrator Fan-In Synthes  │
                                      │  Channel A: Customer Draft   │
                                      │  Channel B: Ops Routing Note │
                                      └──────────────┬───────────────┘
                                                     │
                                                     ▼
                                      ┌──────────────────────────────┐
                     ┌───────────────►│  Automated Reviewer Gate     │◄──────────────┐
                     │                │  (4 Regulatory Checkpoints)  │               │
                     │                └──────────────┬───────────────┘               │
               Rework Loop                           │                               │
             (Max 1 Attempt)             [PASS]      │      [FAIL 2x]                │
                     │                     ┌─────────┴─────────┐                     │
                     │                     ▼                   ▼                     │
                     │            ┌─────────────────┐ ┌──────────────────┐           │
                     └────────────┤  Human Approval │ │ QUARANTINE LOCK  │           │
                                  │  HITL Interface │ │ (Manual Escalate)│           │
                                  └────────┬────────┘ └──────────────────┘           │
                                           │                                         │
                                [Selective Refinement: ≤5 Rounds] ───────────────────┘
                                           │
                                     [Human Clicks
                                       Approve]
                                           ▼
                                  ┌──────────────────┐
                                  │   MCP Tool Gate  │
                                  │ ├── append_record│
                                  │ └── email_draft  │
                                  │   (auto_send=F)  │
                                  └──────────────────┘
```

---

## 🚀 Key Functional Modules

### 1. Pre-Graph PII Redactor (`src/sanitizer.py`)
- Executes **strictly before** any model call, prompt formatting, or state logging.
- Deterministic regex patterns coupled with Luhn/Indian statutory checksums redacts:
  - **PAN**: `[A-Z]{5}[0-9]{4}[A-Z]{1}` $\to$ `[PAN_REDACTED]`
  - **Indian Mobile Numbers**: `(?:(?:\+91|91|0)[- ]?)?[6-9]\d{9}` $\to$ `[MOBILE_REDACTED]`
  - **Aadhaar**: `\b\d{4}[ -]?\d{4}[ -]?\d{4}\b` $\to$ `[AADHAAR_REDACTED]`
  - **Emails & OTPs**: Fully sanitized.
- False-positive currency protection ensures monetary amounts (e.g. `Rs 50,000`, `10000`, `1%`) are preserved.

### 2. Parallel Specialist Trio (`src/agents/`)
- **Facts Specialist** (`src/agents/facts_agent.py`):
  - Sources statutory ground truth from parsed scheme SIDs (HDFC Large Cap, Mid Cap, Small Cap, Gold ETF FoF, Silver ETF FoF).
  - Extracts exact contractual clauses (e.g., exit load tiers, stamp duty).
  - Emits the single verified citation URL (e.g., `https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth`).
  - Returns `status="not_covered"` for external or unlisted funds without hallucinating.
- **Pattern Specialist** (`src/agents/pattern_agent.py`):
  - Ingests 1,650 normalized Play Store reviews across 5 analyzed thematic clusters (`trading_charts`, `money_movement`, `reliability`, `fees_brokerage`, `other`).
  - Identifies feedback volume, frequency (`recurring`, `rising`, `one-off`), and dataset window (`2026-04-12 to 2026-07-04`).
- **Compliance Specialist** (`src/agents/compliance_agent.py`):
  - Scans for advice solicitation, speculative inquiries, or performance return promises.
  - Verifies zero surviving raw PII.

### 3. Orchestrator Synthesizer (`src/orchestrator/orchestrator.py`)
Produces a strict **Dual-Channel Deliverable**:
- **Channel A: Customer Support Reply Draft**:
  - $\le 3$ sentences maximum.
  - Strictly grounded in statutory facts; zero speculation.
  - Exactly 1 verified citation link.
  - Fixed statutory verification timestamp: `25-Jun-2026`.
- **Channel B: Internal Incident Routing Note**:
  - Target escalation team (`Growth & Retention`, `Payments & Banking`, `Compliance Ops`).
  - Incident priority tag (`P1 - Critical` vs `P2 - Standard`) driven by VoC cluster volume.
  - **Discrepancy Protocol**: Detects contradictions between user allegations (e.g., claiming unfair exit load on an investment held for 2 years) and verified SID terms.

### 4. Automated Reviewer Guardrail (`src/orchestrator/reviewer.py`)
- Independent verification node testing 4 mandatory compliance invariants:
  1. No advice violation (SEBI RA Regs 2014)
  2. Grounded verification date (`25-Jun-2026`) present
  3. Single valid citation URL present
  4. Sentence length strictly $\le 3$ sentences
  5. Zero PII leakage
- **1-Rework Cap**: If rejected, routes back to Orchestrator once with corrective feedback.
- **Quarantine Failsafe**: If a second failure occurs, the ticket is permanently quarantined and MCP tools are blocked.

### 5. Selective Human Refinement (`src/graph.py`)
- Allows support operators to push back (e.g., *"make it shorter"*, *"check Mid Cap terms"*).
- Intent classification triggers **selective specialist re-execution** rather than re-running the entire pipeline.
- Enforces a hard budget ceiling: **maximum 5 refinement rounds**.

### 6. Approval-Gated MCP Dispatch (`src/mcp_tools.py`)
- **Zero Auto-Send Invariant**: Autonomously emailing financial customers is strictly prevented. Drafts are created with `auto_send = False` and status `DRAFT`.
- `append_record_to_doc`: Appends sanitized draft, routing note, and timestamp to the central compliance ledger.
- `create_email_draft`: Stages customer support draft in the support queue.
- Built-in cryptographic idempotency registry prevents duplicate dispatches.

---

## 💻 Tech Stack

| Component | Technology | Rationale |
|---|---|---|
| **Language** | Python 3.10+ | Robust type hinting (`TypedDict`, `Annotated`) |
| **Workflow Engine** | LangGraph 0.2 | Native DAG fan-out/fan-in and conditional routing loops |
| **State Validation** | Pydantic v2 | High-speed schema validation and type safety |
| **Web API Backend** | Starlette / Uvicorn | Lightweight ASGI server with low latency and clean endpoints |
| **Frontend UI** | Vanilla HTML5 / Modern CSS / JS | 3-column FinTech Cockpit, dynamic SVG DAG, zero build dependencies |
| **Testing Harness** | Pytest / Pytest-Asyncio | 75 unit, integration, and adversarial acceptance tests |

---

## 📊 Comprehensive Evaluation & Benchmark Scorecard

The system was evaluated using an automated 40-scenario benchmark suite ([`tests/eval_runner.py`](tests/eval_runner.py)) comprising:
- **5 Canonical Branches** (Clean Fact, Out of Scope, Recurring Theme, PII Injection, Advice Probe)
- **20 Real Play Store Customer Reviews** (Ratings 1-5 across all app modules)
- **15 Adversarial Red-Team Payloads** (Prompt injections, spaced PANs, Hindi/Hinglish, return guarantees)

| Regulatory Evaluation Metric | Target Threshold | Measured Score | Release Gate Status |
|---|---|---|---|
| **SEBI Advice Deflection Rate** | 100.0% | **100.0%** | ✅ PASSED |
| **Zero-PII Leakage Rate** | 100.0% | **100.0%** | ✅ PASSED |
| **Verification Date Grounding Rate** (`25-Jun-2026`) | 100.0% | **100.0%** | ✅ PASSED |
| **Source Citation Grounding Rate** | 100.0% | **100.0%** | ✅ PASSED |
| **Draft $\le 3$ Sentence Cap Adherence** | $\ge 95.0\%$ | **100.0%** | ✅ PASSED |
| **Discrepancy Protocol Trigger Accuracy** | 100.0% | **100.0%** | ✅ PASSED |
| **Zero Autonomous SMTP Dispatch** | 100.0% | **100.0%** | ✅ PASSED |

**Total Suite Result**: **75 tests passing across 8 test suites (100% pass rate)**.

---

## ⚡ Quick Start & Setup

### 1. Installation
Clone the repository and install dependencies:
```bash
git clone https://github.com/mraodeo/mcp-nextleap.git
cd mcp-nextleap
git checkout multi-agent-system

python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Run the Full Test Suite
Execute the 75-test acceptance and regression suite:
```bash
python tests/run_tests.py
# Or using pytest:
pytest tests/ -v
```

### 3. Launch the FinTech Operations Cockpit (Web UI)
Launch the local ASGI server:
```bash
python app_ui.py
```
Open your browser at **`http://localhost:8000`** to access the 3-column Cockpit.

### 4. Interactive CLI Mode
To run individual queries directly in the terminal:
```bash
python run.py --query "Why was I charged an exit load on HDFC Large Cap Fund? PAN: ABCDE1234F"
```

---

## 🌐 Cloud Deployment (Render.com)

The repository includes a production-ready [Procfile](Procfile) and [render.yaml](render.yaml) blueprint.

### Deployment Configuration:
1. **Repository**: Connect `https://github.com/mraodeo/mcp-nextleap.git` (Branch: `multi-agent-system`).
2. **Environment**: Python 3.
3. **Build Command**:
   ```bash
   pip install -r requirements.txt
   ```
4. **Start Command**:
   ```bash
   python -m uvicorn src.web.server:app --host 0.0.0.0 --port $PORT
   ```

---

## 📂 Directory Layout

```
MultiAgent/
├── Data/
│   ├── parsed/                   # 5 Scheme SID parsed disclosures (NAV: 25-Jun-2026)
│   ├── normalized_reviews.json   # 1,650 Play Store customer reviews
│   └── analyzed_themes.json      # 5 VoC theme clusters (volume, ratings, score)
├── src/
│   ├── config.py                 # Grounding date, sentence limit, constants
│   ├── state.py                  # AgentGraphState schema with reducer annotations
│   ├── sanitizer.py              # Regex + checksum pre-graph PII redactor
│   ├── data_loader.py            # Singleton loader for SIDs and VoC review clusters
│   ├── agents/                   # Parallel Specialist Trio
│   │   ├── facts_agent.py        # SID extraction and single-link citation sourcing
│   │   ├── pattern_agent.py      # VoC cluster matching and frequency calculation
│   │   └── compliance_agent.py   # Anti-advice and return guarantee detector
│   ├── orchestrator/
│   │   ├── orchestrator.py       # Dual-channel synthesizer & discrepancy detection
│   │   └── reviewer.py           # 4-point compliance guardrail with 1-rework cap
│   ├── graph.py                  # Compiled LangGraph workflow with selective refinement
│   ├── mcp_tools.py              # Approval-gated tools with auto_send=False guarantee
│   └── web/                      # Web Dashboard Backend & Static Assets
│       ├── server.py             # Starlette ASGI API server
│       └── static/
│           ├── index.html        # 3-Column FinTech Cockpit UI
│           ├── style.css         # Modern Dark Glassmorphic Design System
│           └── app.js            # SVG DAG animator, live validator, shortcuts
├── tests/                        # 75-Test Comprehensive Suite
│   ├── test_sanitizer.py         # PII redactor edge cases
│   ├── test_data_loader.py       # Corpus loading and parsing integrity
│   ├── test_specialists.py       # Parallel agents behavior
│   ├── test_reviewer.py          # Reviewer rework loops and sentence counting
│   ├── test_graph.py             # End-to-end LangGraph execution & refinement
│   ├── test_mcp_tools.py         # Idempotency and approval gates
│   ├── test_acceptance_suite.py  # 5 canonical branches, 20 reviews, 15 adversarial tests
│   ├── test_web_server.py        # Starlette REST endpoints
│   ├── eval_runner.py            # Quantitative 40-scenario benchmark harness
│   └── run_tests.py              # Zero-dependency test runner
├── app_ui.py                     # Local & Cloud ASGI launcher
├── run.py                        # Terminal CLI runner
├── Procfile                      # Render/PaaS deployment specification
├── render.yaml                   # Infrastructure-as-code deployment blueprint
├── requirements.txt              # Production Python dependencies
└── README.md                     # Project documentation
```

---

## ⚖️ License & Disclaimers

This project is developed for educational and portfolio demonstration purposes based on the Groww customer support reply problem statement. Grounded data represents snapshot public disclosures as of 25-Jun-2026.
