import sqlglot
from sqlglot import exp

ALLOWED_SCHEMAS = {"analytics"}
MAX_ROWS = 100
PII_MASKS = {"analytics.customers": ["email"]}  # schema.table -> columns to mask

_FORBIDDEN = (exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Create, exp.Alter, exp.Command)


class GuardrailError(ValueError):
    pass


def validate_and_rewrite(sql: str) -> str:
    """Return a safe SQL string, or raise GuardrailError."""
    try:
        statements = sqlglot.parse(sql, read="duckdb")
    except sqlglot.errors.SqlglotError as e:
        raise GuardrailError(f"SQL parse error: {e}")

    statements = [s for s in statements if s is not None]
    if len(statements) != 1:
        raise GuardrailError("Exactly one statement is allowed")

    tree = statements[0]
    if not isinstance(tree, exp.Select):
        raise GuardrailError("Only SELECT statements are allowed")
    if tree.args.get("into"):
        raise GuardrailError("SELECT INTO is not allowed")
    if any(isinstance(n, _FORBIDDEN) for n in tree.walk()):
        raise GuardrailError("Write/DDL operations are not allowed")

    # Allow-list: schema-qualified tables in allowed schemas, no table functions
    cte_names = {c.alias for c in tree.find_all(exp.CTE)}
    tables = list(tree.find_all(exp.Table))
    for t in tables:
        if not isinstance(t.this, exp.Identifier):
            raise GuardrailError("Table functions are not allowed")
        if not t.db:
            if t.name in cte_names:
                continue
            raise GuardrailError(f"Use schema-qualified tables (schema.table): {t.name}")
        if t.catalog or t.db not in ALLOWED_SCHEMAS:
            raise GuardrailError(f"Schema not allowed: {t.db}")

    # schema.table.column would not resolve after masking: reduce it to table.column
    for col in tree.find_all(exp.Column):
        col.set("db", None)
        col.set("catalog", None)

    # PII masking: replace the table by a masked subquery (covers SELECT *, aliases)
    for t in tables:
        key = f"{t.db}.{t.name}".lower()  # DuckDB identifiers are case-insensitive
        if key in PII_MASKS:
            cols = ", ".join(f"'***' AS {c}" for c in PII_MASKS[key])
            masked = sqlglot.parse_one(f"SELECT * REPLACE ({cols}) FROM {key}", read="duckdb")
            t.replace(masked.subquery(alias=t.alias or t.name))

    # Force / cap LIMIT
    limit = tree.args.get("limit")
    if limit is None:
        tree = tree.limit(MAX_ROWS)
    else:
        try:
            n = int(limit.expression.name)
        except ValueError:
            n = MAX_ROWS + 1
        if n > MAX_ROWS:
            tree = tree.limit(MAX_ROWS)

    return tree.sql(dialect="duckdb")
