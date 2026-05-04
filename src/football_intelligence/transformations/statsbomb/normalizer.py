"""Normalize raw StatsBomb Open Data JSON into silver-ready row sets."""

from __future__ import annotations

import logging
from typing import Any

from football_intelligence.transformations.statsbomb.reader import StatsBombBronzeData
from football_intelligence.transformations.statsbomb.types import CsvRow, JsonObject
from football_intelligence.transformations.statsbomb.utils import (
    as_float,
    as_int,
    as_text,
    json_text,
    location_x,
    location_y,
    nested_get,
)
from football_intelligence.transformations.statsbomb.writer import TABLE_COLUMNS

logger = logging.getLogger(__name__)


def normalize_statsbomb_bronze(data: StatsBombBronzeData) -> dict[str, list[CsvRow]]:
    """Normalize raw StatsBomb bronze records into silver table rows."""

    tables = {table_name: [] for table_name in TABLE_COLUMNS}
    teams: dict[int, CsvRow] = {}
    players: dict[int, CsvRow] = {}

    tables["competitions"] = [_competition_row(record) for record in data.competitions]

    for match in data.matches:
        tables["matches"].append(_match_row(match))
        _upsert_team(
            teams,
            nested_get(match, "home_team", "home_team_id"),
            nested_get(match, "home_team", "home_team_name"),
            nested_get(match, "home_team", "country", "name"),
        )
        _upsert_team(
            teams,
            nested_get(match, "away_team", "away_team_id"),
            nested_get(match, "away_team", "away_team_name"),
            nested_get(match, "away_team", "country", "name"),
        )

    for lineup_group in data.lineups:
        for lineup in lineup_group.records:
            team_id = _upsert_team(
                teams,
                lineup.get("team_id"),
                lineup.get("team_name"),
                nested_get(lineup, "country", "name"),
            )
            for player in _list_of_objects(lineup.get("lineup")):
                player_id = _upsert_player(
                    players,
                    player.get("player_id"),
                    player.get("player_name"),
                    team_id,
                    lineup.get("team_name"),
                    player.get("jersey_number"),
                    nested_get(player, "country", "name"),
                )
                logger.debug(
                    "Processed lineup player_id=%s match_id=%s",
                    player_id,
                    lineup_group.match_id,
                )

    for event_group in data.events:
        for event in event_group.records:
            event_row = _event_row(event, event_group.match_id)
            tables["events"].append(event_row)

            team_id = _upsert_team(
                teams,
                nested_get(event, "team", "id"),
                nested_get(event, "team", "name"),
                None,
            )
            _upsert_player(
                players,
                nested_get(event, "player", "id"),
                nested_get(event, "player", "name"),
                team_id,
                nested_get(event, "team", "name"),
                None,
                None,
            )

            event_type_name = as_text(nested_get(event, "type", "name"))
            if event_type_name == "Shot":
                tables["shots"].append(_shot_row(event, event_group.match_id))
            elif event_type_name == "Pass":
                tables["passes"].append(_pass_row(event, event_group.match_id))
                _upsert_player(
                    players,
                    nested_get(event, "pass", "recipient", "id"),
                    nested_get(event, "pass", "recipient", "name"),
                    None,
                    None,
                    None,
                    None,
                )
            elif event_type_name == "Pressure":
                tables["pressures"].append(_pressure_row(event, event_group.match_id))

    for frame_group in data.three_sixty:
        for frame in frame_group.records:
            tables["three_sixty_freeze_frames"].extend(
                _three_sixty_rows(frame, frame_group.match_id)
            )

    tables["teams"] = sorted(teams.values(), key=lambda row: row["team_id"])
    tables["players"] = sorted(players.values(), key=lambda row: row["player_id"])

    for table_name, rows in tables.items():
        logger.info("Normalized StatsBomb silver table %s rows=%d", table_name, len(rows))

    return tables


def _competition_row(record: JsonObject) -> CsvRow:
    return {
        "competition_id": as_int(record.get("competition_id")),
        "season_id": as_int(record.get("season_id")),
        "competition_name": as_text(record.get("competition_name")),
        "country_name": as_text(record.get("country_name")),
        "competition_gender": as_text(record.get("competition_gender")),
        "season_name": as_text(record.get("season_name")),
    }


def _match_row(record: JsonObject) -> CsvRow:
    return {
        "match_id": as_int(record.get("match_id")),
        "competition_id": as_int(record.get("competition_id")),
        "season_id": as_int(record.get("season_id")),
        "match_date": as_text(record.get("match_date")),
        "kick_off": as_text(record.get("kick_off")),
        "home_team_id": as_int(nested_get(record, "home_team", "home_team_id")),
        "home_team_name": as_text(nested_get(record, "home_team", "home_team_name")),
        "away_team_id": as_int(nested_get(record, "away_team", "away_team_id")),
        "away_team_name": as_text(nested_get(record, "away_team", "away_team_name")),
        "home_score": as_int(record.get("home_score")),
        "away_score": as_int(record.get("away_score")),
        "stadium_name": as_text(nested_get(record, "stadium", "name")),
        "referee_name": as_text(nested_get(record, "referee", "name")),
    }


def _event_row(record: JsonObject, match_id: int) -> CsvRow:
    location = record.get("location")
    return {
        "event_id": as_text(record.get("id")),
        "match_id": as_int(record.get("match_id")) or match_id,
        "index": as_int(record.get("index")),
        "period": as_int(record.get("period")),
        "timestamp": as_text(record.get("timestamp")),
        "minute": as_int(record.get("minute")),
        "second": as_int(record.get("second")),
        "possession": as_int(record.get("possession")),
        "possession_team_id": as_int(nested_get(record, "possession_team", "id")),
        "possession_team_name": as_text(nested_get(record, "possession_team", "name")),
        "team_id": as_int(nested_get(record, "team", "id")),
        "team_name": as_text(nested_get(record, "team", "name")),
        "player_id": as_int(nested_get(record, "player", "id")),
        "player_name": as_text(nested_get(record, "player", "name")),
        "position_id": as_int(nested_get(record, "position", "id")),
        "position_name": as_text(nested_get(record, "position", "name")),
        "event_type_id": as_int(nested_get(record, "type", "id")),
        "event_type_name": as_text(nested_get(record, "type", "name")),
        "play_pattern_id": as_int(nested_get(record, "play_pattern", "id")),
        "play_pattern_name": as_text(nested_get(record, "play_pattern", "name")),
        "location_x": location_x(location),
        "location_y": location_y(location),
        "duration": as_float(record.get("duration")),
        "under_pressure": record.get("under_pressure"),
        "out": record.get("out"),
    }


def _shot_row(record: JsonObject, match_id: int) -> CsvRow:
    shot = _object(record.get("shot"))
    end_location = shot.get("end_location")
    base = _event_row(record, match_id)
    return {
        "event_id": base["event_id"],
        "match_id": base["match_id"],
        "team_id": base["team_id"],
        "player_id": base["player_id"],
        "timestamp": base["timestamp"],
        "possession": base["possession"],
        "location_x": base["location_x"],
        "location_y": base["location_y"],
        "end_location_x": location_x(end_location),
        "end_location_y": location_y(end_location),
        "end_location_z": _location_z(end_location),
        "xg": as_float(shot.get("statsbomb_xg")),
        "outcome_id": as_int(nested_get(shot, "outcome", "id")),
        "outcome_name": as_text(nested_get(shot, "outcome", "name")),
        "body_part_id": as_int(nested_get(shot, "body_part", "id")),
        "body_part_name": as_text(nested_get(shot, "body_part", "name")),
        "technique_id": as_int(nested_get(shot, "technique", "id")),
        "technique_name": as_text(nested_get(shot, "technique", "name")),
        "first_time": shot.get("first_time"),
        "one_on_one": shot.get("one_on_one"),
        "statsbomb_xg": as_float(shot.get("statsbomb_xg")),
    }


def _pass_row(record: JsonObject, match_id: int) -> CsvRow:
    pass_record = _object(record.get("pass"))
    end_location = pass_record.get("end_location")
    base = _event_row(record, match_id)
    return {
        "event_id": base["event_id"],
        "match_id": base["match_id"],
        "team_id": base["team_id"],
        "player_id": base["player_id"],
        "timestamp": base["timestamp"],
        "possession": base["possession"],
        "location_x": base["location_x"],
        "location_y": base["location_y"],
        "end_location_x": location_x(end_location),
        "end_location_y": location_y(end_location),
        "recipient_player_id": as_int(nested_get(pass_record, "recipient", "id")),
        "recipient_player_name": as_text(nested_get(pass_record, "recipient", "name")),
        "length": as_float(pass_record.get("length")),
        "angle": as_float(pass_record.get("angle")),
        "height_id": as_int(nested_get(pass_record, "height", "id")),
        "height_name": as_text(nested_get(pass_record, "height", "name")),
        "type_id": as_int(nested_get(pass_record, "type", "id")),
        "type_name": as_text(nested_get(pass_record, "type", "name")),
        "outcome_id": as_int(nested_get(pass_record, "outcome", "id")),
        "outcome_name": as_text(nested_get(pass_record, "outcome", "name")),
        "body_part_id": as_int(nested_get(pass_record, "body_part", "id")),
        "body_part_name": as_text(nested_get(pass_record, "body_part", "name")),
        "switch": pass_record.get("switch"),
        "cross": pass_record.get("cross"),
        "cut_back": pass_record.get("cut_back"),
        "assisted_shot_id": as_text(pass_record.get("assisted_shot_id")),
        "shot_assist": pass_record.get("shot_assist"),
        "goal_assist": pass_record.get("goal_assist"),
    }


def _pressure_row(record: JsonObject, match_id: int) -> CsvRow:
    pressure = _object(record.get("pressure"))
    base = _event_row(record, match_id)
    return {
        "event_id": base["event_id"],
        "match_id": base["match_id"],
        "team_id": base["team_id"],
        "player_id": base["player_id"],
        "timestamp": base["timestamp"],
        "possession": base["possession"],
        "location_x": base["location_x"],
        "location_y": base["location_y"],
        "counterpress": pressure.get("counterpress") or record.get("counterpress"),
    }


def _three_sixty_rows(record: JsonObject, match_id: int) -> list[CsvRow]:
    freeze_frame = _list_of_objects(record.get("freeze_frame"))
    visible_area = json_text(record.get("visible_area"))
    rows: list[CsvRow] = []
    for frame in freeze_frame:
        location = frame.get("location")
        rows.append(
            {
                "event_id": as_text(record.get("event_uuid")),
                "match_id": match_id,
                "player_id": as_int(nested_get(frame, "player", "id")),
                "player_name": as_text(nested_get(frame, "player", "name")),
                "teammate": frame.get("teammate"),
                "actor": frame.get("actor"),
                "keeper": frame.get("keeper"),
                "location_x": location_x(location),
                "location_y": location_y(location),
                "visible_area": visible_area,
            }
        )
    return rows


def _upsert_team(
    teams: dict[int, CsvRow],
    team_id_value: Any,
    team_name: Any,
    country_name: Any,
) -> int | None:
    team_id = as_int(team_id_value)
    if team_id is None:
        return None

    existing = teams.get(team_id, {})
    teams[team_id] = {
        "team_id": team_id,
        "team_name": as_text(existing.get("team_name") or team_name),
        "country_name": as_text(existing.get("country_name") or country_name),
    }
    return team_id


def _upsert_player(
    players: dict[int, CsvRow],
    player_id_value: Any,
    player_name: Any,
    team_id: Any,
    team_name: Any,
    jersey_number: Any,
    country_name: Any,
) -> int | None:
    player_id = as_int(player_id_value)
    if player_id is None:
        return None

    existing = players.get(player_id, {})
    players[player_id] = {
        "player_id": player_id,
        "player_name": as_text(existing.get("player_name") or player_name),
        "team_id": as_int(existing.get("team_id")) or as_int(team_id),
        "team_name": as_text(existing.get("team_name") or team_name),
        "jersey_number": as_int(existing.get("jersey_number")) or as_int(jersey_number),
        "country_name": as_text(existing.get("country_name") or country_name),
    }
    return player_id


def _object(value: Any) -> JsonObject:
    return value if isinstance(value, dict) else {}


def _list_of_objects(value: Any) -> list[JsonObject]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _location_z(value: Any) -> float | None:
    if isinstance(value, list) and len(value) > 2:
        return as_float(value[2])
    return None
