"""Parsing helpers for representative StatsBomb Open Data records."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class StatsBombParseError(ValueError):
    """Raised when a StatsBomb record does not satisfy expected shape."""


@dataclass(frozen=True)
class CompetitionRecord:
    """Parsed competition-season record."""

    competition_id: int
    season_id: int
    competition_name: str
    season_name: str


@dataclass(frozen=True)
class MatchRecord:
    """Parsed match metadata record."""

    match_id: int
    match_date: str
    home_team_id: int
    away_team_id: int


@dataclass(frozen=True)
class EventRecord:
    """Parsed event record with common identifiers."""

    event_id: str
    match_id: int | None
    event_type: str
    team_id: int | None
    player_id: int | None


@dataclass(frozen=True)
class LineupRecord:
    """Parsed lineup team record."""

    team_id: int
    team_name: str
    player_ids: tuple[int, ...]


@dataclass(frozen=True)
class ThreeSixtyRecord:
    """Parsed StatsBomb 360 frame record."""

    event_uuid: str
    visible_area_points: int
    freeze_frame_players: int


def parse_competition_record(record: dict[str, Any]) -> CompetitionRecord:
    """Parse a StatsBomb `competitions.json` record."""

    return CompetitionRecord(
        competition_id=_required_int(record, "competition_id"),
        season_id=_required_int(record, "season_id"),
        competition_name=_required_str(record, "competition_name"),
        season_name=_required_str(record, "season_name"),
    )


def parse_match_record(record: dict[str, Any]) -> MatchRecord:
    """Parse a StatsBomb match metadata record."""

    home_team = _required_mapping(record, "home_team")
    away_team = _required_mapping(record, "away_team")
    return MatchRecord(
        match_id=_required_int(record, "match_id"),
        match_date=_required_str(record, "match_date"),
        home_team_id=_required_int(home_team, "home_team_id"),
        away_team_id=_required_int(away_team, "away_team_id"),
    )


def parse_event_record(record: dict[str, Any]) -> EventRecord:
    """Parse a representative StatsBomb event record."""

    event_type = _required_mapping(record, "type")
    team = record.get("team")
    player = record.get("player")
    return EventRecord(
        event_id=_required_str(record, "id"),
        match_id=_optional_int(record, "match_id"),
        event_type=_required_str(event_type, "name"),
        team_id=_optional_nested_int(team, "id"),
        player_id=_optional_nested_int(player, "id"),
    )


def parse_lineup_record(record: dict[str, Any]) -> LineupRecord:
    """Parse a StatsBomb lineup team record."""

    lineup = record.get("lineup", [])
    if not isinstance(lineup, list):
        raise StatsBombParseError("Expected lineup to be a list")

    player_ids = []
    for player in lineup:
        if not isinstance(player, dict):
            raise StatsBombParseError("Expected lineup player records to be objects")
        player_ids.append(_required_int(player, "player_id"))

    return LineupRecord(
        team_id=_required_int(record, "team_id"),
        team_name=_required_str(record, "team_name"),
        player_ids=tuple(player_ids),
    )


def parse_three_sixty_record(record: dict[str, Any]) -> ThreeSixtyRecord:
    """Parse a representative StatsBomb 360 frame record."""

    visible_area = record.get("visible_area", [])
    freeze_frame = record.get("freeze_frame", [])
    if not isinstance(visible_area, list):
        raise StatsBombParseError("Expected visible_area to be a list")
    if not isinstance(freeze_frame, list):
        raise StatsBombParseError("Expected freeze_frame to be a list")

    return ThreeSixtyRecord(
        event_uuid=_required_str(record, "event_uuid"),
        visible_area_points=len(visible_area),
        freeze_frame_players=len(freeze_frame),
    )


def _required_mapping(record: dict[str, Any], key: str) -> dict[str, Any]:
    value = record.get(key)
    if not isinstance(value, dict):
        raise StatsBombParseError(f"Missing or invalid object field: {key}")
    return value


def _required_str(record: dict[str, Any], key: str) -> str:
    value = record.get(key)
    if not isinstance(value, str) or not value:
        raise StatsBombParseError(f"Missing or invalid string field: {key}")
    return value


def _required_int(record: dict[str, Any], key: str) -> int:
    value = record.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise StatsBombParseError(f"Missing or invalid integer field: {key}")
    return value


def _optional_int(record: dict[str, Any], key: str) -> int | None:
    value = record.get(key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise StatsBombParseError(f"Invalid integer field: {key}")
    return value


def _optional_nested_int(value: Any, key: str) -> int | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise StatsBombParseError(f"Expected optional nested field {key} to be in an object")
    return _optional_int(value, key)
