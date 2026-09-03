# Groww App Review Pulse Agent Implementation Plan

This document outlines the phase-wise execution plan to build the system detailed in the architecture document.

## Open Questions (Before Development)
1. **MCP Servers:** Do you already have the Google Docs and Gmail MCP servers configured and running locally, or should we include setting those up as part of the process?

## Proposed Implementation Phases

### Phase 1: Project Setup and Data Ingestion
Establish the foundational Python project and implement the logic to fetch raw data.

#### `requirements.txt`
- Dependencies: `google-play-scraper`, `langchain`, `langchain-core`, `langchain-groq`, `pydantic`, `langdetect`.

#### `.env`
- Template file for storing the LLM API Key.

#### `src/scraper/play_store.py`
- Implements fetching logic for the `com.nextbillion.groww` app using `google-play-scraper`.
- Filters reviews to the trailing 8-12 weeks.
- **Filtering:** Drops any reviews with fewer than 8 words, and utilizes `langdetect` to strictly drop non-English reviews.
- **Sanitization:** Removes reviewer names and avatars, and scrubs PII (emails/phone numbers) before passing data downstream to ensure strict privacy compliance.

---

### Phase 2: AI Agent Schemas and Prompts
Define the strict structures and prompts the LLM needs to follow to parse the reviews.

#### `src/agent/models.py`
- Defines the `PulseReport` Pydantic model enforcing:
  - `themes` (max 3 items)
  - `quotes` (max 3 items, verbatim from reviews)
  - `actions` (max 3 items, actionable steps based on themes)

#### `src/agent/prompts.py`
- System prompts instructing the LLM to cluster reviews, extract the top 3 themes, pick verbatim quotes, and keep the final output strictly under 250 words.

---

### Phase 3: LangChain Reasoning
Implement the core logic tying the raw data to the LLM.

#### `src/agent/chains.py`
- Creates the LangChain LCEL (LangChain Expression Language) pipeline using the `openai/gpt-oss-120b` model via Groq.
- Implements chunking and rate-limiting logic to strictly respect the 8K Tokens Per Minute limit (e.g., using `time.sleep()` or LangChain's token text splitters).
- Uses `with_structured_output` to parse the LLM's response into the `PulseReport` Pydantic model.
- Formats the structured data into the final, readable Markdown string.

---

### Phase 4: MCP Integration Tools
Create the LangChain tools that communicate with remote MCP servers for Google Workspace integration.

#### `src/mcp_clients/docs_client.py`
- Wraps the Google Docs MCP server calls into a LangChain `@tool`.
- Function: `append_to_docs(markdown_content: str) -> str` (Appends to the document specified by GOOGLE_DOC_ID).

#### `src/mcp_clients/gmail_client.py`
- Wraps the Gmail MCP server calls into a LangChain `@tool`.
- Function: `draft_pulse_email(summary: str) -> bool` (Returns True on success, emails the TARGET_EMAIL).

---

### Phase 5: Orchestration
The final step tying all the layers together into a single executable process.

#### `src/main.py`
- Orchestrates the end-to-end flow:
  1. Calls `play_store.py` to fetch sanitized reviews.
  2. Passes the reviews to `chains.py` to generate the Pulse markdown report.
  3. Uses the `append_to_docs` tool to append the report in Google Docs.
  4. Uses the `draft_pulse_email` tool to create a draft email containing a link to the report.

## Verification Plan

### Automated Tests
- Optionally add `pytest` for unit testing the scraper logic and prompt formatting.

### Manual Verification
1. **Scraper Test:** Run `play_store.py` standalone to ensure it fetches reviews within the date range and correctly strips PII.
2. **AI Reasoning Test:** Run `chains.py` with mock review data to verify the LLM consistently outputs the strict Pydantic structure without hallucinating quotes.
3. **MCP Integration Test:** Test the `docs_client` and `gmail_client` independently to ensure they successfully route commands to the local MCP servers.
4. **End-to-End Test:** Run `main.py` and verify a new Google Doc is created and a Draft Email appears in the target Gmail account.
