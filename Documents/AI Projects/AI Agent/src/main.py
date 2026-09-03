import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import asyncio
from dotenv import load_dotenv

from src.scraper.play_store import fetch_groww_reviews
from src.agent.chains import analyze_reviews_with_groq, format_pulse_report_to_markdown
from src.mcp_clients.docs_client import append_to_docs
from src.mcp_clients.gmail_client import draft_pulse_email

# Load environment variables
load_dotenv()

async def run_pulse_agent():
    print("🚀 Starting Groww App Review Pulse Agent...")
    
    # Check if necessary environment variables are set
    doc_id = os.environ.get("GOOGLE_DOC_ID")
    target_email = os.environ.get("TARGET_EMAIL")
    
    if not doc_id or doc_id == "your_google_doc_id_here":
        print("⚠️ Warning: GOOGLE_DOC_ID is not configured in .env. Docs appending may fail.")
        
    if not target_email or target_email == "your_email@example.com":
        print("⚠️ Warning: TARGET_EMAIL is not configured in .env. Email drafting may fail.")
        
    print("\n[1/4] Fetching recent reviews...")
    # Using weeks_back=1 for faster execution in daily/weekly cron, or 8 for historical pulse
    reviews = fetch_groww_reviews(weeks_back=8, max_count=300)
    
    if not reviews:
        print("No new reviews found.")
        return

    print(f"✅ Fetched {len(reviews)} reviews.\n")
    
    print("[2/4] Analyzing reviews with Groq (LangChain)...")
    pulse_report = analyze_reviews_with_groq(reviews)
    markdown_report = format_pulse_report_to_markdown(pulse_report)
    
    print("✅ Analysis complete.\n")
    print("--- Report Preview ---")
    print(markdown_report)
    print("----------------------\n")
    
    print("[3/4] Appending report to Google Docs via MCP...")
    # Provide the raw markdown to the docs client, ensuring it is formatted for appending
    append_text = f"\n\n--- Pulse Report generated on ---\n\n{markdown_report}"
    docs_result = await append_to_docs.ainvoke({"markdown_content": append_text})
    print(f"✅ Docs Result: {docs_result}\n")
    
    print("[4/4] Drafting notification email via MCP...")
    # Summarize the themes for the email body
    summary = "\n".join([f"- {theme}" for theme in pulse_report.themes])
    email_result = await draft_pulse_email.ainvoke({"summary": summary})
    if email_result:
        print("✅ Email drafted successfully.\n")
    else:
        print("❌ Failed to draft email.\n")
        
    print("🎉 Pulse Agent workflow complete!")

if __name__ == "__main__":
    asyncio.run(run_pulse_agent())
