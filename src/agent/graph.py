import json
import re
from typing import TypedDict

from langgraph.graph import END, StateGraph

from src import tracing
from src.agent import llm
from src.mcp_server.guardrails import GuardrailError, validate_and_rewrite

MAX_ATTEMPTS = 2  # first try + one retry

# A metric block is shown to the LLM only if the question mentions the metric.
METRIC_HINTS = {
    "revenue": ["sales"],
    "aov": ["average order value", "order value"],
    "average_order_value": ["aov", "order value"],
}

SQL_SYSTEM = (
    "You write DuckDB SQL. Rules: one SELECT statement only; always use schema-qualified "
    "table names (e.g. analytics.orders); no comments; return ONLY the SQL, no explanation."
)

EXPLAIN_SYSTEM = (
    "Answer the business question in 1-3 sentences, using only the SQL result. "
    "This assistant is strictly read-only: it can never drop, delete, update or create anything. "
    "If the question asks to modify data, say the request cannot be done because access is read-only. "
    "If the result is empty or does not answer the question, say so. "
    "Never claim that data was changed."
)


class State(TypedDict, total=False):
    question: str
    tables: list[str]
    metrics: str
    selected: list[str]
    schema_text: str
    sql: str
    error: str
    result: dict
    answer: str
    attempts: int
    tokens_in: int
    tokens_out: int


def build_graph(wh, use_semantic: bool = True):
    def _tok(s, ti, to):
        return {"tokens_in": s["tokens_in"] + ti, "tokens_out": s["tokens_out"] + to}

    async def _schema_text(tables):
        parts = []
        for t in tables:
            cols = await wh.call("describe_table", {"table": t})
            docs = (await wh.call("get_table_docs", {"table": t}))[0] if use_semantic else None
            lines = [
                f"  {c['column']} {c['type']}"
                + (f"  -- {docs['columns'].get(c['column'], '')}" if docs else "")
                for c in cols
            ]
            head = t + (f"  ({docs['description']})" if docs else "")
            parts.append(head + "\n" + "\n".join(lines))
        return "\n\n".join(parts)

    async def understand(s: State):
        tables = [t["table"] for t in await wh.call("list_tables")]
        metrics = ""
        if use_semantic:
            m = (await wh.call("list_metrics"))[0]
            q = s["question"].lower()
            hit = {k: v for k, v in m.items()
                   if any(w in q for w in [k.replace("_", " ").lower(), *METRIC_HINTS.get(k, [])])}
            metrics = "\n".join(
                f"- {k}: {v['description']} -> SELECT {v['expression']} "
                f"FROM {v['from']} WHERE {v['filter']}"
                for k, v in hit.items()
            )
        return {"tables": tables, "metrics": metrics, "attempts": 0,
                "tokens_in": 0, "tokens_out": 0, "error": ""}

    async def pick_tables(s: State):
        txt, ti, to = await llm.chat(
            'Pick the tables needed to answer a business question. '
            'Reply with JSON only: {"tables": ["schema.table", ...]}.',
            f"Available tables: {s['tables']}\nQuestion: {s['question']}",
            json_mode=True,
        )
        try:
            picked = [t for t in json.loads(txt).get("tables", []) if t in s["tables"]]
        except (json.JSONDecodeError, AttributeError):
            picked = []
        picked = picked or s["tables"]

        return {"selected": picked, "schema_text": await _schema_text(picked), **_tok(s, ti, to)}

    async def write_sql(s: State):
        schema_text = s["schema_text"]
        if s.get("error"):  # retry: show every table, not just the picked ones
            schema_text = await _schema_text(s["tables"])
        prompt = f"Schema:\n{schema_text}\n\n"
        if s.get("metrics"):
            prompt += (
                "Official metric definitions. Use them ONLY if the question asks for one of "
                "these metrics; otherwise ignore them and do not add their filters or joins:\n"
                f"{s['metrics']}\n\n"
            )
        prompt += f"Question: {s['question']}"
        if s.get("error"):
            prompt += f"\n\nYour previous SQL failed.\nSQL: {s['sql']}\nError: {s['error']}\nFix it."
        txt, ti, to = await llm.chat(SQL_SYSTEM, prompt)
        sql = re.sub(r"^```(?:sql)?\s*|\s*```$", "", txt.strip(), flags=re.I).strip()
        return {"sql": sql, "schema_text": schema_text, "attempts": s["attempts"] + 1,
                "error": "", **_tok(s, ti, to)}

    async def validate(s: State):
        # Early check so the LLM can fix its SQL. The server re-validates anyway.
        try:
            validate_and_rewrite(s["sql"])
            return {"error": ""}
        except GuardrailError as e:
            return {"error": f"Rejected by guardrails: {e}"}

    async def run(s: State):
        try:
            res = (await wh.call("run_query", {"sql": s["sql"]}))[0]
            return {"result": res, "error": ""}
        except Exception as e:  # SQL error, timeout, server-side guardrail
            return {"error": str(e)}

    async def explain(s: State):
        if s.get("error") or not s.get("result"):
            return {"answer": f"Could not answer safely. Reason: {s.get('error')}"}
        r = s["result"]
        txt, ti, to = await llm.chat(
            EXPLAIN_SYSTEM,
            f"Question: {s['question']}\n"
            f"SQL executed (read-only SELECT): {s['sql']}\n"
            f"Columns: {r['columns']}\nRows (max 20): {r['rows'][:20]}",
        )
        return {"answer": txt.strip(), **_tok(s, ti, to)}

    def after_validate(s: State):
        if not s.get("error"):
            return "run"
        return "write_sql" if s["attempts"] < MAX_ATTEMPTS else "explain"

    def after_run(s: State):
        if not s.get("error"):
            return "explain"
        return "write_sql" if s["attempts"] < MAX_ATTEMPTS else "explain"

    g = StateGraph(State)
    for name, fn in [("understand", understand), ("pick_tables", pick_tables),
                     ("write_sql", write_sql), ("validate", validate),
                     ("run", run), ("explain", explain)]:
        g.add_node(name, tracing.observe(name=f"node.{name}")(fn))
    g.set_entry_point("understand")
    g.add_edge("understand", "pick_tables")
    g.add_edge("pick_tables", "write_sql")
    g.add_edge("write_sql", "validate")
    g.add_conditional_edges("validate", after_validate, ["run", "write_sql", "explain"])
    g.add_conditional_edges("run", after_run, ["explain", "write_sql"])
    g.add_edge("explain", END)
    return g.compile()
