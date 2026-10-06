import asyncio

import pytest

from src.agent.mcp_client import Warehouse


async def _run(sql):
    async with Warehouse() as wh:
        return await wh.call("run_query", {"sql": sql})


@pytest.mark.parametrize("sql", [
    "SELECT email FROM analytics.CUSTOMERS",
    'SELECT email FROM analytics."Customers"',
    "SELECT c.email FROM analytics.Customers c",
])
def test_email_masked_whatever_the_case(sql):
    res = asyncio.run(_run(sql))
    assert "@" not in str(res)
    assert "***" in str(res)
