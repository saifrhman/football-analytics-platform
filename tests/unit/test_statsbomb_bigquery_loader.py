from pathlib import Path
from unittest.mock import Mock

import pytest
from google.cloud import bigquery

from football_intelligence.loaders.bigquery.statsbomb_silver import (
    STATSBOMB_SILVER_TABLES,
    StatsBombSilverBigQueryLoader,
    _schema_for_table,
    _validate_environment,
)


def test_statsbomb_bigquery_loader_loads_all_tables_with_write_truncate(
    tmp_path: Path,
) -> None:
    silver_dir = tmp_path / "silver" / "statsbomb"
    for table_name in STATSBOMB_SILVER_TABLES:
        _write_csv(silver_dir / f"{table_name}.csv")

    client = Mock()
    load_job = Mock()
    client.load_table_from_file.return_value = load_job
    client.get_table.return_value = Mock(num_rows=3)
    loader = StatsBombSilverBigQueryLoader(
        project_id="test-project",
        dataset_id="football_silver",
        silver_dir=silver_dir,
        client=client,
    )

    results = loader.load_all()

    assert [result.table_name for result in results] == list(STATSBOMB_SILVER_TABLES)
    assert client.load_table_from_file.call_count == len(STATSBOMB_SILVER_TABLES)
    first_call = client.load_table_from_file.call_args_list[0]
    assert first_call.args[1] == "test-project.football_silver.competitions"
    job_config = first_call.kwargs["job_config"]
    assert job_config.source_format == bigquery.SourceFormat.CSV
    assert job_config.skip_leading_rows == 1
    assert job_config.write_disposition == bigquery.WriteDisposition.WRITE_TRUNCATE
    assert job_config.autodetect is False
    assert [field.name for field in job_config.schema] == [
        field.name for field in _schema_for_table("competitions")
    ]
    assert load_job.result.call_count == len(STATSBOMB_SILVER_TABLES)


def test_statsbomb_bigquery_loader_requires_existing_csv(tmp_path: Path) -> None:
    loader = StatsBombSilverBigQueryLoader(
        project_id="test-project",
        dataset_id="football_silver",
        silver_dir=tmp_path,
        client=Mock(),
    )

    with pytest.raises(FileNotFoundError, match="competitions.csv"):
        loader.load_table("competitions")


def test_statsbomb_bigquery_loader_rejects_unknown_table(tmp_path: Path) -> None:
    loader = StatsBombSilverBigQueryLoader(
        project_id="test-project",
        dataset_id="football_silver",
        silver_dir=tmp_path,
        client=Mock(),
    )

    with pytest.raises(ValueError, match="Unsupported StatsBomb silver table"):
        loader.load_table("unknown")


def test_statsbomb_bigquery_loader_validates_required_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)

    with pytest.raises(ValueError) as exc_info:
        _validate_environment(project_id=None, dataset_id=None)

    assert "GCP_PROJECT_ID" in str(exc_info.value)
    assert "BIGQUERY_DATASET_SILVER" in str(exc_info.value)
    assert "GOOGLE_APPLICATION_CREDENTIALS" in str(exc_info.value)


def test_statsbomb_bigquery_loader_accepts_required_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "/tmp/credentials.json")

    _validate_environment(project_id="test-project", dataset_id="football_silver")


def _write_csv(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("id\n1\n", encoding="utf-8")
