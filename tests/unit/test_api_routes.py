import pytest
from fastapi import HTTPException

from football_intelligence.api.main import (
    AnalyticsFilters,
    GoldWarehouseConfig,
    health,
    list_teams,
    pass_types,
)
from football_intelligence.io.bigquery import BigQueryRepositoryError


class StubRepository:
    def __init__(self, rows: list[dict[str, object]] | None = None, *, fail: bool = False) -> None:
        self.rows = rows or []
        self.fail = fail
        self.calls: list[tuple[str, dict[str, object] | None]] = []

    def query(
        self,
        sql: str,
        parameters: dict[str, object] | None = None,
    ) -> list[dict[str, object]]:
        self.calls.append((sql, parameters))
        if self.fail:
            raise BigQueryRepositoryError("missing table")
        return self.rows


def test_health_route_payload() -> None:
    response = health()

    assert response["status"] == "ok"


def test_teams_route_returns_bigquery_rows() -> None:
    repository = StubRepository(rows=[{"team_id": 1, "team_name": "Arsenal"}])

    response = list_teams(repository=repository, config=_test_config(), limit=5)

    assert response == [{"team_id": 1, "team_name": "Arsenal"}]
    assert repository.calls[0][1] == {"limit": 5}


def test_analytics_route_passes_optional_filters_to_query() -> None:
    repository = StubRepository(rows=[{"type_name": "Regular pass", "passes": 12}])

    response = pass_types(
        filters=AnalyticsFilters(team_id=1, match_id=2, player_id=3, limit=10),
        repository=repository,
        config=_test_config(),
    )

    assert response == [{"type_name": "Regular pass", "passes": 12}]
    assert repository.calls[0][1] == {
        "limit": 10,
        "team_id": 1,
        "match_id": 2,
        "player_id": 3,
    }


def test_route_returns_503_for_bigquery_failure() -> None:
    repository = StubRepository(fail=True)

    with pytest.raises(HTTPException) as exc_info:
        list_teams(repository=repository, config=_test_config(), limit=100)

    assert exc_info.value.status_code == 503
    assert "BigQuery query failed" in exc_info.value.detail


def _test_config() -> GoldWarehouseConfig:
    return GoldWarehouseConfig(
        project_id="example-project",
        dataset_id="football_gold",
        location="europe-west2",
    )
