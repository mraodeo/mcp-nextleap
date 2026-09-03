import os
from langchain_core.tools import tool
from src.mcp_clients.mcp_connection import get_mcp_session

@tool
async def append_to_docs(markdown_content: str) -> str:
    """
    Appends the provided markdown content to the target Google Doc.
    """
    doc_id = os.environ.get("GOOGLE_DOC_ID")
    if not doc_id or doc_id == "your_google_doc_id_here":
        return "Failed: GOOGLE_DOC_ID environment variable is missing or not set."

    try:
        async with get_mcp_session() as session:
            # We call the 'append_to_doc' tool exposed by the remote MCP server
            result = await session.call_tool("append_to_doc", arguments={"documentId": doc_id, "content": markdown_content})
            
            # The result content is a list of TextContent objects
            for content in result.content:
                if content.type == 'text':
                    return content.text
            return "Document updated, but response content not found."
    except Exception as e:
        return f"Failed to append to docs: {str(e)}"
