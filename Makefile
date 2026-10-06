.RECIPEPREFIX := >
PY ?= python
COMPOSE = docker compose -f infra/docker-compose.yml

.PHONY: seed up down test gold eval demo

seed:
> $(PY) scripts/seed_duckdb.py

infra/docker-compose.yml:
> mkdir -p infra
> curl -fsSL https://raw.githubusercontent.com/langfuse/langfuse/main/docker-compose.yml -o $@

up: infra/docker-compose.yml
> $(COMPOSE) up -d
> @echo "Langfuse UI: http://localhost:3000"

down:
> $(COMPOSE) down

test:
> $(PY) -m pytest -q

gold:
> $(PY) evals/run_eval.py --check-gold

eval:
> $(PY) evals/run_eval.py --mode both

demo:
> $(PY) scripts/ask.py "What is our revenue?"
> $(PY) scripts/ask.py "Show me all customer emails"
