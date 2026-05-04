from unittest.mock import Mock

from google.cloud import bigquery

from football_intelligence.io.bigquery import BigQueryRepository


def test_bigquery_repository_runs_parameterized_query() -> None:
    row = Mock()
    row.items.return_value = [("team_id", 1), ("team_name", "Arsenal")]
    query_job = Mock()
    query_job.result.return_value = [row]
    client = Mock()
    client.query.return_value = query_job
    repository = BigQueryRepository(
        project_id="example-project",
        location="europe-west2",
        client=client,
    )

    rows = repository.query(
        "select * from teams where team_id = @team_id",
        parameters={"team_id": 1},
    )

    assert rows == [{"team_id": 1, "team_name": "Arsenal"}]
    query_call = client.query.call_args
    assert query_call.args[0] == "select * from teams where team_id = @team_id"
    job_config = query_call.kwargs["job_config"]
    assert isinstance(job_config, bigquery.QueryJobConfig)
    assert job_config.query_parameters[0].name == "team_id"
    assert job_config.query_parameters[0].type_ == "INT64"
    assert job_config.query_parameters[0].value == 1
