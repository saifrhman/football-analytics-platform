import pytest

from football_intelligence.ingestion.statsbomb.parsers import (
    StatsBombParseError,
    parse_competition_record,
    parse_event_record,
    parse_lineup_record,
    parse_match_record,
    parse_three_sixty_record,
)


def test_parse_competition_record() -> None:
    record = {
        "competition_id": 2,
        "season_id": 44,
        "competition_name": "Premier League",
        "season_name": "2003/2004",
    }

    parsed = parse_competition_record(record)

    assert parsed.competition_id == 2
    assert parsed.season_id == 44
    assert parsed.competition_name == "Premier League"


def test_parse_match_record() -> None:
    record = {
        "match_id": 3754058,
        "match_date": "2020-02-01",
        "home_team": {"home_team_id": 1, "home_team_name": "Home"},
        "away_team": {"away_team_id": 2, "away_team_name": "Away"},
    }

    parsed = parse_match_record(record)

    assert parsed.match_id == 3754058
    assert parsed.home_team_id == 1
    assert parsed.away_team_id == 2


def test_parse_event_record() -> None:
    record = {
        "id": "9b728cc7-3fdf-41a1-b96b-7dc2a1187a3f",
        "match_id": 3754058,
        "type": {"id": 30, "name": "Pass"},
        "team": {"id": 1, "name": "Home"},
        "player": {"id": 10, "name": "Midfielder"},
    }

    parsed = parse_event_record(record)

    assert parsed.event_id == "9b728cc7-3fdf-41a1-b96b-7dc2a1187a3f"
    assert parsed.match_id == 3754058
    assert parsed.event_type == "Pass"
    assert parsed.team_id == 1
    assert parsed.player_id == 10


def test_parse_lineup_record() -> None:
    record = {
        "team_id": 1,
        "team_name": "Home",
        "lineup": [
            {"player_id": 10, "player_name": "Player A"},
            {"player_id": 11, "player_name": "Player B"},
        ],
    }

    parsed = parse_lineup_record(record)

    assert parsed.team_id == 1
    assert parsed.player_ids == (10, 11)


def test_parse_three_sixty_record() -> None:
    record = {
        "event_uuid": "9b728cc7-3fdf-41a1-b96b-7dc2a1187a3f",
        "visible_area": [1.0, 2.0, 3.0, 4.0],
        "freeze_frame": [{"player": {"id": 10}}, {"player": {"id": 11}}],
    }

    parsed = parse_three_sixty_record(record)

    assert parsed.event_uuid == "9b728cc7-3fdf-41a1-b96b-7dc2a1187a3f"
    assert parsed.visible_area_points == 4
    assert parsed.freeze_frame_players == 2


def test_parse_event_rejects_missing_type() -> None:
    with pytest.raises(StatsBombParseError):
        parse_event_record({"id": "event-id"})
