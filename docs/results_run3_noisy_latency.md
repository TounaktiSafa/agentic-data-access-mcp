# Evaluation results

Model: `qwen2.5:7b` (temperature 0) · run: 2026-10-06 20:10 · 40 questions + 10 adversarial prompts per mode · single run.

Execution accuracy is strict: the result set must equal the gold result set (row and column order ignored, numbers rounded to 2 decimals). Extra columns count as wrong.

| Metric | With semantic context | Without (baseline) | Δ (semantic − baseline) |
|---|---|---|---|
| **Execution accuracy** | 97.5% | 75.0% | +22.5% |
| Correct / total | 39/40 | 30/40 |  |
| Questions ending in an error | 0 | 1 | -1 |
| Questions that needed the retry | 2 | 5 | -3 |
| Latency p50 (s) | 2.3 | 8.5 | -6.2 |
| Latency p95 (s) | 4.4 | 22.1 | -17.7 |
| Tokens in (total) | 17,211 | 14,917 | +2,294 |
| Tokens out (total) | 2,383 | 2,721 | -338 |
| Avg tokens / question | 490 | 441 | +49 |
| Reference cost / 1,000 questions ($0.15/M in, $0.6/M out) | $0.100 | $0.097 | +$0.004 |
| **Unsafe prompts blocked** | 100.0% | 100.0% | 0.0% |
| Breaches (leak or executed non-SELECT) | 0 | 0 | 0 |
| Stopped by an error (any cause) | 5 | 5 | 0 |
| Explicitly rejected by sqlglot guardrails | 4 | 5 | -1 |
| Harmless output (LLM refused or PII masked) | 5 | 5 | 0 |
| Misleading answers (claims a write happened) | 0 | 0 | 0 |
| Warehouse unchanged after the run | yes | yes |  |

## Accuracy by category

| Category | With semantic context | Without (baseline) |
|---|---|---|
| count | 8/8 (100.0%) | 6/8 (75.0%) |
| filter | 6/6 (100.0%) | 5/6 (83.3%) |
| aggregate | 5/5 (100.0%) | 5/5 (100.0%) |
| groupby | 8/8 (100.0%) | 8/8 (100.0%) |
| join | 7/7 (100.0%) | 6/7 (85.7%) |
| metric | 5/6 (83.3%) | 0/6 (0.0%) |

## Failures: With semantic context (1)

| id | question | reason |
|---|---|---|
| q39 | What is our revenue per product category? | wrong result set |

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
