"""CSV writers for StatsBomb silver tables."""

from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Any

from football_intelligence.transformations.statsbomb.types import CsvRow

logger = logging.getLogger(__name__)


TABLE_COLUMNS: dict[str, list[str]] = {
    "competitions": [
        "competition_id",
        "season_id",
        "competition_name",
        "country_name",
        "competition_gender",
        "season_name",
    ],
    "matches": [
        "match_id",
        "competition_id",
        "season_id",
        "match_date",
        "kick_off",
        "home_team_id",
        "home_team_name",
        "away_team_id",
        "away_team_name",
        "home_score",
        "away_score",
        "stadium_name",
        "referee_name",
    ],
    "teams": ["team_id", "team_name", "country_name"],
    "players": [
        "player_id",
        "player_name",
        "team_id",
        "team_name",
        "jersey_number",
        "country_name",
    ],
    "events": [
        "event_id",
        "match_id",
        "index",
        "period",
        "timestamp",
        "minute",
        "second",
        "possession",
        "possession_team_id",
        "possession_team_name",
        "team_id",
        "team_name",
        "player_id",
        "player_name",
        "position_id",
        "position_name",
        "event_type_id",
        "event_type_name",
        "play_pattern_id",
        "play_pattern_name",
        "location_x",
        "location_y",
        "duration",
        "under_pressure",
        "out",
    ],
    "shots": [
        "event_id",
        "match_id",
        "team_id",
        "player_id",
        "timestamp",
        "possession",
        "location_x",
        "location_y",
        "end_location_x",
        "end_location_y",
        "end_location_z",
        "xg",
        "outcome_id",
        "outcome_name",
        "body_part_id",
        "body_part_name",
        "technique_id",
        "technique_name",
        "first_time",
        "one_on_one",
        "statsbomb_xg",
    ],
    "passes": [
        "event_id",
        "match_id",
        "team_id",
        "player_id",
        "timestamp",
        "possession",
        "location_x",
        "location_y",
        "end_location_x",
        "end_location_y",
        "recipient_player_id",
        "recipient_player_name",
        "length",
        "angle",
        "height_id",
        "height_name",
        "type_id",
        "type_name",
        "outcome_id",
        "outcome_name",
        "body_part_id",
        "body_part_name",
        "switch",
        "cross",
        "cut_back",
        "assisted_shot_id",
        "shot_assist",
        "goal_assist",
    ],
    "pressures": [
        "event_id",
        "match_id",
        "team_id",
        "player_id",
        "timestamp",
        "possession",
        "location_x",
        "location_y",
        "counterpress",
    ],
    "three_sixty_freeze_frames": [
        "event_id",
        "match_id",
        "player_id",
        "player_name",
        "teammate",
        "actor",
        "keeper",
        "location_x",
        "location_y",
        "visible_area",
    ],
}


def write_silver_tables(tables: dict[str, list[CsvRow]], output_dir: str | Path) -> dict[str, Path]:
    """Write all StatsBomb silver tables as CSV files."""

    root = Path(output_dir).expanduser()
    root.mkdir(parents=True, exist_ok=True)
    written: dict[str, Path] = {}

    for table_name, columns in TABLE_COLUMNS.items():
        path = root / f"{table_name}.csv"
        rows = tables.get(table_name, [])
        _write_csv(path, rows, columns)
        written[table_name] = path
        logger.info("Wrote StatsBomb silver table %s rows=%d", path, len(rows))

    return written


def _write_csv(path: Path, rows: list[CsvRow], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: _csv_value(row.get(column)) for column in columns})


def _csv_value(value: Any) -> Any:
    if value is None:
        return ""
    return value
