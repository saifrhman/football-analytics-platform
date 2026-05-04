.PHONY: build up down logs lint format test ingest-statsbomb ingest-transfermarkt
.PHONY: transform-statsbomb-silver dbt-debug dbt-deps dbt-parse clean

build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

lint:
	ruff check src tests airflow/dags

format:
	ruff format src tests airflow/dags

test:
	pytest

ingest-statsbomb:
	python3 -m football_intelligence.ingestion.statsbomb.run

ingest-transfermarkt:
	python3 -m football_intelligence.ingestion.transfermarkt.run

transform-statsbomb-silver:
	python3 -m football_intelligence.transformations.statsbomb.run

dbt-debug:
	cd dbt/football_intelligence && dbt debug

dbt-deps:
	cd dbt/football_intelligence && dbt deps

dbt-parse:
	cd dbt/football_intelligence && dbt parse

clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache htmlcov .coverage
