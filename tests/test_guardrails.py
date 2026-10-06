import pytest

from src.mcp_server.guardrails import GuardrailError, validate_and_rewrite
from src.mcp_server.warehouse import run_select


@pytest.mark.parametrize("sql", [
    "DROP TABLE analytics.orders",
    "DELETE FROM analytics.orders",
    "INSERT INTO analytics.orders VALUES (1, 1, DATE '2024-01-01', 'x')",
    "CREATE TABLE analytics.x AS SELECT 1",
    "SELECT 1; DROP TABLE analytics.orders",
    "SELECT * FROM internal.audit_log",
    "SELECT * FROM orders",
    "SELECT * FROM read_csv('/etc/passwd')",
    "ATTACH 'other.db'",
    "COPY analytics.orders TO 'out.csv'",
    "SELEKT nonsense",
])
def test_blocked(sql):
    with pytest.raises(GuardrailError):
        validate_and_rewrite(sql)


def test_limit_forced():
    out = validate_and_rewrite("SELECT * FROM analytics.orders")
    assert "LIMIT 100" in out


def test_limit_capped():
    assert "LIMIT 100" in validate_and_rewrite("SELECT * FROM analytics.orders LIMIT 100000")


def test_small_limit_kept():
    assert "LIMIT 5" in validate_and_rewrite("SELECT * FROM analytics.orders LIMIT 5")


def test_valid_aggregate():
    out = validate_and_rewrite(
        "SELECT country, COUNT(*) AS n FROM analytics.customers GROUP BY country"
    )
    assert "analytics.customers" in out


@pytest.mark.parametrize("sql", [
    "SELECT email FROM analytics.customers",
    "SELECT email AS e FROM analytics.customers",
    "SELECT * FROM analytics.customers",
])
def test_pii_masked_end_to_end(sql):
    cols, rows = run_select(validate_and_rewrite(sql))
    flat = [v for r in rows for v in r]
    assert not any("@example.com" in str(v) for v in flat)
