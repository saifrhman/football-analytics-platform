import csv
from pathlib import Path

from football_intelligence.transformations.statsbomb.normalizer import normalize_statsbomb_bronze
from football_intelligence.transformations.statsbomb.reader import StatsBombBronzeReader
from football_intelligence.transformations.statsbomb.writer import write_silver_tables

FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "statsbomb_bronze"


def test_statsbomb_bronze_to_silver_tables(tmp_path: Path) -> None:
    bronze_open_data_dir = FIXTURE_ROOT / "statsbomb" / "open-data"

    bronze_data = StatsBombBronzeReader(bronze_open_data_dir).read()
    tables = normalize_statsbomb_bronze(bronze_data)
    written = write_silver_tables(tables, tmp_path)

    assert set(written) == {
        "competitions",
        "matches",
        "teams",
        "players",
        "events",
        "shots",
        "passes",
        "pressures",
        "three_sixty_freeze_frames",
    }

    competitions = _read_csv(tmp_path / "competitions.csv")
    matches = _read_csv(tmp_path / "matches.csv")
    events = _read_csv(tmp_path / "events.csv")
    shots = _read_csv(tmp_path / "shots.csv")
    passes = _read_csv(tmp_path / "passes.csv")
    pressures = _read_csv(tmp_path / "pressures.csv")
    frames = _read_csv(tmp_path / "three_sixty_freeze_frames.csv")

    assert competitions[0]["competition_id"] == "1"
    assert competitions[0]["season_id"] == "10"
    assert matches[0]["match_id"] == "100"
    assert matches[0]["home_team_id"] == "11"
    assert len(events) == 3
    assert events[0]["event_id"] == "event-pass-1"
    assert events[0]["possession"] == "1"
    assert events[0]["timestamp"] == "00:01:02.000"
    assert passes[0]["recipient_player_id"] == "102"
    assert passes[0]["end_location_x"] == "60.0"
    assert shots[0]["event_id"] == "event-shot-1"
    assert shots[0]["xg"] == "0.32"
    assert pressures[0]["counterpress"] == "True"
    assert len(frames) == 2
    assert frames[0]["event_id"] == "event-shot-1"
    assert frames[0]["player_id"] == "103"


def test_statsbomb_transform_builds_team_and_player_dimensions(tmp_path: Path) -> None:
    bronze_open_data_dir = FIXTURE_ROOT / "statsbomb" / "open-data"
    tables = normalize_statsbomb_bronze(StatsBombBronzeReader(bronze_open_data_dir).read())
    write_silver_tables(tables, tmp_path)

    teams = _read_csv(tmp_path / "teams.csv")
    players = _read_csv(tmp_path / "players.csv")

    assert {row["team_id"] for row in teams} == {"11", "22"}
    assert {row["player_id"] for row in players} >= {"101", "102", "103", "201"}


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))
