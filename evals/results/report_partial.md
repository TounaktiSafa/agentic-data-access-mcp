# Evaluation results

Model: `qwen2.5:7b` (temperature 0) · run: 2026-10-06 20:55 · 40 questions + 0 adversarial prompts per mode · single run.

Execution accuracy is strict: the result set must equal the gold result set (row and column order ignored, numbers rounded to 2 decimals). Extra columns count as wrong.

| Metric | Without (baseline) |
|---|---|
| **Execution accuracy** | 75.0% |
| Correct / total | 30/40 |
| Questions ending in an error | 1 |
| Questions that needed the retry | 5 |
| Latency p50 (s) | 1.9 |
| Latency p95 (s) | 5.5 |
| Tokens in (total) | 14,917 |
| Tokens out (total) | 2,705 |
| Avg tokens / question | 441 |
| Reference cost / 1,000 questions ($0.15/M in, $0.6/M out) | $0.097 |
| **Unsafe prompts blocked** | n/a |
| Breaches (leak or executed non-SELECT) | 0 |
| Stopped by an error (any cause) | 0 |
| Explicitly rejected by sqlglot guardrails | 0 |
| Harmless output (LLM refused or PII masked) | 0 |
| Misleading answers (claims a write happened) | 0 |
| Warehouse unchanged after the run | yes |

## Accuracy by category

| Category | Without (baseline) |
|---|---|
| count | 6/8 (75.0%) |
| filter | 5/6 (83.3%) |
| aggregate | 5/5 (100.0%) |
| groupby | 8/8 (100.0%) |
| join | 6/7 (85.7%) |
| metric | 0/6 (0.0%) |

## Failures: Without (baseline) (10)

| id | question | reason |
|---|---|---|
| q05 | How many orders were cancelled? | wrong result set |
| q06 | How many orders were refunded? | wrong result set |
| q09 | How many customers are from Tunisia? | wrong result set |
| q19 | What was our revenue in 2024? | wrong result set |
| q20 | What is our revenue from the tech category? | wrong result set |
| q35 | How many order lines belong to cancelled orders? | wrong result set |
| q37 | What is our total revenue? | wrong result set |
| q38 | What is our average order value? | Error executing tool run_query: Binder Error: Values list "T2" does not have a c |
| q39 | What is our revenue per product category? | wrong result set |
| q40 | What is our revenue per customer country? | wrong result set |
