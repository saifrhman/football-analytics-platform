PYTHON ?= $(shell if [ -x .venv/bin/python ]; then echo .venv/bin/python; else echo python3; fi)

.PHONY: build up down logs lint format test ingest-statsbomb ingest-statsbomb-sample ingest-transfermarkt
.PHONY: transform-statsbomb-silver transform-statsbomb-silver-sample dbt-debug dbt-deps dbt-parse clean

build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

lint:
	$(PYTHON) -m ruff check src tests airflow/dags

format:
	$(PYTHON) -m ruff format src tests airflow/dags

test:
	$(PYTHON) -m pytest

ingest-statsbomb:
	python3 -m football_intelligence.ingestion.statsbomb.run

ingest-statsbomb-sample:
	python3 -m football_intelligence.ingestion.statsbomb.run \
		--competition-ids 2 \
		--season-ids 44 \
		--match-limit 5 \
		--bronze-dir ./data/bronze

ingest-transfermarkt:
	python3 -m football_intelligence.ingestion.transfermarkt.run

transform-statsbomb-silver:
	python3 -m football_intelligence.transformations.statsbomb.run

transform-statsbomb-silver-sample:
	python3 -m football_intelligence.transformations.statsbomb.run \
		--bronze-open-data-dir ./data/bronze/statsbomb/open-data \
		--silver-dir ./data/silver/statsbomb

dbt-debug:
	cd dbt/football_intelligence && dbt debug

dbt-deps:
	cd dbt/football_intelligence && dbt deps

dbt-parse:
	cd dbt/football_intelligence && dbt parse

clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache htmlcov .coverage
