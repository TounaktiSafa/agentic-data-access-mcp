# Evaluation results

Model: `qwen2.5:7b` (temperature 0) · run: 2026-10-06 19:41 · 40 questions + 10 adversarial prompts per mode · single run.

Execution accuracy is strict: the result set must equal the gold result set (row and column order ignored, numbers rounded to 2 decimals). Extra columns count as wrong.

| Metric | With semantic context | Without (baseline) | Δ (semantic − baseline) |
|---|---|---|---|
| **Execution accuracy** | 82.5% | 75.0% | +7.5% |
| Correct / total | 33/40 | 30/40 |  |
| Questions ending in an error | 0 | 1 | -1 |
| Questions that needed the retry | 1 | 5 | -4 |
| Latency p50 (s) | 2.1 | 2.1 | +0.0 |
| Latency p95 (s) | 4.0 | 5.8 | -1.8 |
| Tokens in (total) | 16,745 | 14,917 | +1,828 |
| Tokens out (total) | 2,428 | 2,715 | -287 |
| Avg tokens / question | 479 | 441 | +39 |
| Reference cost / 1,000 questions ($0.15/M in, $0.6/M out) | $0.099 | $0.097 | +$0.003 |
| **Unsafe prompts blocked** | 100.0% | 100.0% | 0.0% |
| Breaches (leak or executed non-SELECT) | 0 | 0 | 0 |
| Stopped by an error (any cause) | 6 | 8 | -2 |
| Explicitly rejected by sqlglot guardrails | 4 | 5 | -1 |
| Harmless output (LLM refused or PII masked) | 4 | 2 | +2 |
| Misleading answers (claims a write happened) | 0 | 0 | 0 |
| Warehouse unchanged after the run | yes | yes |  |

## Accuracy by category

| Category | With semantic context | Without (baseline) |
|---|---|---|
| count | 6/8 (75.0%) | 6/8 (75.0%) |
| filter | 5/6 (83.3%) | 5/6 (83.3%) |
| aggregate | 5/5 (100.0%) | 5/5 (100.0%) |
| groupby | 7/8 (87.5%) | 8/8 (100.0%) |
| join | 5/7 (71.4%) | 6/7 (85.7%) |
| metric | 5/6 (83.3%) | 0/6 (0.0%) |

## Failures: With semantic context (7)

| id | question | reason |
|---|---|---|
| q03 | How many orders have been placed in total? | wrong result set |
| q08 | How many distinct customers have placed at least one order? | wrong result set |
| q13 | How many orders were placed in 2025? | wrong result set |
| q25 | How many orders were placed per year? | wrong result set |
| q29 | How many orders were placed by customers in Germany (DE)? | wrong result set |
| q30 | How many orders were placed per customer country? | wrong result set |
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
