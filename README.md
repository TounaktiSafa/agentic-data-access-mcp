# Agentic Data Access with MCP

A safe MCP server that lets an AI agent query a warehouse, plus a measured evaluation of how well it works.

![architecture](docs/architecture.png)

```
LangGraph agent -> MCP client -> MCP server (guardrails + semantic layer) -> read-only DuckDB
                                   Langfuse traces every agent step and MCP call
```

## Problem

Giving an LLM a SQL connection is risky and unreliable. It can write a DROP, leak PII, or answer "revenue" with the wrong definition. This project puts the controls in a **MCP server** (not in the prompt) and **measures** both safety and accuracy.

## Tech and why

| Piece | Why |
|---|---|
| MCP (FastMCP) | One governed entry point to the data. Any agent or client can reuse it. |
| sqlglot | Real SQL parsing for validation. Regex cannot reliably spot multi-statements or hidden writes. |
| DuckDB | Fast local start, read-only mode, no external access. Snowflake is the next step. |
| LangGraph + Ollama (qwen2.5:7b) | Explicit graph with one retry, free local inference, temperature 0. |
| Semantic layer (dbt-style `manifest.json` + `metrics.yml`) | Table and column docs plus official revenue/AOV definitions. |
| Langfuse (self-hosted) | One trace per question: nodes, MCP calls, LLM calls with token counts. |

## How to run

```bash
pip install -r requirements.txt && ollama pull qwen2.5:7b
make seed                  # builds data/shop.duckdb
make test                  # 52 tests, no LLM needed
make demo                  # two example questions (needs Ollama running)
make eval                  # 40 questions x 2 modes + 10 adversarial prompts -> docs/results.md
```

Optional tracing: `make up`, create keys at http://localhost:3000, export `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST`. Unset them for clean latency runs.

## Results

qwen2.5:7b, temperature 0, 40 business questions with gold SQL, 10 adversarial prompts. Execution accuracy is strict: the result set must equal the gold result set. Full tables in [docs/results.md](docs/results.md).

| | With semantic context | Without (baseline) |
|---|---|---|
| **Execution accuracy** | **97.5% (39/40)** | 75.0% (30/40) |
| Metric questions (revenue, AOV) | 5/6 | 0/6 |
| The other 34 questions | 34/34 | 30/34 |
| Questions that needed the retry | 2 | 5 |
| Latency p50 / p95 † | 1.7 s / 3.7 s | 1.9 s / 5.5 s |
| Avg tokens per question | 490 | 441 |
| Reference cost per 1,000 questions | $0.100 | $0.097 |
| Adversarial prompts: breaches | 0 / 10 | 0 / 10 |
| Rejected outright by sqlglot | 4 | 5 |
| Warehouse unchanged after the run | yes | yes |

† Clean rerun on an idle laptop. Accuracy and tokens were identical across the two runs. Indicative only.

**Three runs, honestly.** The prompt and docs were changed after looking at the eval set, so the 97.5% is a tuned number, not a held-out result.

| Run | What changed | Semantic | Baseline |
|---|---|---|---|
| 1 | First version | 34/40 | 30/40 |
| 2 | Metric definitions shown only when the question mentions them; full schema on retry | 33/40 | 30/40 |
| 3 | Removed the "only completed counts as sales" sentence from the `orders` table docs | 39/40 | 30/40 |

**What the numbers say**
- The semantic layer's real win is the metric questions: 0/6 to 5/6. The baseline cannot know that "revenue" means completed orders only.
- The baseline also guessed value formats (`'Cancelled'`, `'Tunisia'`: q05, q06, q09, q35), which column docs fix.
- Run 1 had semantic *below* baseline on non-metric questions (29/34 vs 30/34). The cause was one business rule stated in two places: the always-visible table docs leaked it into unrelated questions. Run 3 fixed that.
- Remaining semantic failure: q39 (revenue per category). The model drops the `completed` filter once a GROUP BY is added.
- Forty questions in one run means one question is 2.5 points. Read differences below about 5 points as noise.
- Safety: 0 breaches in 10 prompts per mode is a demonstration, not a proof.

## Design decisions and trade-offs

- **Guardrails live in the server, not the prompt.** The agent has an early `validate` node, but the server re-validates everything. See [docs/guardrails.md](docs/guardrails.md).
- **Masking at the table level.** The table becomes `SELECT * REPLACE ('***' AS email)`, so no filter, alias or function can reach the raw column.
- **Retry once, with a wider schema.** Run 1 showed that a retry with the same incomplete schema cannot fix a wrong table choice.
- **State each business rule once.** Metric definitions are shown only when the question mentions the metric. Duplicating a rule in the table docs caused the leak above.
- **Strict evaluation.** Extra columns count as wrong, so some "wrong" answers are cosmetic. Gold SQL is validated against the guardrails before any LLM run.
- **A test found a hole the eval missed.** `analytics.CUSTOMERS` bypassed masking until a targeted test caught it.
- **Limits.** Single run per mode, a single 7B model, seed data where top-N would tie, and the tuning caveat above.

## Cost

Local inference is free. For a reference, at an assumed small hosted rate ($0.15 per 1M input, $0.60 per 1M output tokens), about **$0.10 per 1,000 questions**. The semantic layer adds about 11% more tokens (490 vs 441 per question). Langfuse is self-hosted.

## What I'd do next

1. **Compile metrics into SQL in a tool** (`metric + dimensions` to SQL) instead of trusting a 7B model with the definition. This removes the q39-style failures.
2. Swap DuckDB for Snowflake with a dedicated read-only role. The guardrail layers stay the same.
3. A held-out question set, more adversarial prompts (case, comments, encodings), and several runs per mode.
4. Support `UNION` and CTE edge cases, a column-level allow-list, per-user auth and rate limits.

## Demo and trace

- Demo video: _link_
- Example trace: ![trace](docs/trace.png)
