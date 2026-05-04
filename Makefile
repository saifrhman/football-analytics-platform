PYTHON ?= $(shell if [ -x .venv/bin/python ]; then echo .venv/bin/python; else echo python3; fi)
DBT ?= $(shell if [ -x .venv/bin/dbt ]; then echo ../../.venv/bin/dbt; else echo dbt; fi)
DBT_WITH_ENV = set -a; [ ! -f ../../.env ] || . ../../.env; set +a; $(DBT)

.PHONY: build up down logs lint format test ingest-statsbomb ingest-statsbomb-sample ingest-transfermarkt load-statsbomb-bigquery
.PHONY: transform-statsbomb-silver transform-statsbomb-silver-sample dbt-debug dbt-deps dbt-parse dbt-run dbt-test dbt-docs-generate clean

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

load-statsbomb-bigquery:
	python3 -m football_intelligence.loaders.bigquery.statsbomb_silver

dbt-debug:
	cd dbt/football_intelligence && $(DBT_WITH_ENV) debug

dbt-deps:
	cd dbt/football_intelligence && $(DBT_WITH_ENV) deps

dbt-parse:
	cd dbt/football_intelligence && $(DBT_WITH_ENV) parse

dbt-run:
	cd dbt/football_intelligence && $(DBT_WITH_ENV) run

dbt-test:
	cd dbt/football_intelligence && $(DBT_WITH_ENV) test

dbt-docs-generate:
	cd dbt/football_intelligence && $(DBT_WITH_ENV) docs generate

clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache htmlcov .coverage
