import pytest

from src.mcp_server.guardrails import validate_and_rewrite


@pytest.mark.parametrize("sql", [
    "SELECT email FROM analytics.CUSTOMERS",
    "SELECT email FROM analytics.Customers",
    'SELECT email FROM analytics."Customers"',
    "SELECT c.email FROM analytics.customers AS c",
    "SELECT analytics.customers.email FROM analytics.customers",
    "WITH x AS (SELECT * FROM analytics.customers) SELECT email FROM x",
    "SELECT email FROM (SELECT * FROM analytics.customers) t",
])
def test_pii_always_masked(sql):
    assert "'***' AS email" in validate_and_rewrite(sql)
