import pytest

from football_intelligence.api.main import (
    AnalyticsFilters,
    GoldWarehouseConfig,
    build_matches_query,
    build_pass_types_query,
    build_pressures_query,
    build_shot_outcomes_query,
    build_teams_query,
    build_xg_summary_query,
    fact_filter_conditions,
    table_ref,
    validate_gold_config,
)


def test_api_table_ref_uses_gold_config() -> None:
    config = GoldWarehouseConfig(
        project_id="example-project",
        dataset_id="football_gold",
        location="europe-west2",
    )

    assert table_ref(config, "fact_shots") == "`example-project.football_gold.fact_shots`"


def test_api_table_ref_rejects_invalid_table_name() -> None:
    config = GoldWarehouseConfig(
        project_id="example-project",
        dataset_id="football_gold",
        location="europe-west2",
    )

    with pytest.raises(ValueError):
        table_ref(config, "fact_shots;drop")


def test_api_validate_gold_config_rejects_invalid_project() -> None:
    config = GoldWarehouseConfig(
        project_id="example project",
        dataset_id="football_gold",
        location="europe-west2",
    )

    with pytest.raises(ValueError, match="GCP_PROJECT_ID"):
        validate_gold_config(config)


def test_api_fact_filter_conditions_are_parameterized() -> None:
    filters = AnalyticsFilters(team_id=1, match_id=2, player_id=3, limit=25)

    predicate, parameters = fact_filter_conditions(filters, alias="events")

    assert "events.team_id = @team_id" in predicate
    assert "events.match_id = @match_id" in predicate
    assert "events.player_id = @player_id" in predicate
    assert parameters == {"limit": 25, "team_id": 1, "match_id": 2, "player_id": 3}


def test_api_queries_reference_gold_tables_and_limits() -> None:
    config = GoldWarehouseConfig(
        project_id="example-project",
        dataset_id="football_gold",
        location="europe-west2",
    )
    filters = AnalyticsFilters(team_id=10, limit=50)

    specs = [
        build_teams_query(config, limit=50),
        build_matches_query(config, team_id=10, limit=50),
        build_xg_summary_query(config, filters),
        build_pass_types_query(config, filters),
        build_shot_outcomes_query(config, filters),
        build_pressures_query(config, filters),
    ]

    combined_sql = "\n".join(spec.sql for spec in specs)
    assert "`example-project.football_gold.dim_teams`" in combined_sql
    assert "`example-project.football_gold.dim_matches`" in combined_sql
    assert "`example-project.football_gold.fact_shots`" in combined_sql
    assert "`example-project.football_gold.fact_passes`" in combined_sql
    assert "`example-project.football_gold.fact_pressures`" in combined_sql
    assert "@limit" in combined_sql
    assert all(spec.parameters["limit"] == 50 for spec in specs)


def test_api_xg_summary_group_by_uses_only_raw_dimensions() -> None:
    config = GoldWarehouseConfig(
        project_id="example-project",
        dataset_id="football_gold",
        location="europe-west2",
    )

    spec = build_xg_summary_query(config, AnalyticsFilters())
    group_by_clause = spec.sql.lower().split("group by", maxsplit=1)[1].split(
        "order by",
        maxsplit=1,
    )[0]

    assert "count(" not in group_by_clause
    assert "sum(" not in group_by_clause
    assert "avg(" not in group_by_clause
    assert " shots" not in group_by_clause
    assert "total_xg" not in group_by_clause
    assert "average_xg" not in group_by_clause
    assert "match_label" not in group_by_clause
    assert "fs.match_id" in group_by_clause
    assert "matches.home_team_name" in group_by_clause
    assert "matches.away_team_name" in group_by_clause
    assert "matches.match_date" in group_by_clause
