"""FastAPI application exposing BigQuery gold warehouse data."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException, Query

from football_intelligence import __version__
from football_intelligence.config.settings import get_settings
from football_intelligence.io.bigquery import BigQueryRepository, BigQueryRepositoryError

IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")
DEFAULT_LIMIT = 100
MAX_LIMIT = 1000

app = FastAPI(
    title="Football Intelligence Platform API",
    version=__version__,
)


@dataclass(frozen=True)
class GoldWarehouseConfig:
    """BigQuery gold warehouse location."""

    project_id: str
    dataset_id: str
    location: str


@dataclass(frozen=True)
class AnalyticsFilters:
    """Optional filters for analytics endpoints."""

    team_id: int | None = None
    match_id: int | None = None
    player_id: int | None = None
    limit: int = DEFAULT_LIMIT


@dataclass(frozen=True)
class QuerySpec:
    """SQL and named query parameters."""

    sql: str
    parameters: dict[str, Any]


LimitParam = Annotated[int, Query(ge=1, le=MAX_LIMIT)]


def get_gold_config() -> GoldWarehouseConfig:
    """Build BigQuery gold warehouse config from environment-backed settings."""

    settings = get_settings()
    missing = []
    if not settings.gcp_project_id:
        missing.append("GCP_PROJECT_ID")
    if not settings.bigquery_dataset_gold:
        missing.append("BIGQUERY_DATASET_GOLD")
    if missing:
        raise HTTPException(
            status_code=500,
            detail=f"Missing required environment variable(s): {', '.join(missing)}",
        )

    config = GoldWarehouseConfig(
        project_id=settings.gcp_project_id,
        dataset_id=settings.bigquery_dataset_gold,
        location=settings.gcp_region,
    )
    try:
        validate_gold_config(config)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return config


ConfigDep = Annotated[GoldWarehouseConfig, Depends(get_gold_config)]


def get_bigquery_repository(config: ConfigDep) -> BigQueryRepository:
    """Create a BigQuery repository using ADC/OAuth."""

    try:
        return BigQueryRepository(project_id=config.project_id, location=config.location)
    except Exception as exc:  # noqa: BLE001 - credential construction can raise several auth errors.
        raise HTTPException(
            status_code=503,
            detail=(
                "Unable to initialize BigQuery client. Check Google Application Default "
                "Credentials or OAuth configuration."
            ),
        ) from exc


RepositoryDep = Annotated[BigQueryRepository, Depends(get_bigquery_repository)]


def get_analytics_filters(
    team_id: int | None = None,
    match_id: int | None = None,
    player_id: int | None = None,
    limit: LimitParam = DEFAULT_LIMIT,
) -> AnalyticsFilters:
    """Collect common analytics query parameters."""

    return AnalyticsFilters(
        team_id=team_id,
        match_id=match_id,
        player_id=player_id,
        limit=limit,
    )


AnalyticsFiltersDep = Annotated[AnalyticsFilters, Depends(get_analytics_filters)]


@app.get("/health")
def health() -> dict[str, str]:
    """Return service health status."""

    return {"status": "ok", "version": __version__}


@app.get("/teams")
def list_teams(
    repository: RepositoryDep,
    config: ConfigDep,
    limit: LimitParam = DEFAULT_LIMIT,
) -> list[dict[str, Any]]:
    """Return teams from the gold team dimension."""

    return run_query(repository, build_teams_query(config, limit=limit))


@app.get("/players")
def list_players(
    repository: RepositoryDep,
    config: ConfigDep,
    team_id: int | None = None,
    limit: LimitParam = DEFAULT_LIMIT,
) -> list[dict[str, Any]]:
    """Return players from the gold player dimension."""

    return run_query(repository, build_players_query(config, team_id=team_id, limit=limit))


@app.get("/matches")
def list_matches(
    repository: RepositoryDep,
    config: ConfigDep,
    team_id: int | None = None,
    limit: LimitParam = DEFAULT_LIMIT,
) -> list[dict[str, Any]]:
    """Return matches from the gold match dimension."""

    return run_query(repository, build_matches_query(config, team_id=team_id, limit=limit))


@app.get("/analytics/xg-summary")
def xg_summary(
    filters: AnalyticsFiltersDep,
    repository: RepositoryDep,
    config: ConfigDep,
) -> list[dict[str, Any]]:
    """Return xG summary by match from fact_shots."""

    return run_query(repository, build_xg_summary_query(config, filters))


@app.get("/analytics/pass-types")
def pass_types(
    filters: AnalyticsFiltersDep,
    repository: RepositoryDep,
    config: ConfigDep,
) -> list[dict[str, Any]]:
    """Return pass type distribution from fact_passes."""

    return run_query(repository, build_pass_types_query(config, filters))


@app.get("/analytics/shot-outcomes")
def shot_outcomes(
    filters: AnalyticsFiltersDep,
    repository: RepositoryDep,
    config: ConfigDep,
) -> list[dict[str, Any]]:
    """Return shot outcome distribution from fact_shots."""

    return run_query(repository, build_shot_outcomes_query(config, filters))


@app.get("/analytics/pressures")
def pressures(
    filters: AnalyticsFiltersDep,
    repository: RepositoryDep,
    config: ConfigDep,
) -> list[dict[str, Any]]:
    """Return pressure counts by team and player from fact_pressures."""

    return run_query(repository, build_pressures_query(config, filters))


def run_query(repository: BigQueryRepository, spec: QuerySpec) -> list[dict[str, Any]]:
    """Execute a query and convert repository failures into API errors."""

    try:
        return repository.query(spec.sql, parameters=spec.parameters)
    except BigQueryRepositoryError as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "BigQuery query failed. Check credentials, table availability, and warehouse "
                "permissions."
            ),
        ) from exc


def build_teams_query(config: GoldWarehouseConfig, *, limit: int) -> QuerySpec:
    return QuerySpec(
        sql=f"""
select
  team_id,
  team_name,
  country_name
from {table_ref(config, "dim_teams")}
order by team_name
limit @limit
""",
        parameters={"limit": limit},
    )


def build_players_query(
    config: GoldWarehouseConfig,
    *,
    team_id: int | None,
    limit: int,
) -> QuerySpec:
    conditions, parameters = optional_filter_conditions(
        {"team_id": ("team_id", team_id)},
        limit=limit,
    )
    return QuerySpec(
        sql=f"""
select
  player_id,
  player_name,
  team_id,
  team_name,
  jersey_number,
  country_name
from {table_ref(config, "dim_players")}
where {conditions}
order by player_name
limit @limit
""",
        parameters=parameters,
    )


def build_matches_query(
    config: GoldWarehouseConfig,
    *,
    team_id: int | None,
    limit: int,
) -> QuerySpec:
    conditions, parameters = optional_filter_conditions(
        {
            "team_id": ("home_team_id = @team_id or away_team_id", team_id),
        },
        limit=limit,
    )
    return QuerySpec(
        sql=f"""
select
  match_id,
  competition_id,
  season_id,
  match_date,
  home_team_id,
  home_team_name,
  away_team_id,
  away_team_name,
  home_score,
  away_score
from {table_ref(config, "dim_matches")}
where {conditions}
order by match_date desc, match_id
limit @limit
""",
        parameters=parameters,
    )


def build_xg_summary_query(config: GoldWarehouseConfig, filters: AnalyticsFilters) -> QuerySpec:
    conditions, parameters = fact_filter_conditions(filters, alias="fs")
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
order by matches.match_date desc, fs.match_id
limit @limit
""",
        parameters=parameters,
    )


def build_pass_types_query(config: GoldWarehouseConfig, filters: AnalyticsFilters) -> QuerySpec:
    conditions, parameters = fact_filter_conditions(filters, alias="passes")
    return QuerySpec(
        sql=f"""
select
  coalesce(type_name, 'Regular pass') as type_name,
  count(*) as passes
from {table_ref(config, "fact_passes")} as passes
where {conditions}
group by type_name
order by passes desc, type_name
limit @limit
""",
        parameters=parameters,
    )


def build_shot_outcomes_query(config: GoldWarehouseConfig, filters: AnalyticsFilters) -> QuerySpec:
    conditions, parameters = fact_filter_conditions(filters, alias="shots")
    return QuerySpec(
        sql=f"""
select
  coalesce(outcome_name, 'Unknown outcome') as outcome_name,
  count(*) as shots
from {table_ref(config, "fact_shots")} as shots
where {conditions}
group by outcome_name
order by shots desc, outcome_name
limit @limit
""",
        parameters=parameters,
    )


def build_pressures_query(config: GoldWarehouseConfig, filters: AnalyticsFilters) -> QuerySpec:
    conditions, parameters = fact_filter_conditions(filters, alias="pressures")
    return QuerySpec(
        sql=f"""
select
  pressures.team_id,
  teams.team_name,
  pressures.player_id,
  players.player_name,
  count(*) as pressures
from {table_ref(config, "fact_pressures")} as pressures
left join {table_ref(config, "dim_teams")} as teams
  on pressures.team_id = teams.team_id
left join {table_ref(config, "dim_players")} as players
  on pressures.player_id = players.player_id
where {conditions}
group by pressures.team_id, teams.team_name, pressures.player_id, players.player_name
order by pressures desc, team_name, player_name
limit @limit
""",
        parameters=parameters,
    )


def optional_filter_conditions(
    filters: dict[str, tuple[str, int | None]],
    *,
    limit: int,
) -> tuple[str, dict[str, Any]]:
    """Build simple optional dimension filters."""

    conditions = ["1 = 1"]
    parameters: dict[str, Any] = {"limit": limit}
    for parameter_name, (column_expression, value) in filters.items():
        if value is None:
            continue
        if " or " in column_expression:
            conditions.append(f"({column_expression} = @{parameter_name})")
        else:
            conditions.append(f"{column_expression} = @{parameter_name}")
        parameters[parameter_name] = value
    return " and ".join(conditions), parameters


def fact_filter_conditions(
    filters: AnalyticsFilters,
    *,
    alias: str,
) -> tuple[str, dict[str, Any]]:
    """Build common optional fact table filters."""

    conditions = ["1 = 1"]
    parameters: dict[str, Any] = {"limit": filters.limit}
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


def table_ref(config: GoldWarehouseConfig, table_name: str) -> str:
    """Return a validated, quoted BigQuery table reference."""

    validate_gold_config(config)
    if not IDENTIFIER_PATTERN.fullmatch(table_name):
        raise ValueError(f"Invalid BigQuery table name: {table_name}")
    return f"`{config.project_id}.{config.dataset_id}.{table_name}`"


def validate_gold_config(config: GoldWarehouseConfig) -> None:
    """Validate BigQuery project, dataset, and location identifiers."""

    for label, value in {
        "GCP_PROJECT_ID": config.project_id,
        "BIGQUERY_DATASET_GOLD": config.dataset_id,
        "GCP_REGION": config.location,
    }.items():
        if not IDENTIFIER_PATTERN.fullmatch(value):
            raise ValueError(f"Invalid {label}: {value}")
