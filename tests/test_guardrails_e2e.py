"""Sends SQL straight to the MCP server's run_query tool, with no LLM involved.
Proves the guardrails hold no matter what the model writes."""
import asyncio

import pytest

from src.agent.mcp_client import Warehouse


async def _run(sql):
    async with Warehouse() as wh:
        return await wh.call("run_query", {"sql": sql})


@pytest.mark.parametrize("sql", [
    "DROP TABLE analytics.orders",
    "DELETE FROM analytics.customers",
    "UPDATE analytics.products SET price = 0",
    "SELECT 1; DROP TABLE analytics.orders",
    "SELECT * FROM internal.audit_log",
    "SELECT * FROM sys.audit_log",
])
def test_dangerous_sql_is_rejected(sql):
    with pytest.raises(RuntimeError):
        asyncio.run(_run(sql))


@pytest.mark.parametrize("sql", [
    "SELECT email FROM analytics.customers",
    "SELECT c.email FROM analytics.customers c",
    "SELECT analytics.customers.email FROM analytics.customers",
    "SELECT * FROM analytics.customers",
    "SELECT lower(email) FROM analytics.customers",
])
def test_email_never_leaks(sql):
    try:
        res = asyncio.run(_run(sql))
    except RuntimeError:
        return  # rejected outright is fine too
    assert "@" not in str(res)
