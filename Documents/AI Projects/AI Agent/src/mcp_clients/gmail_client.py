import os
from langchain_core.tools import tool
from src.mcp_clients.mcp_connection import get_mcp_session

@tool
async def draft_pulse_email(summary: str) -> bool:
    """
    Drafts an email containing a link to the generated Pulse report and a summary.
    Returns True on success, False otherwise.
    """
    target_email = os.environ.get("TARGET_EMAIL")
    if not target_email or target_email == "your_email@example.com":
        print("Failed: TARGET_EMAIL environment variable is missing or not set.")
        return False
        
    doc_id = os.environ.get("GOOGLE_DOC_ID")
    doc_url = f"https://docs.google.com/document/d/{doc_id}/edit" if doc_id else "No Doc ID configured."
    
    subject = "Groww App Review Pulse Report"
    body = f"Here is the latest Groww App Review Pulse report:\n\n{summary}\n\nView the full report document here: {doc_url}"

    try:
        async with get_mcp_session() as session:
            # We call the 'send_email' tool exposed by the remote MCP server
            result = await session.call_tool(
                "send_email", 
                arguments={
                    "to": target_email, 
                    "subject": subject,
                    "body": body
                }
            )
            return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False
