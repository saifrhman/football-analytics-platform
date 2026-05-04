"""Streamlit dashboard backed by BigQuery gold warehouse tables."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import pandas as pd
import streamlit as st

from football_intelligence.config.settings import get_settings
from football_intelligence.io.bigquery import BigQueryRepository, BigQueryRepositoryError

IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


@dataclass(frozen=True)
class WarehouseConfig:
    """BigQuery warehouse location for gold dashboard models."""

    project_id: str
    dataset_id: str
    location: str


@dataclass(frozen=True)
class DashboardFilters:
    """Selected dashboard filters."""

    team_id: int | None = None
    match_id: int | None = None
    player_id: int | None = None
    event_type_name: str | None = None


@dataclass(frozen=True)
class QuerySpec:
    """SQL and named parameters for one dashboard query."""

    sql: str
    parameters: dict[str, Any]


def main() -> None:
    """Render the BigQuery-backed dashboard."""

    st.set_page_config(page_title="Football Intelligence", layout="wide")
    st.title("Football Intelligence")
    st.caption("StatsBomb sample analytics from BigQuery gold warehouse tables.")

    try:
        config = warehouse_config_from_env()
    except ValueError as exc:
        st.error(str(exc))
        st.stop()

    repository = get_repository(config.project_id, config.location)

    try:
        filters = render_filters(repository, config)
        render_dashboard(repository, config, filters)
    except BigQueryRepositoryError as exc:
        st.error(
            "Unable to query BigQuery. Check Google Application Default Credentials, "
            "project access, and whether dbt gold tables have been built."
        )
        st.exception(exc)
    except FileNotFoundError as exc:
        st.error(str(exc))


def warehouse_config_from_env() -> WarehouseConfig:
    """Load dashboard warehouse configuration from environment-backed settings."""

    settings = get_settings()
    missing = []
    if not settings.gcp_project_id:
        missing.append("GCP_PROJECT_ID")
    if not settings.bigquery_dataset_gold:
        missing.append("BIGQUERY_DATASET_GOLD")
    if missing:
        raise ValueError(f"Missing required environment variable(s): {', '.join(missing)}")

    config = WarehouseConfig(
        project_id=settings.gcp_project_id,
        dataset_id=settings.bigquery_dataset_gold,
        location=settings.gcp_region,
    )
    validate_warehouse_config(config)
    return config


@st.cache_resource
def get_repository(project_id: str, location: str) -> BigQueryRepository:
    """Create a cached BigQuery repository for Streamlit reruns."""

    return BigQueryRepository(project_id=project_id, location=location)


def render_filters(repository: BigQueryRepository, config: WarehouseConfig) -> DashboardFilters:
    """Render sidebar filters from BigQuery dimension tables."""

    st.sidebar.header("Filters")
    teams = repository.query(build_team_options_query(config).sql)
    matches = repository.query(build_match_options_query(config).sql)
    players = repository.query(build_player_options_query(config).sql)
    event_types = repository.query(build_event_type_options_query(config).sql)

    team = st.sidebar.selectbox(
        "Team",
        options=[None, *teams],
        format_func=lambda row: "All teams" if row is None else row["team_name"],
    )
    match = st.sidebar.selectbox(
        "Match",
        options=[None, *matches],
        format_func=lambda row: "All matches" if row is None else row["match_label"],
    )
    player = st.sidebar.selectbox(
        "Player",
        options=[None, *players],
        format_func=lambda row: "All players" if row is None else row["player_name"],
    )
    event_type = st.sidebar.selectbox(
        "Event type",
        options=[None, *event_types],
        format_func=lambda row: "All event types" if row is None else row["event_type_name"],
    )

    return DashboardFilters(
        team_id=None if team is None else int(team["team_id"]),
        match_id=None if match is None else int(match["match_id"]),
        player_id=None if player is None else int(player["player_id"]),
        event_type_name=None if event_type is None else str(event_type["event_type_name"]),
    )


def render_dashboard(
    repository: BigQueryRepository,
    config: WarehouseConfig,
    filters: DashboardFilters,
) -> None:
    """Render dashboard sections and charts."""

    xg = dataframe(run_query(repository, build_xg_summary_query(config, filters)))
    pass_types = dataframe(
        run_query(repository, build_pass_type_distribution_query(config, filters))
    )
    shot_outcomes = dataframe(
        run_query(repository, build_shot_outcome_distribution_query(config, filters))
    )
    pressures = dataframe(run_query(repository, build_pressure_count_query(config, filters)))
    top_passers = dataframe(run_query(repository, build_top_passers_query(config, filters)))

    total_xg = float(xg["total_xg"].sum()) if "total_xg" in xg else 0.0
    total_shots = int(xg["shots"].sum()) if "shots" in xg else 0
    total_passes = int(pass_types["passes"].sum()) if "passes" in pass_types else 0
    total_pressures = int(pressures["pressures"].sum()) if "pressures" in pressures else 0

    metric_cols = st.columns(4)
    metric_cols[0].metric("Total xG", f"{total_xg:.2f}")
    metric_cols[1].metric("Shots", f"{total_shots:,}")
    metric_cols[2].metric("Passes", f"{total_passes:,}")
    metric_cols[3].metric("Pressures", f"{total_pressures:,}")

    left, right = st.columns(2)
    with left:
        render_line_chart(
            "xG Trend by Match",
            "Total expected goals from `fact_shots`, grouped by match date.",
            xg,
            index="match_label",
            value="total_xg",
        )
        render_bar_chart(
            "Shot Outcome Distribution",
            "Shot outcomes from `fact_shots`, useful for reviewing finishing profile.",
            shot_outcomes,
            index="outcome_name",
            value="shots",
        )
        render_bar_chart(
            "Top Passers",
            "Players with the highest pass event volume in `fact_passes`.",
            top_passers,
            index="player_name",
            value="passes",
        )

    with right:
        render_bar_chart(
            "Pass Type Distribution",
            "Pass event types from `fact_passes`, including regular and set-piece variants.",
            pass_types,
            index="type_name",
            value="passes",
        )
        render_bar_chart(
            "Pressure Count by Team and Player",
            "Pressure events from `fact_pressures`, grouped by team and player.",
            pressures,
            index="pressure_label",
            value="pressures",
        )


def render_line_chart(
    title: str,
    explanation: str,
    data: pd.DataFrame,
    *,
    index: str,
    value: str,
) -> None:
    """Render a titled line chart with an empty state."""

    st.subheader(title)
    st.caption(explanation)
    if data.empty:
        st.info("No rows match the current filters.")
        return
    st.line_chart(data.set_index(index)[value])


def render_bar_chart(
    title: str,
    explanation: str,
    data: pd.DataFrame,
    *,
    index: str,
    value: str,
) -> None:
    """Render a titled bar chart with an empty state."""

    st.subheader(title)
    st.caption(explanation)
    if data.empty:
        st.info("No rows match the current filters.")
        return
    st.bar_chart(data.set_index(index)[value])


def dataframe(rows: list[dict[str, Any]]) -> pd.DataFrame:
    """Convert BigQuery rows into a pandas DataFrame."""

    return pd.DataFrame(rows)


def run_query(repository: BigQueryRepository, spec: QuerySpec) -> list[dict[str, Any]]:
    """Run a dashboard query specification."""

    return repository.query(spec.sql, parameters=spec.parameters)


def build_team_options_query(config: WarehouseConfig) -> QuerySpec:
    return QuerySpec(
        sql=f"""
select
  team_id,
  team_name
from {table_ref(config, "dim_teams")}
order by team_name
""",
        parameters={},
    )


def build_match_options_query(config: WarehouseConfig) -> QuerySpec:
    return QuerySpec(
        sql=f"""
select
  match_id,
  concat(home_team_name, ' vs ', away_team_name, ' (', cast(match_date as string), ')')
    as match_label
from {table_ref(config, "dim_matches")}
order by match_date desc, match_id
""",
        parameters={},
    )


def build_player_options_query(config: WarehouseConfig) -> QuerySpec:
    return QuerySpec(
        sql=f"""
select
  player_id,
  player_name
from {table_ref(config, "dim_players")}
where player_name is not null
order by player_name
""",
        parameters={},
    )


def build_event_type_options_query(config: WarehouseConfig) -> QuerySpec:
    return QuerySpec(
        sql=f"""
select distinct
  event_type_name
from {table_ref(config, "fact_events")}
where event_type_name is not null
order by event_type_name
""",
        parameters={},
    )


def build_xg_summary_query(config: WarehouseConfig, filters: DashboardFilters) -> QuerySpec:
    conditions, parameters = filter_conditions(filters, event_type_name="Shot", alias="fs")
    return QuerySpec(
        sql=f"""
select
  fs.match_id,
  concat(
    matches.home_team_name,
    ' vs ',
    matches.away_team_name,
    ' (',
    cast(matches.match_date as string),
    ')'
  ) as match_label,
  matches.match_date,
  count(*) as shots,
  sum(coalesce(fs.statsbomb_xg, fs.xg, 0)) as total_xg,
  avg(coalesce(fs.statsbomb_xg, fs.xg)) as average_xg
from {table_ref(config, "fact_shots")} as fs
left join {table_ref(config, "dim_matches")} as matches
  on fs.match_id = matches.match_id
where {conditions}
group by fs.match_id, matches.home_team_name, matches.away_team_name, matches.match_date
order by matches.match_date, fs.match_id
""",
        parameters=parameters,
    )


def build_pass_type_distribution_query(
    config: WarehouseConfig,
    filters: DashboardFilters,
) -> QuerySpec:
    conditions, parameters = filter_conditions(filters, event_type_name="Pass", alias="passes")
    return QuerySpec(
        sql=f"""
select
  coalesce(type_name, 'Regular pass') as type_name,
  count(*) as passes
from {table_ref(config, "fact_passes")} as passes
where {conditions}
group by type_name
order by passes desc, type_name
""",
        parameters=parameters,
    )


def build_shot_outcome_distribution_query(
    config: WarehouseConfig,
    filters: DashboardFilters,
) -> QuerySpec:
    conditions, parameters = filter_conditions(filters, event_type_name="Shot", alias="shots")
    return QuerySpec(
        sql=f"""
select
  coalesce(outcome_name, 'Unknown outcome') as outcome_name,
  count(*) as shots
from {table_ref(config, "fact_shots")} as shots
where {conditions}
group by outcome_name
order by shots desc, outcome_name
""",
        parameters=parameters,
    )


def build_pressure_count_query(config: WarehouseConfig, filters: DashboardFilters) -> QuerySpec:
    conditions, parameters = filter_conditions(
        filters,
        event_type_name="Pressure",
        alias="pressures",
    )
    return QuerySpec(
        sql=f"""
select
  concat(
    coalesce(teams.team_name, 'Unknown team'),
    ' / ',
    coalesce(players.player_name, 'Unknown player')
  ) as pressure_label,
  count(*) as pressures
from {table_ref(config, "fact_pressures")} as pressures
left join {table_ref(config, "dim_teams")} as teams
  on pressures.team_id = teams.team_id
left join {table_ref(config, "dim_players")} as players
  on pressures.player_id = players.player_id
where {conditions}
group by pressure_label
order by pressures desc, pressure_label
limit 20
""",
        parameters=parameters,
    )


def build_top_passers_query(config: WarehouseConfig, filters: DashboardFilters) -> QuerySpec:
    conditions, parameters = filter_conditions(filters, event_type_name="Pass", alias="passes")
    return QuerySpec(
        sql=f"""
select
  coalesce(players.player_name, 'Unknown player') as player_name,
  count(*) as passes
from {table_ref(config, "fact_passes")} as passes
left join {table_ref(config, "dim_players")} as players
  on passes.player_id = players.player_id
where {conditions}
group by player_name
order by passes desc, player_name
limit 20
""",
        parameters=parameters,
    )


def filter_conditions(
    filters: DashboardFilters,
    *,
    event_type_name: str,
    alias: str,
) -> tuple[str, dict[str, Any]]:
    """Build a reusable filter predicate for fact queries."""

    conditions = [f"(@event_type_name is null or @event_type_name = '{event_type_name}')"]
    parameters: dict[str, Any] = {"event_type_name": filters.event_type_name}
    if filters.team_id is not None:
        conditions.append(f"{alias}.team_id = @team_id")
        parameters["team_id"] = filters.team_id
    if filters.match_id is not None:
        conditions.append(f"{alias}.match_id = @match_id")
        parameters["match_id"] = filters.match_id
    if filters.player_id is not None:
        conditions.append(f"{alias}.player_id = @player_id")
        parameters["player_id"] = filters.player_id

    return " and ".join(conditions), parameters


def table_ref(config: WarehouseConfig, table_name: str) -> str:
    """Return a validated, quoted BigQuery table reference."""

    validate_warehouse_config(config)
    if not IDENTIFIER_PATTERN.fullmatch(table_name):
        raise ValueError(f"Invalid BigQuery table name: {table_name}")
    return f"`{config.project_id}.{config.dataset_id}.{table_name}`"


def validate_warehouse_config(config: WarehouseConfig) -> None:
    """Validate BigQuery project, dataset, and location identifiers."""

    for label, value in {
        "GCP_PROJECT_ID": config.project_id,
        "BIGQUERY_DATASET_GOLD": config.dataset_id,
        "GCP_REGION": config.location,
    }.items():
        if not IDENTIFIER_PATTERN.fullmatch(value):
            raise ValueError(f"Invalid {label}: {value}")


if __name__ == "__main__":
    main()
