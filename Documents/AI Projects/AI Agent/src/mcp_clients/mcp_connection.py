import os
from contextlib import asynccontextmanager
from mcp import ClientSession
from mcp.client.sse import sse_client

MCP_SERVER_URL = os.environ.get("MCP_SERVER_URL", "https://mcp-nextleap-production.up.railway.app/sse")

@asynccontextmanager
async def get_mcp_session():
    """Connects to the remote MCP server via SSE and yields the session."""
    async with sse_client(MCP_SERVER_URL) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            yield session
