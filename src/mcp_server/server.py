from mcp.server.fastmcp import FastMCP

from src.mcp_server.guardrails import ALLOWED_SCHEMAS, MAX_ROWS, validate_and_rewrite
from src.mcp_server.warehouse import connect, run_select
from src.mcp_server.semantic import load_metrics, load_models

mcp = FastMCP("warehouse")

@mcp.tool()
def get_table_docs(table: str) -> dict:
    """Business description of a table and its columns (from the dbt manifest)."""
    schema = table.split(".", 1)[0]
    if schema not in ALLOWED_SCHEMAS:
        raise ValueError(f"Schema '{schema}' is not allowed")
    models = load_models()
    if table not in models:
        raise ValueError(f"No docs for '{table}'")
    return models[table]


@mcp.tool()
def list_metrics() -> dict:
    """Official business metric definitions (revenue, aov): expression, joins, filter."""
    return load_metrics()

@mcp.tool()
def list_tables() -> list[dict]:
    """List the tables the agent is allowed to query (schema.table)."""
    with connect() as con:
        rows = con.execute(
            """
            SELECT table_schema, table_name
            FROM information_schema.tables
            WHERE list_contains(?, table_schema)
            ORDER BY 1, 2
            """,
            [sorted(ALLOWED_SCHEMAS)],
        ).fetchall()
    return [{"table": f"{s}.{t}"} for s, t in rows]


@mcp.tool()
def describe_table(table: str) -> list[dict]:
    """Describe the columns of a table. Use the form schema.table."""
    if "." not in table:
        raise ValueError("Use the form schema.table")
    schema, name = table.split(".", 1)
    if schema not in ALLOWED_SCHEMAS:
        raise ValueError(f"Schema '{schema}' is not allowed")
    with connect() as con:
        rows = con.execute(
            """
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = ? AND table_name = ?
            ORDER BY ordinal_position
            """,
            [schema, name],
        ).fetchall()
    if not rows:
        raise ValueError(f"Table '{table}' not found")
    return [{"column": c, "type": t} for c, t in rows]


@mcp.tool()
def run_query(sql: str) -> dict:
    """Run ONE read-only SELECT on analytics.* tables (max 100 rows, 5 s timeout).
    Tables must be schema-qualified. PII columns are masked."""
    safe_sql = validate_and_rewrite(sql)  # raises GuardrailError if unsafe
    cols, rows = run_select(safe_sql, timeout_s=5.0, max_rows=MAX_ROWS)
    clean = [
        [v if isinstance(v, (int, float, str, bool, type(None))) else str(v) for v in r]
        for r in rows
    ]
    return {"columns": cols, "rows": clean, "row_count": len(clean), "executed_sql": safe_sql}


if __name__ == "__main__":
    mcp.run()
