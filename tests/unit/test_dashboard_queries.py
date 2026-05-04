import pytest

from football_intelligence.dashboard.app import (
    DashboardFilters,
    WarehouseConfig,
    build_pass_type_distribution_query,
    build_pressure_count_query,
    build_shot_outcome_distribution_query,
    build_top_passers_query,
    build_xg_summary_query,
    filter_conditions,
    table_ref,
    validate_warehouse_config,
)


def test_table_ref_uses_env_backed_config_without_hardcoding() -> None:
    config = WarehouseConfig(
        project_id="example-project",
        dataset_id="football_gold",
        location="europe-west2",
    )

    assert table_ref(config, "fact_shots") == "`example-project.football_gold.fact_shots`"


def test_table_ref_rejects_invalid_identifiers() -> None:
    config = WarehouseConfig(
        project_id="example-project",
        dataset_id="football_gold",
        location="europe-west2",
    )

    with pytest.raises(ValueError):
        table_ref(config, "fact_shots; drop table")


def test_validate_warehouse_config_rejects_blank_or_unsafe_values() -> None:
    config = WarehouseConfig(
        project_id="example project",
        dataset_id="football_gold",
        location="europe-west2",
    )

    with pytest.raises(ValueError, match="GCP_PROJECT_ID"):
        validate_warehouse_config(config)


def test_filter_conditions_builds_parameterized_predicate() -> None:
    filters = DashboardFilters(
        team_id=1,
        match_id=2,
        player_id=3,
        event_type_name="Pass",
    )

    predicate, parameters = filter_conditions(filters, event_type_name="Pass", alias="passes")

    assert "passes.team_id = @team_id" in predicate
    assert "passes.match_id = @match_id" in predicate
    assert "passes.player_id = @player_id" in predicate
    assert "@event_type_name" in predicate
    assert parameters == {
        "event_type_name": "Pass",
        "team_id": 1,
        "match_id": 2,
        "player_id": 3,
    }


def test_dashboard_queries_reference_gold_tables_and_filters() -> None:
    config = WarehouseConfig(
        project_id="example-project",
        dataset_id="football_gold",
        location="europe-west2",
    )
    filters = DashboardFilters(team_id=10, event_type_name="Shot")

    specs = [
        build_xg_summary_query(config, filters),
        build_pass_type_distribution_query(config, filters),
        build_shot_outcome_distribution_query(config, filters),
        build_pressure_count_query(config, filters),
        build_top_passers_query(config, filters),
    ]

    combined_sql = "\n".join(spec.sql for spec in specs)
    assert "`example-project.football_gold.fact_shots`" in combined_sql
    assert "`example-project.football_gold.fact_passes`" in combined_sql
    assert "`example-project.football_gold.fact_pressures`" in combined_sql
    assert "@team_id" in combined_sql
    assert all(spec.parameters["team_id"] == 10 for spec in specs)
    assert all(spec.parameters["event_type_name"] == "Shot" for spec in specs)


def test_xg_summary_query_group_by_uses_only_raw_dimensions() -> None:
    config = WarehouseConfig(
        project_id="example-project",
        dataset_id="football_gold",
        location="europe-west2",
    )

    spec = build_xg_summary_query(config, DashboardFilters())
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
