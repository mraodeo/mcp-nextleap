import asyncio
from mcp.client.sse import sse_client
from mcp import ClientSession

async def list_mcp_tools():
    try:
        async with sse_client("https://mcp-nextleap-production.up.railway.app/sse") as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                tools = await session.list_tools()
                for t in tools.tools:
                    print(f"Tool: {t.name}")
                    print(f"Description: {t.description}")
                    print(f"Schema: {t.inputSchema}")
                    print("---")
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(list_mcp_tools())
