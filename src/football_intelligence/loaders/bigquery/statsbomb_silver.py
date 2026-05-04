"""Load StatsBomb silver CSV tables into BigQuery."""

from __future__ import annotations

import argparse
import logging
import os
from dataclasses import dataclass
from pathlib import Path

from google.api_core.exceptions import GoogleAPIError
from google.cloud import bigquery

from football_intelligence.config.settings import get_settings
from football_intelligence.logging import configure_logging

logger = logging.getLogger(__name__)

STATSBOMB_SILVER_TABLES = (
    "competitions",
    "matches",
    "teams",
    "players",
    "events",
    "shots",
    "passes",
    "pressures",
    "three_sixty_freeze_frames",
)

SchemaSpec = tuple[str, str, str]

STATSBOMB_SILVER_SCHEMAS: dict[str, tuple[SchemaSpec, ...]] = {
    "competitions": (
        ("competition_id", "INTEGER", "REQUIRED"),
        ("season_id", "INTEGER", "REQUIRED"),
        ("competition_name", "STRING", "NULLABLE"),
        ("country_name", "STRING", "NULLABLE"),
        ("competition_gender", "STRING", "NULLABLE"),
        ("season_name", "STRING", "NULLABLE"),
    ),
    "matches": (
        ("match_id", "INTEGER", "REQUIRED"),
        ("competition_id", "INTEGER", "NULLABLE"),
        ("season_id", "INTEGER", "NULLABLE"),
        ("match_date", "DATE", "NULLABLE"),
        ("kick_off", "STRING", "NULLABLE"),
        ("home_team_id", "INTEGER", "NULLABLE"),
        ("home_team_name", "STRING", "NULLABLE"),
        ("away_team_id", "INTEGER", "NULLABLE"),
        ("away_team_name", "STRING", "NULLABLE"),
        ("home_score", "INTEGER", "NULLABLE"),
        ("away_score", "INTEGER", "NULLABLE"),
        ("stadium_name", "STRING", "NULLABLE"),
        ("referee_name", "STRING", "NULLABLE"),
    ),
    "teams": (
        ("team_id", "INTEGER", "REQUIRED"),
        ("team_name", "STRING", "NULLABLE"),
        ("country_name", "STRING", "NULLABLE"),
    ),
    "players": (
        ("player_id", "INTEGER", "REQUIRED"),
        ("player_name", "STRING", "NULLABLE"),
        ("team_id", "INTEGER", "NULLABLE"),
        ("team_name", "STRING", "NULLABLE"),
        ("jersey_number", "INTEGER", "NULLABLE"),
        ("country_name", "STRING", "NULLABLE"),
    ),
    "events": (
        ("event_id", "STRING", "REQUIRED"),
        ("match_id", "INTEGER", "NULLABLE"),
        ("index", "INTEGER", "NULLABLE"),
        ("period", "INTEGER", "NULLABLE"),
        ("timestamp", "STRING", "NULLABLE"),
        ("minute", "INTEGER", "NULLABLE"),
        ("second", "INTEGER", "NULLABLE"),
        ("possession", "INTEGER", "NULLABLE"),
        ("possession_team_id", "INTEGER", "NULLABLE"),
        ("possession_team_name", "STRING", "NULLABLE"),
        ("team_id", "INTEGER", "NULLABLE"),
        ("team_name", "STRING", "NULLABLE"),
        ("player_id", "INTEGER", "NULLABLE"),
        ("player_name", "STRING", "NULLABLE"),
        ("position_id", "INTEGER", "NULLABLE"),
        ("position_name", "STRING", "NULLABLE"),
        ("event_type_id", "INTEGER", "NULLABLE"),
        ("event_type_name", "STRING", "NULLABLE"),
        ("play_pattern_id", "INTEGER", "NULLABLE"),
        ("play_pattern_name", "STRING", "NULLABLE"),
        ("location_x", "FLOAT", "NULLABLE"),
        ("location_y", "FLOAT", "NULLABLE"),
        ("duration", "FLOAT", "NULLABLE"),
        ("under_pressure", "BOOLEAN", "NULLABLE"),
        ("out", "BOOLEAN", "NULLABLE"),
    ),
    "shots": (
        ("event_id", "STRING", "REQUIRED"),
        ("match_id", "INTEGER", "NULLABLE"),
        ("team_id", "INTEGER", "NULLABLE"),
        ("player_id", "INTEGER", "NULLABLE"),
        ("timestamp", "STRING", "NULLABLE"),
        ("possession", "INTEGER", "NULLABLE"),
        ("location_x", "FLOAT", "NULLABLE"),
        ("location_y", "FLOAT", "NULLABLE"),
        ("end_location_x", "FLOAT", "NULLABLE"),
        ("end_location_y", "FLOAT", "NULLABLE"),
        ("end_location_z", "FLOAT", "NULLABLE"),
        ("xg", "FLOAT", "NULLABLE"),
        ("outcome_id", "INTEGER", "NULLABLE"),
        ("outcome_name", "STRING", "NULLABLE"),
        ("body_part_id", "INTEGER", "NULLABLE"),
        ("body_part_name", "STRING", "NULLABLE"),
        ("technique_id", "INTEGER", "NULLABLE"),
        ("technique_name", "STRING", "NULLABLE"),
        ("first_time", "BOOLEAN", "NULLABLE"),
        ("one_on_one", "BOOLEAN", "NULLABLE"),
        ("statsbomb_xg", "FLOAT", "NULLABLE"),
    ),
    "passes": (
        ("event_id", "STRING", "REQUIRED"),
        ("match_id", "INTEGER", "NULLABLE"),
        ("team_id", "INTEGER", "NULLABLE"),
        ("player_id", "INTEGER", "NULLABLE"),
        ("timestamp", "STRING", "NULLABLE"),
        ("possession", "INTEGER", "NULLABLE"),
        ("location_x", "FLOAT", "NULLABLE"),
        ("location_y", "FLOAT", "NULLABLE"),
        ("end_location_x", "FLOAT", "NULLABLE"),
        ("end_location_y", "FLOAT", "NULLABLE"),
        ("recipient_player_id", "INTEGER", "NULLABLE"),
        ("recipient_player_name", "STRING", "NULLABLE"),
        ("length", "FLOAT", "NULLABLE"),
        ("angle", "FLOAT", "NULLABLE"),
        ("height_id", "INTEGER", "NULLABLE"),
        ("height_name", "STRING", "NULLABLE"),
        ("type_id", "INTEGER", "NULLABLE"),
        ("type_name", "STRING", "NULLABLE"),
        ("outcome_id", "INTEGER", "NULLABLE"),
        ("outcome_name", "STRING", "NULLABLE"),
        ("body_part_id", "INTEGER", "NULLABLE"),
        ("body_part_name", "STRING", "NULLABLE"),
        ("switch", "BOOLEAN", "NULLABLE"),
        ("cross", "BOOLEAN", "NULLABLE"),
        ("cut_back", "BOOLEAN", "NULLABLE"),
        ("assisted_shot_id", "STRING", "NULLABLE"),
        ("shot_assist", "BOOLEAN", "NULLABLE"),
        ("goal_assist", "BOOLEAN", "NULLABLE"),
    ),
    "pressures": (
        ("event_id", "STRING", "REQUIRED"),
        ("match_id", "INTEGER", "NULLABLE"),
        ("team_id", "INTEGER", "NULLABLE"),
        ("player_id", "INTEGER", "NULLABLE"),
        ("timestamp", "STRING", "NULLABLE"),
        ("possession", "INTEGER", "NULLABLE"),
        ("location_x", "FLOAT", "NULLABLE"),
        ("location_y", "FLOAT", "NULLABLE"),
        ("counterpress", "BOOLEAN", "NULLABLE"),
    ),
    "three_sixty_freeze_frames": (
        ("event_id", "STRING", "REQUIRED"),
        ("match_id", "INTEGER", "NULLABLE"),
        ("player_id", "INTEGER", "NULLABLE"),
        ("player_name", "STRING", "NULLABLE"),
        ("teammate", "BOOLEAN", "NULLABLE"),
        ("actor", "BOOLEAN", "NULLABLE"),
        ("keeper", "BOOLEAN", "NULLABLE"),
        ("location_x", "FLOAT", "NULLABLE"),
        ("location_y", "FLOAT", "NULLABLE"),
        ("visible_area", "STRING", "NULLABLE"),
    ),
}


@dataclass(frozen=True)
class BigQueryLoadResult:
    """Summary of one loaded BigQuery table."""

    table_name: str
    table_id: str
    source_path: Path
    source_bytes: int
    output_rows: int | None


class StatsBombSilverBigQueryLoader:
    """Load local StatsBomb silver CSV files into a BigQuery dataset."""

    def __init__(
        self,
        *,
        project_id: str,
        dataset_id: str,
        silver_dir: str | Path,
        client: bigquery.Client | None = None,
    ) -> None:
        self.project_id = project_id
        self.dataset_id = dataset_id
        self.silver_dir = Path(silver_dir).expanduser()
        self.client = client or bigquery.Client(project=project_id)

    def load_all(self) -> list[BigQueryLoadResult]:
        """Load every supported StatsBomb silver table."""

        logger.info(
            "Starting StatsBomb silver BigQuery load project=%s dataset=%s silver_dir=%s",
            self.project_id,
            self.dataset_id,
            self.silver_dir,
        )
        results = [self.load_table(table_name) for table_name in STATSBOMB_SILVER_TABLES]
        logger.info("Finished StatsBomb silver BigQuery load tables=%d", len(results))
        return results

    def load_table(self, table_name: str) -> BigQueryLoadResult:
        """Load a single StatsBomb silver CSV into BigQuery."""

        if table_name not in STATSBOMB_SILVER_SCHEMAS:
            raise ValueError(f"Unsupported StatsBomb silver table: {table_name}")

        source_path = self.silver_dir / f"{table_name}.csv"
        if not source_path.exists():
            raise FileNotFoundError(f"StatsBomb silver CSV not found: {source_path}")

        table_id = f"{self.project_id}.{self.dataset_id}.{table_name}"
        job_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.CSV,
            skip_leading_rows=1,
            schema=_schema_for_table(table_name),
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
            autodetect=False,
            allow_quoted_newlines=True,
        )

        logger.info("Loading StatsBomb silver table %s from %s", table_id, source_path)
        try:
            with source_path.open("rb") as csv_file:
                load_job = self.client.load_table_from_file(
                    csv_file,
                    table_id,
                    job_config=job_config,
                )
            load_job.result()
            table = self.client.get_table(table_id)
        except GoogleAPIError:
            logger.exception("BigQuery load failed table=%s source=%s", table_id, source_path)
            raise

        result = BigQueryLoadResult(
            table_name=table_name,
            table_id=table_id,
            source_path=source_path,
            source_bytes=source_path.stat().st_size,
            output_rows=getattr(table, "num_rows", None),
        )
        logger.info(
            "Loaded StatsBomb silver table %s rows=%s source_bytes=%d",
            result.table_id,
            result.output_rows,
            result.source_bytes,
        )
        return result


def main() -> None:
    """CLI entry point for StatsBomb silver BigQuery loads."""

    configure_logging()
    settings = get_settings()
    args = _parse_args()

    project_id = args.project_id or settings.gcp_project_id
    dataset_id = args.dataset_id or settings.bigquery_dataset_silver
    silver_dir = args.silver_dir or f"{settings.local_silver_dir}/statsbomb"

    _validate_environment(project_id=project_id, dataset_id=dataset_id)
    loader = StatsBombSilverBigQueryLoader(
        project_id=project_id,
        dataset_id=dataset_id,
        silver_dir=silver_dir,
    )

    try:
        loader.load_all()
    except (FileNotFoundError, GoogleAPIError, ValueError):
        logger.exception("StatsBomb silver BigQuery load failed")
        raise


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Load StatsBomb silver CSVs into BigQuery.")
    parser.add_argument("--silver-dir", help="Local StatsBomb silver CSV directory.")
    parser.add_argument("--project-id", help="GCP project ID. Defaults to GCP_PROJECT_ID.")
    parser.add_argument(
        "--dataset-id",
        help="BigQuery silver dataset ID. Defaults to BIGQUERY_DATASET_SILVER.",
    )
    return parser.parse_args()


def _validate_environment(*, project_id: str | None, dataset_id: str | None) -> None:
    missing = []
    if not project_id:
        missing.append("GCP_PROJECT_ID")
    if not dataset_id:
        missing.append("BIGQUERY_DATASET_SILVER")
    if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        missing.append("GOOGLE_APPLICATION_CREDENTIALS")

    if missing:
        raise ValueError(f"Missing required environment variable(s): {', '.join(missing)}")


def _schema_for_table(table_name: str) -> list[bigquery.SchemaField]:
    return [
        bigquery.SchemaField(name=name, field_type=field_type, mode=mode)
        for name, field_type, mode in STATSBOMB_SILVER_SCHEMAS[table_name]
    ]


if __name__ == "__main__":
    main()
