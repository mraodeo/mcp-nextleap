# Groww App Review Pulse Agent

An autonomous AI agent that extracts, analyzes, and synthesizes app reviews from the Google Play Store to generate real-time product insights for the Groww App.

## Architecture

This project is divided into four main layers:
1. **Scraping Layer (`src/scraper/play_store.py`)**: Connects to the Google Play Store via the `google-play-scraper` package. It fetches recent reviews, sanitizes them, and drops non-English or blank reviews.
2. **Agent Reasoning Layer (`src/agent/`)**: Uses LangChain and Groq (LLaMA) to chunk the reviews safely under API rate limits, analyze them for top themes, extract verbatim quotes, and propose actionable product ideas.
3. **MCP Integration Layer (`src/mcp_clients/`)**: Connects to a remote Model Context Protocol (MCP) server hosted on Railway to securely interface with Google Docs (for appending reports) and Gmail (for drafting/sending notification emails).
4. **Orchestration Layer (`src/main.py`)**: The entry point that ties all the layers together sequentially.

## Setup Instructions

1. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Environment Variables (`.env`)**:
   Create a `.env` file in the root directory with the following variables:
   ```env
   GROQ_API_KEY=gsk_your_groq_api_key
   MCP_SERVER_URL=https://mcp-nextleap-production.up.railway.app/sse
   GOOGLE_DOC_ID=your_google_doc_id
   TARGET_EMAIL=your_email@gmail.com
   ```

## How to Run

To execute the agent end-to-end (fetch reviews -> analyze -> append to Docs -> send Email), simply run the `main.py` script from the root directory:

```bash
python src/main.py
```

*Note: Ensure you are running this from the root of the `AI Agent` folder, not from inside the `src` folder, so Python can correctly resolve module paths.*
