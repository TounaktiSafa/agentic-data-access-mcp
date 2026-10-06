import asyncio

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    params = StdioServerParameters(command="python", args=["-m", "src.mcp_server.server"])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as s:
            await s.initialize()
            print("tools:", [t.name for t in (await s.list_tools()).tools])
            print((await s.call_tool("list_tables", {})).content)
            print((await s.call_tool("describe_table", {"table": "analytics.customers"})).content)


asyncio.run(main())
