# Edge Cases & Corner Scenarios: Groww App Review Pulse Agent

This document outlines potential edge cases, failure modes, and corner scenarios for the Groww App Review Pulse Agent based on the current architecture and implementation plan. Handling these scenarios ensures a robust and reliable system.

---

## 1. Data Ingestion & Scraping (`play_store.py`)

| Scenario | Potential Impact | Mitigation Strategy |
| :--- | :--- | :--- |
| **No Reviews Found** | The system fetches 0 reviews for the trailing 8-12 weeks. | Abort the pipeline early. Log the event and optionally send an email stating "No recent reviews found" instead of throwing an error. |
| **High Review Volume** | Fetching thousands of reviews creates a massive payload that exceeds downstream limits. | Implement a cap (e.g., max 1000 most "helpful" or "recent" reviews) or sample the dataset to ensure we don't overwhelm the LLM context window or hit API rate limits. |
| **Scraper Blocked** | Google Play blocks the IP due to automated scraping. | Implement exponential backoff for the scraper. If blocked completely, alert the user via console/logs to run the task locally or cycle IP/proxy. |
| **Non-English Reviews** | The raw text is in Hindi, Hinglish, or other regional languages. | Ensure the LLM prompt explicitly instructs the model to translate non-English quotes into English while retaining the core meaning, OR filter to English-only at the scraping layer. |
| **Gibberish/Emoji-Only Reviews** | Reviews that contain no text, just symbols or random characters. | Pre-filter reviews using a basic regex/heuristic to drop reviews that don't contain at least 3-4 actual dictionary words. |

---

## 2. LLM Reasoning & Groq Limitations (`chains.py`)

| Scenario | Potential Impact | Mitigation Strategy |
| :--- | :--- | :--- |
| **Hitting 8K TPM Limit** | Sending a large batch of reviews triggers a `429 Too Many Requests` error from Groq. | **CRITICAL:** Implement a robust token counting text-splitter (e.g., `tiktoken`) before sending to Groq. Use `time.sleep()` between chunks or a LangChain retry mechanism (e.g., `Tenacity`) with exponential backoff. |
| **Hitting 30 RPM Limit** | Too many chunked requests in a short window. | Combine requests where possible up to the token limit, and enforce a minimum delay of 2 seconds between LLM calls. |
| **Hallucinated Quotes** | The LLM "invents" a quote that sounds plausible but wasn't actually in the review data. | Emphasize in the System Prompt: *"Quotes MUST be verbatim substrings from the provided text. Do not generate or paraphrase quotes."* Optionally, add a post-validation step in Python to check if `quote in raw_reviews`. |
| **Malformed Output (JSON Error)** | The LLM fails to adhere to the `PulseReport` Pydantic model (e.g., adds markdown formatting around the JSON). | Use LangChain's `with_structured_output` strictly. Implement an `OutputFixingParser` or automatic retry loop if parsing fails. |

---

## 3. Data Privacy & Sanitization

| Scenario | Potential Impact | Mitigation Strategy |
| :--- | :--- | :--- |
| **PII in Review Body** | A user writes their phone number or email directly inside the review text (e.g., "My email is x@y.com"). | Beyond stripping metadata names, the `play_store.py` sanitization step should use basic Regex to scrub email formats (`*@*.*`) and 10-digit phone numbers from the raw text before it hits the LLM. |

---

## 4. MCP Integrations (`docs_client.py` & `gmail_client.py`)

| Scenario | Potential Impact | Mitigation Strategy |
| :--- | :--- | :--- |
| **MCP Server Unreachable** | The local MCP server for Docs/Gmail is down or not started. | Add connection timeout handling in `main.py`. If the MCP client cannot connect, fail gracefully and output the final Markdown to a local file (e.g., `fallback_pulse.md`) so the LLM generation isn't wasted. |
| **Auth/Token Expiration** | The Google credentials within the MCP server have expired. | Catch permission errors returned by the MCP `@tool`. Surface a clear error message: *"MCP Auth Error: Please re-authenticate your Google MCP server."* |
| **Email Draft Creation Fails** | The Gmail MCP tool rejects the payload due to formatting issues or size. | Ensure the markdown summary passed to the email tool is strictly plaintext or properly formatted HTML. If it fails, fallback to just emailing the Google Doc URL. |

---

## 5. Orchestration (`main.py`)

| Scenario | Potential Impact | Mitigation Strategy |
| :--- | :--- | :--- |
| **Partial Pipeline Failure** | The Doc is created, but the Gmail draft fails, leaving an orphaned document. | Log the URL of the created document immediately to standard output (`stdout`) before attempting to draft the email, ensuring the user can still find the generated report. |
| **Concurrent Executions** | The cron job fires while a previous slow execution is still running, causing duplicate docs/emails. | Implement a simple lock file (e.g., `.agent_running.lock`) at the start of `main.py` to prevent concurrent executions. |
