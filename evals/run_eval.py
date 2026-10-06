"""Evaluation harness for the text-to-SQL agent.

  python evals/run_eval.py --check-gold            # validate gold SQL only (no LLM needed)
  python evals/run_eval.py --mode both --limit 5   # quick smoke test
  python evals/run_eval.py --mode both             # full run -> evals/results/*.json + docs/results.md

Run the full evaluation WITHOUT the LANGFUSE_* env vars so latency is not affected by tracing.
"""
import argparse
import asyncio
import datetime as dt
import json
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)  # relative paths (data/shop.duckdb) resolve like they do for the MCP server

import duckdb  # noqa: E402
import yaml  # noqa: E402

from evals import metrics  # noqa: E402
from src import tracing  # noqa: E402
from src.agent import llm  # noqa: E402
from src.agent.graph import build_graph  # noqa: E402
from src.agent.mcp_client import Warehouse  # noqa: E402
from src.agent.run import ask  # noqa: E402
from src.mcp_server.guardrails import GuardrailError, validate_and_rewrite  # noqa: E402

DB_PATH = os.getenv("WAREHOUSE_PATH", "data/shop.duckdb")
RESULTS_DIR = ROOT / "evals" / "results"
EXPECTED_ROWS = {
    "analytics.customers": 500,
    "analytics.products": 50,
    "analytics.orders": 5000,
    "analytics.order_items": 12000,
    "internal.audit_log": 10,
}
CATEGORIES = ["count", "filter", "aggregate", "groupby", "join", "metric"]
LABELS = {"semantic": "With semantic context", "baseline": "Without (baseline)"}


def load(name: str) -> list[dict]:
    return yaml.safe_load((ROOT / "evals" / name).read_text(encoding="utf-8"))


def run_gold(con, sql: str) -> list:
    return con.execute(sql).fetchall()


def warehouse_intact(con) -> bool:
    try:
        return all(
            con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] == n
            for t, n in EXPECTED_ROWS.items()
        )
    except Exception:
        return False


# ---------------------------------------------------------------- gold validation

def check_gold() -> int:
    questions = load("questions.yaml")
    adversarial = load("adversarial.yaml")
    problems = 0
    if len(questions) != 40:
        print(f"[WARN] expected 40 questions, found {len(questions)}")
        problems += 1
    if len({q["id"] for q in questions}) != len(questions):
        print("[WARN] duplicate question ids")
        problems += 1
    if len(adversarial) != 10:
        print(f"[WARN] expected 10 adversarial prompts, found {len(adversarial)}")
        problems += 1

    con = duckdb.connect(DB_PATH, read_only=True)
    for q in questions:
        try:
            rows = run_gold(con, q["gold_sql"])
        except Exception as e:
            print(f"[FAIL] {q['id']}: {e}")
            problems += 1
            continue
        note = ""
        if not rows:
            note = "  <-- EMPTY gold result"
        elif len(rows) > 50:
            note = "  <-- more than 50 rows (row cap risk)"
        try:
            validate_and_rewrite(q["gold_sql"])
        except GuardrailError as e:
            note += f"  <-- guardrails reject this gold SQL: {e}"
        problems += bool(note)
        print(f"[{'!!' if note else 'ok'}] {q['id']} {q['category']:<9} {len(rows):>3} rows  "
              f"{str(rows[:2])[:60]}{note}")
    con.close()
    print(f"\n{len(questions)} questions, {len(adversarial)} adversarial prompts, {problems} problem(s)")
    return problems


# ---------------------------------------------------------------- runs

async def run_questions(graph, questions, gold_con, use_semantic, label):
    records = []
    for i, q in enumerate(questions, 1):
        gold_rows = run_gold(gold_con, q["gold_sql"])
        try:
            out = await ask(graph, q["question"], use_semantic)
        except Exception as e:  # e.g. Ollama timeout: record it and keep going
            out = {"error": f"agent crashed: {e}", "latency_s": 0.0}
        rows = (out.get("result") or {}).get("rows")
        correct = bool(
            not out.get("error") and rows is not None and metrics.results_match(gold_rows, rows)
        )
        records.append({
            "id": q["id"], "category": q["category"], "question": q["question"],
            "correct": correct, "sql": out.get("sql"), "error": out.get("error") or "",
            "attempts": out.get("attempts", 0), "latency_s": out.get("latency_s", 0.0),
            "tokens_in": out.get("tokens_in", 0), "tokens_out": out.get("tokens_out", 0),
        })
        print(f"[{label}] {i:>2}/{len(questions)} {q['id']} {'OK ' if correct else 'BAD'} "
              f"{records[-1]['latency_s']:.1f}s")
    return records


async def run_adversarial(graph, prompts, use_semantic, label):
    records = []
    for i, a in enumerate(prompts, 1):
        try:
            out = await ask(graph, a["prompt"], use_semantic)
        except Exception as e:
            out = {"error": f"agent crashed: {e}", "latency_s": 0.0}
        cls = metrics.classify_adversarial(a["kind"], out)
        records.append({
            "id": a["id"], "kind": a["kind"], "prompt": a["prompt"], "sql": out.get("sql"),
            "error": out.get("error") or "", "answer": (out.get("answer") or "")[:300], **cls,
        })
        print(f"[{label}] adv {i:>2}/{len(prompts)} {a['id']} {cls['outcome']}"
              f"{'  (MISLEADING ANSWER)' if cls['claims_write'] else ''}")
    return records


# ---------------------------------------------------------------- report

def _pct(x):
    return "n/a" if x is None else f"{100 * x:.1f}%"


def render_report(runs: dict) -> str:
    names = list(runs)
    both = names == ["semantic", "baseline"]
    q = {n: metrics.summarize_questions(runs[n]["questions"]) for n in names}
    s = {n: metrics.summarize_adversarial(runs[n]["adversarial"]) for n in names}
    first = runs[names[0]]

    lines = [
        "# Evaluation results",
        "",
        f"Model: `{first['model']}` (temperature 0) · run: {first['timestamp']} · "
        f"{q[names[0]]['n']} questions + {s[names[0]]['n']} adversarial prompts per mode · single run.",
        "",
        "Execution accuracy is strict: the result set must equal the gold result set "
        "(row and column order ignored, numbers rounded to 2 decimals). Extra columns count as wrong.",
        "",
        "| Metric | " + " | ".join(LABELS[n] for n in names) + (" | Δ (semantic − baseline) |" if both else " |"),
        "|---|" + "---|" * (len(names) + (1 if both else 0)),
    ]

    def row(title, getter, fmt, delta=True):
        vals = [getter(n) for n in names]
        cells = [fmt(v) if v is not None else "n/a" for v in vals]
        d = ""
        if both:
            if delta and all(isinstance(v, (int, float)) for v in vals):
                diff = vals[0] - vals[1]
                d = f" | {'+' if diff > 0 else ''}{fmt(diff)}"
            else:
                d = " | "
        lines.append(f"| {title} | " + " | ".join(cells) + d + " |")

    row("**Execution accuracy**", lambda n: q[n]["accuracy"], _pct)
    row("Correct / total", lambda n: f"{q[n]['correct']}/{q[n]['n']}", str, delta=False)
    row("Questions ending in an error", lambda n: q[n]["errors"], str)
    row("Questions that needed the retry", lambda n: q[n]["retried"], str)
    row("Latency p50 (s)", lambda n: q[n]["latency_p50"], lambda v: f"{v:.1f}")
    row("Latency p95 (s)", lambda n: q[n]["latency_p95"], lambda v: f"{v:.1f}")
    row("Tokens in (total)", lambda n: q[n]["tokens_in"], lambda v: f"{v:,.0f}")
    row("Tokens out (total)", lambda n: q[n]["tokens_out"], lambda v: f"{v:,.0f}")
    row("Avg tokens / question", lambda n: q[n]["avg_tokens"], lambda v: f"{v:,.0f}")
    row(f"Reference cost / 1,000 questions (${metrics.PRICE_IN_PER_M}/M in, "
        f"${metrics.PRICE_OUT_PER_M}/M out)", lambda n: q[n]["cost_per_1k"], lambda v: f"${v:.3f}")
    row("**Unsafe prompts blocked**", lambda n: s[n]["blocked_rate"], _pct)
    row("Breaches (leak or executed non-SELECT)", lambda n: s[n]["breaches"], str)
    row("Stopped by an error (any cause)", lambda n: s[n]["guardrail_blocked"], str)
    row("Explicitly rejected by sqlglot guardrails", lambda n: s[n]["rejected"], str)
    row("Harmless output (LLM refused or PII masked)", lambda n: s[n]["safe_output"], str)
    row("Misleading answers (claims a write happened)", lambda n: s[n]["misleading"], str)
    row("Warehouse unchanged after the run", lambda n: "yes" if runs[n]["warehouse_intact"] else "NO", str, delta=False)

    lines += ["", "## Accuracy by category", "",
              "| Category | " + " | ".join(LABELS[n] for n in names) + " |",
              "|---|" + "---|" * len(names)]
    for cat in CATEGORIES:
        cells = []
        for n in names:
            c, t = q[n]["by_category"].get(cat, [0, 0])
            cells.append(f"{c}/{t} ({_pct(c / t)})" if t else "n/a")
        lines.append(f"| {cat} | " + " | ".join(cells) + " |")

    for n in names:
        failed = [r for r in runs[n]["questions"] if not r["correct"]]
        lines += ["", f"## Failures: {LABELS[n]} ({len(failed)})", "",
                  "| id | question | reason |", "|---|---|---|"]
        for r in failed:
            why = r["error"][:80].replace("|", "/") if r["error"] else "wrong result set"
            lines.append(f"| {r['id']} | {r['question']} | {why} |")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- main

async def amain(args):
    questions = load("questions.yaml")[: args.limit]
    prompts = [] if args.skip_adversarial else load("adversarial.yaml")[: args.limit]
    modes = {
        "both": [("semantic", True), ("baseline", False)],
        "semantic": [("semantic", True)],
        "baseline": [("baseline", False)],
    }[args.mode]

    RESULTS_DIR.mkdir(exist_ok=True)
    gold_con = duckdb.connect(DB_PATH, read_only=True)
    runs = {}
    async with Warehouse() as wh:
        for name, use_sem in modes:
            graph = build_graph(wh, use_semantic=use_sem)
            q_rec = await run_questions(graph, questions, gold_con, use_sem, name)
            a_rec = await run_adversarial(graph, prompts, use_sem, name)
            runs[name] = {
                "model": llm.MODEL,
                "timestamp": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
                "questions": q_rec,
                "adversarial": a_rec,
                "warehouse_intact": warehouse_intact(gold_con),
            }
            (RESULTS_DIR / f"{name}.json").write_text(
                json.dumps(runs[name], indent=2, default=str), encoding="utf-8")
    tracing.flush()

    report = render_report(runs)
    partial = args.limit is not None or args.skip_adversarial or args.mode != "both"
    path = RESULTS_DIR / "report_partial.md" if partial else ROOT / "docs" / "results.md"
    path.write_text(report, encoding="utf-8")
    print("\n" + report)
    print(f"Report written to {path.relative_to(ROOT)}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--mode", choices=["both", "semantic", "baseline"], default="both")
    p.add_argument("--limit", type=int, default=None, help="only the first N questions / prompts")
    p.add_argument("--skip-adversarial", action="store_true")
    p.add_argument("--check-gold", action="store_true")
    args = p.parse_args()
    if args.check_gold:
        sys.exit(1 if check_gold() else 0)
    asyncio.run(amain(args))


if __name__ == "__main__":
    main()
