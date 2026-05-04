"""Airflow DAG skeleton for the football intelligence platform."""

from __future__ import annotations

from datetime import datetime

from airflow.decorators import dag, task


@dag(
    dag_id="football_intelligence_pipeline",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    tags=["football", "statsbomb", "transfermarkt", "dbt"],
)
def football_intelligence_pipeline() -> None:
    """Coordinate ingestion, loading, transformations, and quality checks."""

    @task
    def ingest_statsbomb() -> str:
        """Placeholder for StatsBomb Open Data ingestion."""

        return "statsbomb_ingestion_pending"

    @task
    def ingest_transfermarkt() -> str:
        """Placeholder for Transfermarkt ingestion."""

        return "transfermarkt_ingestion_pending"

    @task
    def load_bronze_to_warehouse() -> str:
        """Placeholder for raw-to-warehouse loading."""

        return "warehouse_load_pending"

    @task
    def run_dbt_transformations() -> str:
        """Placeholder for dbt transformations."""

        return "dbt_transformations_pending"

    @task
    def run_quality_checks() -> str:
        """Placeholder for data quality checks."""

        return "quality_checks_pending"

    statsbomb = ingest_statsbomb()
    transfermarkt = ingest_transfermarkt()
    loaded = load_bronze_to_warehouse()
    transformed = run_dbt_transformations()
    checked = run_quality_checks()

    [statsbomb, transfermarkt] >> loaded >> transformed >> checked


football_intelligence_pipeline()
