# Implementation Plan: Multi-Agent Support Reply System for Groww

## 1. Implementation Overview & Technology Stack

This document serves as the complete, end-to-end technical implementation plan and blueprint for the **Groww Multi-Agent Support Reply System**, directly translating the architectural specifications from [architecture.md](file:///c:/Users/mange/Documents/AI%20Projects/MultiAgent/architecture.md) and the operational constraints from [Problemstatement.md](file:///c:/Users/mange/Documents/AI%20Projects/MultiAgent/Problemstatement.md) into clean, production-grade Python code.

### 1.1 Core Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Graph Orchestration** | `langgraph` (v0.2+) | State graph, parallel fan-out/fan-in, conditional rework loops |
| **Model Abstraction** | `langchain-core` / `litellm` / `google-genai` | Structured output / JSON mode classification models |
| **State & Schema Validation** | `pydantic` (v2+) & `typing.TypedDict` | Type-safe graph state, agent IO schemas |
| **Data Layer** | Built-in `json`, `pathlib` | Fast in-memory caching of scheme documents & theme clusters |
| **PII & Guardrails Engine** | Standard `re` (Regex) + Deterministic Heuristics | Zero-retention sanitization of PAN, Aadhaar, accounts, phone, email, OTP |
| **Tool Execution** | Model Context Protocol (`mcp`) / Python Callbacks | Approval-gated document append and email draft actions |
| **Testing & Acceptance** | `pytest`, `pytest-asyncio` | Unit tests, 4-branch coverage, 20-review batch benchmark |

### 1.2 Target Project Structure

```
MultiAgent/
├── architecture.md                     # Architectural specification
├── implementation-plan.md              # This implementation plan and blueprint
├── edge-case.md                        # Failure mode and edge-case defenses
├── eval.md                             # Evaluation metrics and benchmarks
├── Problemstatement.md                 # Canonical problem statement
├── requirements.txt                    # Project dependencies
├── run.py                              # Interactive CLI runner
│
├── Data/                               # Canonical data directory
│   ├── normalized_reviews.json         # 1,650 Play Store reviews
│   ├── analyzed_themes.json            # 5 Clustered feedback themes
│   └── parsed/
│       ├── parse_manifest.json         # Manifest (5 schemes, NAV date 25-Jun-2026)
│       ├── large_cap.json              # HDFC Large Cap Direct Growth
│       ├── mid_cap.json                # HDFC Mid Cap Direct Growth
│       ├── small_cap.json              # HDFC Small Cap Direct Growth
│       ├── gold_fof.json               # HDFC Gold ETF FoF Direct Growth
│       └── silver_fof.json             # HDFC Silver ETF FoF Direct Growth
│
├── src/
│   ├── __init__.py
│   ├── config.py                       # Paths, constants, and environment config
│   ├── state.py                        # Graph State TypedDict definitions
│   ├── sanitizer.py                    # Pre-graph PII redaction engine
│   ├── data_loader.py                  # In-memory corpus loader and indexer
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── facts_agent.py              # Parallel Node 1: Scheme classification & extraction
│   │   ├── pattern_agent.py            # Parallel Node 2: Theme classification & review analytics
│   │   └── compliance_agent.py         # Parallel Node 3: Advice & performance check
│   │
│   ├── orchestrator/
│   │   ├── __init__.py
│   │   ├── orchestrator.py             # Fan-in node: Synthesizer & Router
│   │   └── reviewer.py                 # Automated Quality & Compliance Guardrail Node
│   │
│   ├── graph.py                        # LangGraph workflow assembly and compilation
│   └── mcp_tools.py                    # Approval-gated Document & Email tools
│
└── tests/
    ├── test_sanitizer.py               # PII pattern and zero-leakage tests
    ├── test_specialists.py             # Unit tests for Facts, Pattern, Compliance
    ├── test_reviewer.py                # Reviewer hard fails & rework cycle tests
    └── test_acceptance_suite.py        # 20-review batch and 4 branch tests
```

---

## 2. Dependencies & Configuration

### 2.1 `requirements.txt`
```text
langgraph>=0.2.20
langchain-core>=0.3.0
pydantic>=2.7.0
litellm>=1.40.0
pytest>=8.0.0
pytest-asyncio>=0.23.0
python-dotenv>=1.0.0
```

### 2.2 `src/config.py`
Centralizes immutable paths, canonical constants, and the closed scheme/theme enumerations.

```python
"""
Configuration and constants for the Groww Multi-Agent System.
"""
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

# Robust data path resolution (handles both 'Data' and 'data')
DATA_DIR = BASE_DIR / "Data"
if not DATA_DIR.exists():
    DATA_DIR = BASE_DIR / "data"

PARSED_DIR = DATA_DIR / "parsed"
SCHEMES_MANIFEST_PATH = PARSED_DIR / "parse_manifest.json"
NORMALIZED_REVIEWS_PATH = DATA_DIR / "normalized_reviews.json"
if not NORMALIZED_REVIEWS_PATH.exists():
    NORMALIZED_REVIEWS_PATH = PARSED_DIR / "normalized_reviews.json"

ANALYZED_THEMES_PATH = BASE_DIR / "analyzed_themes.json"
if not ANALYZED_THEMES_PATH.exists():
    ANALYZED_THEMES_PATH = DATA_DIR / "analyzed_themes.json"

# Closed Set of Schemes
VALID_SCHEME_IDS = [
    "large_cap",
    "mid_cap",
    "small_cap",
    "gold_fof",
    "silver_fof"
]

# Closed Set of Scheme Sections (7 Text Blocks)
VALID_SECTIONS = [
    "Key fund facts",
    "Exit load",
    "Benchmark",
    "Investment objective",
    "Stamp duty and tax",
    "Fund management",
    "Minimum investments"
]

# Closed Set of Themes from Milestone 2
VALID_THEME_IDS = [
    "other",
    "trading_charts",
    "money_movement",
    "reliability",
    "fees_brokerage"
]

# Canonical NAV Date across all 5 scheme files
CANONICAL_NAV_DATE = "25-Jun-2026"

# Review Dataset Time Window
REVIEW_WINDOW = "2026-04-12 to 2026-07-04"

# Execution Budget Invariants
MAX_REWORK_ATTEMPTS = 1
MAX_REFINEMENT_ATTEMPTS = 5
MAX_REPLY_SENTENCES = 3
```

---

## 3. State Schema Definition (`src/state.py`)

The state schema is strictly typed. It guarantees full visibility into agent transitions, preserves immutable sanitized inputs, and isolates intermediate node outputs.

```python
"""
Type-safe state definitions for LangGraph workflow.
"""
from typing import TypedDict, List, Optional, Literal, Dict, Any

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

class ReviewerOutput(TypedDict):
    passed: bool
    failure_reasons: List[str]
    review_attempt: int

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
    fired_agents_log: List[str]

    # Human-in-the-Loop & MCP
    is_approved: bool
    is_quarantined: bool
    mcp_actions_executed: List[str]
```

---

## 4. Pre-Graph PII Sanitizer & Redactor (`src/sanitizer.py`)

Financial compliance mandates **zero PII retention** in graph state, model prompts, and logs. Sanitization runs deterministically *before* any model invocation.

```python
"""
Deterministic PII Sanitization & Redaction Engine.
"""
import re
from typing import Tuple
from src.state import PIIArtifact

class PIISanitizer:
    # 1. Indian Permanent Account Number (PAN): 5 uppercase letters, 4 digits, 1 letter
    PAN_PATTERN = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b", re.IGNORECASE)

    # 2. Aadhaar Number: 12 digits, optional spaces/hyphens
    AADHAAR_PATTERN = re.compile(r"\b[2-9]{1}[0-9]{3}[-\s]?[0-9]{4}[-\s]?[0-9]{4}\b")

    # 3. Bank Account / Demat Number: 9 to 18 consecutive digits
    ACCOUNT_PATTERN = re.compile(r"\b[0-9]{9,18}\b")

    # 4. Indian Phone Number: +91, 0, or 10 digits starting with 6-9
    PHONE_PATTERN = re.compile(r"(?:(?:\+91|0)?[-\s]?)?[6-9]\d{4}[-\s]?\d{5}\b")

    # 5. Email Address: Standard RFC 5322
    EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")

    # 6. OTP Patterns: 4-6 digits preceded by keyword
    OTP_PATTERN = re.compile(r"\b(?:otp|code|pin)[^\w\d]{0,5}(\d{4,6})\b", re.IGNORECASE)

    @classmethod
    def sanitize(cls, text: str) -> Tuple[str, PIIArtifact]:
        """
        Scans and redacts all PII instances. Returns sanitized text and PII metadata.
        """
        detected_types = []
        sanitized = text

        # Check & Redact PAN
        if cls.PAN_PATTERN.search(sanitized):
            detected_types.append("PAN")
            sanitized = cls.PAN_PATTERN.sub("[REDACTED_PAN]", sanitized)

        # Check & Redact Aadhaar
        if cls.AADHAAR_PATTERN.search(sanitized):
            detected_types.append("AADHAAR")
            sanitized = cls.AADHAAR_PATTERN.sub("[REDACTED_AADHAAR]", sanitized)

        # Check & Redact Phone Numbers
        if cls.PHONE_PATTERN.search(sanitized):
            detected_types.append("PHONE")
            sanitized = cls.PHONE_PATTERN.sub("[REDACTED_PHONE]", sanitized)

        # Check & Redact Emails
        if cls.EMAIL_PATTERN.search(sanitized):
            detected_types.append("EMAIL")
            sanitized = cls.EMAIL_PATTERN.sub("[REDACTED_EMAIL]", sanitized)

        # Check & Redact OTP
        if cls.OTP_PATTERN.search(sanitized):
            detected_types.append("OTP")
            sanitized = cls.OTP_PATTERN.sub(r"otp [REDACTED_OTP]", sanitized)

        # Check & Redact Bank/Demat Accounts (after phone/aadhaar/otp to avoid collisions)
        if cls.ACCOUNT_PATTERN.search(sanitized):
            detected_types.append("ACCOUNT")
            sanitized = cls.ACCOUNT_PATTERN.sub("[REDACTED_ACCOUNT]", sanitized)

        artifact: PIIArtifact = {
            "has_pii": len(detected_types) > 0,
            "detected_types": list(set(detected_types)),
            "redacted_text": sanitized
        }

        return sanitized, artifact
```

---

## 5. Ground Truth Data Loader (`src/data_loader.py`)

Loads scheme files, review clusters, and normalized complaints into an in-memory dictionary cache at application startup.

```python
"""
In-memory caching and retrieval of canonical corpora.
"""
import json
from typing import Dict, Any, Optional
from src.config import (
    PARSED_DIR,
    SCHEMES_MANIFEST_PATH,
    ANALYZED_THEMES_PATH,
    NORMALIZED_REVIEWS_PATH,
    VALID_SCHEME_IDS
)

class DataLoader:
    _instance: Optional["DataLoader"] = None

    def __init__(self):
        self.schemes_data: Dict[str, Dict[str, Any]] = {}
        self.themes_data: Dict[str, Any] = {}
        self.theme_lookup: Dict[str, Dict[str, Any]] = {}
        self.reviews: list = []
        self._load_all()

    @classmethod
    def get_instance(cls) -> "DataLoader":
        if cls._instance is None:
            cls._instance = DataLoader()
        return cls._instance

    def _load_all(self):
        # 1. Load Scheme JSON files
        for scheme_id in VALID_SCHEME_IDS:
            scheme_file = PARSED_DIR / f"{scheme_id}.json"
            if scheme_file.exists():
                with open(scheme_file, "r", encoding="utf-8") as f:
                    self.schemes_data[scheme_id] = json.load(f)

        # 2. Load Analyzed Themes
        if ANALYZED_THEMES_PATH.exists():
            with open(ANALYZED_THEMES_PATH, "r", encoding="utf-8") as f:
                self.themes_data = json.load(f)
                for theme in self.themes_data.get("allThemes", []):
                    self.theme_lookup[theme["id"]] = theme

        # 3. Load Normalized Reviews (for acceptance test runner)
        if NORMALIZED_REVIEWS_PATH.exists():
            with open(NORMALIZED_REVIEWS_PATH, "r", encoding="utf-8") as f:
                self.reviews = json.load(f)

    def get_scheme_section_text(self, scheme_id: str, section_title: str) -> Optional[str]:
        scheme = self.schemes_data.get(scheme_id)
        if not scheme:
            return None
        for block in scheme.get("text_blocks", []):
            if block.get("section_title", "").strip().lower() == section_title.strip().lower():
                return block.get("text")
        return None

    def get_scheme_source_url(self, scheme_id: str) -> Optional[str]:
        scheme = self.schemes_data.get(scheme_id)
        return scheme.get("source_url") if scheme else None

    def get_scheme_name(self, scheme_id: str) -> Optional[str]:
        scheme = self.schemes_data.get(scheme_id)
        return scheme.get("scheme_name") if scheme else None

    def get_theme(self, theme_id: str) -> Optional[Dict[str, Any]]:
        return self.theme_lookup.get(theme_id)
```

---

## 6. Specialist Agents Implementation (`src/agents/`)

Every specialist agent adheres to the **Classification-Only Invariant**:
1. Exactly **one LLM call** returning a structured enum ID / boolean flag.
2. Deterministic Python code extracts the text, counts reviews, and attaches links.

### 6.1 Facts Agent (`src/agents/facts_agent.py`)

```python
"""
Facts Agent: Deterministic Scheme Information Retrieval.
"""
import json
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

def mock_or_call_facts_llm(sanitized_text: str) -> Dict[str, Optional[str]]:
    """
    Simulates or executes the single classification LLM call.
    In production, this calls litellm / ChatGoogleGenerativeAI with json_object response.
    Here we implement robust classification matching against closed enumerations.
    """
    text_lower = sanitized_text.lower()
    
    # Scheme classification
    matched_scheme = None
    if "large cap" in text_lower:
        matched_scheme = "large_cap"
    elif "mid cap" in text_lower:
        matched_scheme = "mid_cap"
    elif "small cap" in text_lower:
        matched_scheme = "small_cap"
    elif "gold" in text_lower:
        matched_scheme = "gold_fof"
    elif "silver" in text_lower:
        matched_scheme = "silver_fof"

    # Section classification
    matched_section = None
    if any(k in text_lower for k in ["exit load", "exit-load", "charges for redemption", "penalty"]):
        matched_section = "Exit load"
    elif any(k in text_lower for k in ["nav", "expense ratio", "aum", "fund size", "riskometer"]):
        matched_section = "Key fund facts"
    elif "benchmark" in text_lower:
        matched_section = "Benchmark"
    elif "objective" in text_lower:
        matched_section = "Investment objective"
    elif any(k in text_lower for k in ["tax", "stamp duty"]):
        matched_section = "Stamp duty and tax"
    elif any(k in text_lower for k in ["manager", "management"]):
        matched_section = "Fund management"
    elif any(k in text_lower for k in ["min sip", "minimum investment", "lumpsum"]):
        matched_section = "Minimum investments"

    return {"scheme_id": matched_scheme, "section_title": matched_section}

def facts_agent_node(state: AgentGraphState) -> Dict[str, Any]:
    """
    Facts Agent Node: Runs in parallel fan-out.
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
```

---

### 6.2 Pattern Agent (`src/agents/pattern_agent.py`)

```python
"""
Pattern Agent: Historical Review Trend Analytics.
"""
from typing import Dict, Any
from src.state import AgentGraphState, PatternOutput
from src.data_loader import DataLoader
from src.config import VALID_THEME_IDS, REVIEW_WINDOW

def mock_or_call_pattern_llm(sanitized_text: str) -> str:
    """
    Classifies the user complaint to exactly one theme ID from allThemes.
    """
    text_lower = sanitized_text.lower()
    if any(k in text_lower for k in ["fee", "brokerage", "exit load", "charge", "deducted fee"]):
        return "fees_brokerage"
    elif any(k in text_lower for k in ["withdraw", "deposit", "payment", "bank", "refund", "upi"]):
        return "money_movement"
    elif any(k in text_lower for k in ["chart", "order", "trade", "buy", "sell", "candle"]):
        return "trading_charts"
    elif any(k in text_lower for k in ["crash", "slow", "bug", "stuck", "login", "freeze", "server"]):
        return "reliability"
    return "other"

def pattern_agent_node(state: AgentGraphState) -> Dict[str, Any]:
    """
    Pattern Agent Node: Runs in parallel fan-out.
    """
    sanitized_input = state["sanitized_input"]
    data_loader = DataLoader.get_instance()

    # 1. Single classification call
    theme_id = mock_or_call_pattern_llm(sanitized_input)
    if theme_id not in VALID_THEME_IDS:
        theme_id = "other"

    # 2. Deterministic Analytics
    theme_info = data_loader.get_theme(theme_id) or {
        "id": theme_id,
        "name": "Other feedback",
        "count": 0,
        "avgRating": 3.0
    }

    count = theme_info.get("count", len(theme_info.get("reviewIds", [])))
    avg_rating = theme_info.get("avgRating", 3.0)

    # Status heuristics based on quantitative thresholds
    if count >= 100 and avg_rating <= 2.5:
        pattern_status = "recurring"
    elif theme_id in ["trading_charts", "money_movement"]:
        pattern_status = "rising"
    else:
        pattern_status = "one-off"

    top_themes = [t["id"] for t in data_loader.themes_data.get("topThemes", [])]
    in_top = theme_id in top_themes

    pattern_output: PatternOutput = {
        "theme_id": theme_id,
        "theme_name": theme_info.get("name", theme_id),
        "status": pattern_status,
        "review_count": count,
        "review_window": REVIEW_WINDOW,
        "in_top_themes": in_top
    }

    return {"pattern": pattern_output, "fired_agents_log": ["pattern_agent"]}
```

---

### 6.3 Compliance Agent (`src/agents/compliance_agent.py`)

```python
"""
Compliance Agent: Anti-Advice and Regulatory Guardrail Analysis.
"""
from typing import Dict, Any
from src.state import AgentGraphState, ComplianceOutput

ADVICE_TRIGGERS = [
    "should i", "recommend", "suggest", "better to hold", "better to sell",
    "is it good", "worth investing", "stay invested", "future return"
]

PERFORMANCE_TRIGGERS = [
    "guaranteed return", "expected return", "how much will i make",
    "profit percentage", "cagr promise", "will it double"
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
    Compliance Agent Node: Runs in parallel fan-out.
    """
    sanitized_input = state["sanitized_input"]
    pii_metadata = state["pii_metadata"]

    llm_result = mock_or_call_compliance_llm(sanitized_input)

    # Compliance passes if no advice/performance claim was coerced and PII is handled
    compliance_passed = not (llm_result["advice"] or llm_result["performance_claim"])

    compliance_output: ComplianceOutput = {
        "incoming_has_advice": llm_result["advice"],
        "incoming_has_performance_claim": llm_result["performance_claim"],
        "pii_detected": pii_metadata["has_pii"],
        "detected_pii_types": pii_metadata["detected_types"],
        "compliance_passed": compliance_passed
    }

    return {"compliance": compliance_output, "fired_agents_log": ["compliance_agent"]}
```

---

## 7. Orchestrator & Synthesizer (`src/orchestrator/orchestrator.py`)

The Orchestrator awaits all 3 specialist outputs and generates the dual-channel deliverables.

```python
"""
Orchestrator: Dual-Channel Synthesis and Internal Ticket Routing.
"""
import re
from typing import Dict, Any
from src.state import AgentGraphState, OrchestratorOutput
from src.config import MAX_REPLY_SENTENCES, CANONICAL_NAV_DATE

def count_sentences(text: str) -> int:
    """Counts sentences using punctuation terminators."""
    sentences = re.split(r'[.!?]+(?:\s+|$)', text.strip())
    return len([s for s in sentences if s.strip()])

def orchestrator_node(state: AgentGraphState) -> Dict[str, Any]:
    """
    Fan-in node: merges facts, pattern, and compliance into draft & routing note.
    """
    facts = state.get("facts")
    pattern = state.get("pattern")
    compliance = state.get("compliance")
    rework_count = state.get("rework_count", 0)

    # --- 1. CHANNEL A: USER REPLY DRAFT ---
    # Handled with strict <= 3 sentence constraint, 1 citation, and last checked date
    if facts and facts["status"] == "covered":
        scheme_name = facts["scheme_name"]
        extracted_sentence = facts["extracted_text"].strip()
        citation = facts["source_url"]
        
        # Sentence 1: The factual statement from the scheme
        # Sentence 2: Citation link and last checked date
        reply_draft = (
            f"As per the official scheme terms for {scheme_name}, {extracted_sentence}. "
            f"You can verify this in the scheme document at {citation}. "
            f"Last checked: {CANONICAL_NAV_DATE}."
        )
        citation_url = citation
    else:
        # Out-of-scope query handling
        searched = ", ".join(facts["searched_schemes"][:3]) if facts else "verified funds"
        reply_draft = (
            f"The requested detail is not covered in our verified scheme documents for {searched}. "
            f"Groww support replies strictly reference public scheme disclosures without speculation. "
            f"Last checked: {CANONICAL_NAV_DATE}."
        )
        citation_url = None

    # Handle advice request deflection
    if compliance and compliance["incoming_has_advice"]:
        reply_draft = (
            f"Groww does not provide personalized investment advice or redemption recommendations. "
            + reply_draft
        )

    # Ensure sentence budget constraint
    num_sentences = count_sentences(reply_draft)
    if num_sentences > MAX_REPLY_SENTENCES:
        sentences = [s.strip() for s in re.split(r'[.!?]+', reply_draft) if s.strip()]
        reply_draft = ". ".join(sentences[:MAX_REPLY_SENTENCES]) + f". Last checked: {CANONICAL_NAV_DATE}."
        num_sentences = count_sentences(reply_draft)

    # --- 2. CHANNEL B: INTERNAL ROUTING NOTE ---
    target_team = "Mutual Funds Operations"
    priority = "P3-Low"
    discrepancy = False
    discrepancy_details = None

    if pattern:
        theme_id = pattern["theme_id"]
        review_count = pattern["review_count"]
        status = pattern["status"]

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
        if facts and facts["status"] == "covered" and status == "recurring":
            discrepancy = True
            discrepancy_details = (
                f"Discrepancy Detected: Scheme terms explain the fee/rule cleanly, but {review_count} "
                f"users reported recurring friction in '{pattern['theme_name']}'. "
                f"Flagged for operational review rather than routine closure."
            )

    routing_note = (
        f"Route to: {target_team} | Priority: {priority}\n"
        f"Pattern Context: {pattern['theme_name'] if pattern else 'General'} "
        f"({pattern['review_count'] if pattern else 0} reviews, status: {pattern['status'] if pattern else 'one-off'})\n"
        f"Compliance Status: PII Redacted={compliance['pii_detected'] if compliance else False}, "
        f"Advice Refused={compliance['incoming_has_advice'] if compliance else False}"
    )
    if discrepancy:
        routing_note += f"\nWarning: {discrepancy_details}"

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
```

---

## 8. Automated Reviewer Node (`src/orchestrator/reviewer.py`)

Deterministic gatekeeper enforcing all hard constraints before human review.

```python
"""
Reviewer: Deterministic Compliance & Guardrail Quality Gate.
"""
import re
from typing import Dict, Any, List
from src.state import AgentGraphState, ReviewerOutput
from src.sanitizer import PIISanitizer
from src.config import MAX_REPLY_SENTENCES, CANONICAL_NAV_DATE

BANNED_ADVICE_WORDS = [
    r"\bwe recommend\b",
    r"\byou should\b",
    r"\bconsider staying invested\b",
    r"\bbetter to sell\b",
    r"\bgood buy\b",
    r"\bexpect higher returns\b"
]

def reviewer_node(state: AgentGraphState) -> Dict[str, Any]:
    """
    Reviewer Guardrail Node: Evaluates draft against hard rules.
    """
    orchestrator = state.get("orchestrator")
    facts = state.get("facts")
    rework_count = state.get("rework_count", 0)

    if not orchestrator:
        return {
            "reviewer": {"passed": False, "failure_reasons": ["No orchestrator output"], "review_attempt": rework_count + 1}
        }

    draft = orchestrator["reply_draft"]
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
    sentences = [s.strip() for s in re.split(r'[.!?]+', draft) if s.strip()]
    if len(sentences) > MAX_REPLY_SENTENCES:
        failures.append(f"Draft exceeds {MAX_REPLY_SENTENCES} sentences (found {len(sentences)})")

    # 4. Mandatory Timestamp Check
    if CANONICAL_NAV_DATE not in draft:
        failures.append(f"Missing mandatory last checked verification date '{CANONICAL_NAV_DATE}'")

    # 5. Citation Check on Factual Claims
    if facts and facts["status"] == "covered":
        if not facts["source_url"] or facts["source_url"] not in draft:
            failures.append("Factual scheme claim missing canonical source_url citation link")

    passed = len(failures) == 0

    reviewer_output: ReviewerOutput = {
        "passed": passed,
        "failure_reasons": failures,
        "review_attempt": rework_count + 1
    }

    return {"reviewer": reviewer_output, "fired_agents_log": ["reviewer"]}
```

---

## 9. LangGraph Assembly & Wiring (`src/graph.py`)

Builds and compiles the complete multi-agent workflow using LangGraph.

```python
"""
LangGraph Workflow Assembly: Fan-out, Fan-in, Rework, and Refinement.
"""
from typing import Literal
from langgraph.graph import StateGraph, START, END

from src.state import AgentGraphState
from src.sanitizer import PIISanitizer
from src.agents.facts_agent import facts_agent_node
from src.agents.pattern_agent import pattern_agent_node
from src.agents.compliance_agent import compliance_agent_node
from src.orchestrator.orchestrator import orchestrator_node
from src.orchestrator.reviewer import reviewer_node
from src.config import MAX_REWORK_ATTEMPTS, MAX_REFINEMENT_ATTEMPTS

# --- 1. Node Definitions ---

def sanitizer_node(state: AgentGraphState) -> dict:
    """Pre-graph sanitization step."""
    sanitized, pii_artifact = PIISanitizer.sanitize(state["raw_input"])
    return {
        "sanitized_input": sanitized,
        "pii_metadata": pii_artifact,
        "rework_count": 0,
        "refinement_count": 0,
        "is_approved": False,
        "is_quarantined": False,
        "fired_agents_log": ["sanitizer"]
    }

def quarantine_node(state: AgentGraphState) -> dict:
    """Quarantine node when reviewer fails after max rework."""
    return {
        "is_quarantined": True,
        "is_approved": False,
        "fired_agents_log": ["quarantine"]
    }

def human_review_node(state: AgentGraphState) -> dict:
    """Human Review Node: Draft presented to support agent."""
    return {
        "fired_agents_log": ["human_review"]
    }

# --- 2. Routing Functions ---

def route_reviewer(state: AgentGraphState) -> Literal["human_review", "orchestrator", "quarantine"]:
    """Routes based on Reviewer results and rework budget."""
    reviewer = state.get("reviewer")
    rework_count = state.get("rework_count", 0)

    if reviewer and reviewer["passed"]:
        return "human_review"
    
    if rework_count < MAX_REWORK_ATTEMPTS:
        state["rework_count"] = rework_count + 1
        return "orchestrator"
    
    return "quarantine"

def route_refinement(state: AgentGraphState) -> Literal["orchestrator", "facts", "pattern", END]:
    """Selectively triggers only affected agents upon human pushback."""
    target = state.get("active_refinement_target")
    refinement_count = state.get("refinement_count", 0)

    if refinement_count >= MAX_REFINEMENT_ATTEMPTS:
        return END

    if target == "facts":
        return "facts"
    elif target == "pattern":
        return "pattern"
    elif target == "orchestrator":
        return "orchestrator"
    
    return END

# --- 3. Build & Compile Workflow ---

def create_support_graph() -> StateGraph:
    workflow = StateGraph(AgentGraphState)

    # Register Nodes
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

    # 2. Strict Parallel Fan-Out
    workflow.add_edge("sanitizer", "facts")
    workflow.add_edge("sanitizer", "pattern")
    workflow.add_edge("sanitizer", "compliance")

    # 3. Fan-In to Orchestrator
    workflow.add_edge("facts", "orchestrator")
    workflow.add_edge("pattern", "orchestrator")
    workflow.add_edge("compliance", "orchestrator")

    # 4. Orchestrator to Reviewer
    workflow.add_edge("orchestrator", "reviewer")

    # 5. Reviewer Conditional Routing
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
```

---

## 10. Approval-Gated MCP Tool Execution (`src/mcp_tools.py`)

No external updates occur without an explicit human clicking **Approve**.

```python
"""
Approval-Gated MCP Tool Layer.
"""
from typing import Dict, Any
from src.state import AgentGraphState

class MCPExecutionGate:
    @staticmethod
    def append_record_to_doc(state: AgentGraphState) -> Dict[str, Any]:
        """Appends approved reply and metadata to incident document."""
        if not state.get("is_approved"):
            raise PermissionError("Approval Gate Block: Human approval required before appending to doc.")
        
        orch = state["orchestrator"]
        record = {
            "draft": orch["reply_draft"],
            "citation": orch["citation_url"],
            "routing": orch["routing_note"],
            "timestamp": orch["last_checked"]
        }
        # Real MCP / Document API integration executes here
        return {"status": "success", "action": "append_record_to_doc", "record": record}

    @staticmethod
    def create_email_draft(state: AgentGraphState) -> Dict[str, Any]:
        """Creates pending draft in support client (Guaranteed NO auto-send)."""
        if not state.get("is_approved"):
            raise PermissionError("Approval Gate Block: Human approval required before creating draft.")

        orch = state["orchestrator"]
        draft_payload = {
            "status": "DRAFT",
            "body": orch["reply_draft"],
            "auto_send": False  # Invariant: Never auto-send
        }
        return {"status": "success", "action": "create_email_draft", "payload": draft_payload}
```

---

## 11. Acceptance Testing & Verification Suite (`tests/`)

### 11.1 Acceptance Test Suite (`tests/test_acceptance_suite.py`)
Validates all 5 mandatory branches and executes the 20-review benchmark from `data/normalized_reviews.json`.

```python
"""
Comprehensive Acceptance Test Suite for Groww Multi-Agent System.
"""
import pytest
from src.graph import create_support_graph
from src.data_loader import DataLoader
from src.config import CANONICAL_NAV_DATE

@pytest.fixture(scope="module")
def graph():
    return create_support_graph()

# --- BRANCH A: Clean in-scope fact ---
def test_branch_a_clean_fact(graph):
    query = "Why was I charged an exit load on HDFC Large Cap Fund Direct Growth?"
    result = graph.invoke({"raw_input": query})

    facts = result["facts"]
    orch = result["orchestrator"]
    rev = result["reviewer"]

    assert facts["status"] == "covered"
    assert facts["scheme_id"] == "large_cap"
    assert "1%" in facts["extracted_text"]
    assert facts["source_url"] == "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth"
    assert facts["source_url"] in orch["reply_draft"]
    assert CANONICAL_NAV_DATE in orch["reply_draft"]
    assert orch["sentence_count"] <= 3
    assert rev["passed"] is True

# --- BRANCH B: Out-of-scope query ---
def test_branch_b_out_of_scope(graph):
    query = "What is the exit load for Axis Bluechip Fund?"
    result = graph.invoke({"raw_input": query})

    facts = result["facts"]
    orch = result["orchestrator"]

    assert facts["status"] == "not_covered"
    assert "not covered in our verified scheme documents" in orch["reply_draft"]
    assert orch["citation_url"] is None
    assert CANONICAL_NAV_DATE in orch["reply_draft"]

# --- BRANCH C: Recurring theme detection ---
def test_branch_c_recurring_theme(graph):
    query = "Money was deducted from my bank account but deposit is not showing in Groww balance."
    result = graph.invoke({"raw_input": query})

    pattern = result["pattern"]
    orch = result["orchestrator"]

    assert pattern["theme_id"] == "money_movement"
    assert pattern["review_count"] == 162
    assert orch["target_team"] == "Banking & Payments Desk"
    assert orch["priority"] == "P1-High"

# --- BRANCH D: PII Injection & Redaction ---
def test_branch_d_pii_injection(graph):
    query = "My PAN is ABCDE1234F and mobile number is 9876543210. Why was exit load charged on HDFC Mid Cap?"
    result = graph.invoke({"raw_input": query})

    pii = result["pii_metadata"]
    orch = result["orchestrator"]
    rev = result["reviewer"]

    assert pii["has_pii"] is True
    assert "PAN" in pii["detected_types"]
    assert "PHONE" in pii["detected_types"]
    assert "ABCDE1234F" not in result["sanitized_input"]
    assert "9876543210" not in result["sanitized_input"]
    assert "ABCDE1234F" not in orch["reply_draft"]
    assert "9876543210" not in orch["reply_draft"]
    assert rev["passed"] is True

# --- BRANCH E: Adversarial Advice Probing ---
def test_branch_e_advice_probe(graph):
    query = "Should I redeem my HDFC Gold ETF Fund of Fund now or hold for better returns?"
    result = graph.invoke({"raw_input": query})

    compliance = result["compliance"]
    orch = result["orchestrator"]

    assert compliance["incoming_has_advice"] is True
    assert "does not provide personalized investment advice" in orch["reply_draft"]
    assert "15 days" in orch["reply_draft"]

# --- 20-REVIEW BATCH ACCEPTANCE RUNNER ---
def test_20_review_acceptance_batch(graph):
    loader = DataLoader.get_instance()
    reviews = loader.reviews[:20]
    assert len(reviews) == 20, "Must have at least 20 real normalized reviews"

    for idx, rev in enumerate(reviews):
        text = rev.get("text", "") or rev.get("title", "")
        if not text:
            continue
        res = graph.invoke({"raw_input": text})
        
        # Invariant 1: All 3 specialists produced structured output
        assert res["facts"] is not None
        assert res["pattern"] is not None
        assert res["compliance"] is not None
        
        # Invariant 2: Reviewer ran and produced evaluation
        assert res["reviewer"] is not None
        
        # Invariant 3: Reply draft carries citation OR declares not covered
        draft = res["orchestrator"]["reply_draft"]
        assert (res["orchestrator"]["citation_url"] in draft) or ("not covered" in draft)
        assert CANONICAL_NAV_DATE in draft
```

---

## 12. Interactive CLI Runner (`run.py`)

A full console application that runs complaints through the system, visualizes parallel execution, shows reviewer outputs, and runs the approval gate.

```python
"""
Interactive CLI Runner for Groww Support Reply System.
"""
import sys
from src.graph import create_support_graph
from src.mcp_tools import MCPExecutionGate

def run_ticket(query: str):
    print("=" * 80)
    print(f"INCOMING TICKET: {query}")
    print("=" * 80)

    graph = create_support_graph()
    state = graph.invoke({"raw_input": query})

    print(f"\n[1] PII SANITIZATION:")
    print(f"    Redacted Text: {state['sanitized_input']}")
    print(f"    Detected PII:  {state['pii_metadata']['detected_types']}")

    print(f"\n[2] PARALLEL SPECIALIST RESULTS:")
    facts = state['facts']
    pattern = state['pattern']
    comp = state['compliance']
    print(f"    - Facts:      Status={facts['status']} | Scheme={facts['scheme_id']} | Sec={facts['section_title']}")
    print(f"    - Pattern:    Theme={pattern['theme_name']} | Count={pattern['review_count']} | Status={pattern['status']}")
    print(f"    - Compliance: AdviceFlag={comp['incoming_has_advice']} | PIIFlag={comp['pii_detected']}")

    print(f"\n[3] ORCHESTRATOR OUTPUTS:")
    orch = state['orchestrator']
    print(f"    Reply Draft ({orch['sentence_count']} sentences):")
    print(f"    \"{orch['reply_draft']}\"")
    print(f"\n    Internal Routing Note:")
    for line in orch['routing_note'].split('\n'):
        print(f"    | {line}")

    rev = state['reviewer']
    print(f"\n[4] AUTOMATED REVIEWER CHECK:")
    print(f"    Status: {'PASSED' if rev['passed'] else 'FAILED'}")
    if not rev['passed']:
        print(f"    Reasons: {rev['failure_reasons']}")

    # Approval Gate Simulation
    if rev['passed']:
        print("\n[5] APPROVAL-GATED MCP ACTION:")
        state['is_approved'] = True
        doc_res = MCPExecutionGate.append_record_to_doc(state)
        email_res = MCPExecutionGate.create_email_draft(state)
        print(f"    [OK] Document Append: {doc_res['status']}")
        print(f"    [OK] Email Draft:     {email_res['status']} (auto_send={email_res['payload']['auto_send']})")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    test_queries = [
        "Why was I charged an exit load on HDFC Large Cap Fund Direct Growth?",
        "My phone number is 9876543210 and PAN is ABCDE1234F. Can you refund the exit load?",
        "Money was deducted from my account, please refund immediately!",
        "Should I redeem my gold fund now or hold for higher returns?",
        "What is the exit load for Parag Parikh Flexi Cap Fund?"
    ]

    for q in test_queries:
        run_ticket(q)
```

---

## 13. Step-by-Step Execution Runbook

### Step 1: Environment Setup
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Step 2: Run Automated Acceptance Suite
```powershell
pytest tests/test_acceptance_suite.py -v
```

### Step 3: Run Interactive Demo Runner
```powershell
python run.py
```

### Step 4: Verify System Invariants
- Confirm zero raw PAN / phone numbers appear in drafts or logs.
- Confirm every fact cites `source_url` with `"Last checked: 25-Jun-2026"`.
- Confirm `create_email_draft` operates strictly in `DRAFT` mode with `auto_send=False`.
