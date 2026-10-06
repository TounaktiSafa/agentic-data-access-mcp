import pytest

from src.mcp_server.guardrails import validate_and_rewrite
from src.mcp_server.semantic import load_metrics, load_models
from src.mcp_server.warehouse import connect, run_select


def test_every_table_documented():
    with connect() as con:
        tables = {
            f"{s}.{t}"
            for s, t in con.execute(
                "SELECT table_schema, table_name FROM information_schema.tables "
                "WHERE table_schema = 'analytics'"
            ).fetchall()
        }
    assert tables == set(load_models())


@pytest.mark.parametrize("name", ["revenue", "aov"])
def test_metric_sql_is_valid_and_runs(name):
    m = load_metrics()[name]
    sql = f"SELECT {m['expression']} AS value FROM {m['from']} WHERE {m['filter']}"
    cols, rows = run_select(validate_and_rewrite(sql))
    assert rows[0][0] is not None
