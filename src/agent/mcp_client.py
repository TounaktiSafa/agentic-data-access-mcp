import json
import sys
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from src import tracing


class Warehouse:
    """MCP client: starts the MCP server as a subprocess and calls its tools."""

    async def __aenter__(self):
        self._stack = AsyncExitStack()
        params = StdioServerParameters(command=sys.executable, args=["-m", "src.mcp_server.server"])
        read, write = await self._stack.enter_async_context(stdio_client(params))
        self.session = await self._stack.enter_async_context(ClientSession(read, write))
        await self.session.initialize()
        return self

    async def __aexit__(self, *exc):
        await self._stack.aclose()

    @tracing.observe(name="mcp.call", capture_input=False, capture_output=False)
    async def call(self, tool: str, args: dict | None = None) -> list:
        tracing.update_span(input={"tool": tool, "args": args or {}}, metadata={"tool": tool})
        try:
            res = await self.session.call_tool(tool, args or {})
            texts = [c.text for c in res.content if getattr(c, "text", None)]
            if res.isError:
                raise RuntimeError(texts[0] if texts else "tool error")
            tracing.update_span(output=[t[:500] for t in texts])
            return [json.loads(t) for t in texts]
        except Exception as e:
            tracing.update_span(level="ERROR", status_message=str(e)[:300])
            raise
