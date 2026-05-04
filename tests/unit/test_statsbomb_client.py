import json
from pathlib import Path

from football_intelligence.ingestion.statsbomb.client import StatsBombOpenDataClient
from football_intelligence.ingestion.statsbomb.writer import LocalBronzeWriter


def test_statsbomb_client_reads_local_mirror_and_writes_bronze(tmp_path: Path) -> None:
    mirror = tmp_path / "open-data" / "data"
    _write_json(
        mirror / "competitions.json",
        [
            {
                "competition_id": 2,
                "season_id": 44,
                "competition_name": "Premier League",
                "season_name": "2003/2004",
            }
        ],
    )
    _write_json(
        mirror / "matches" / "2" / "44.json",
        [
            {
                "match_id": 1234,
                "match_date": "2020-02-01",
                "home_team": {"home_team_id": 1},
                "away_team": {"away_team_id": 2},
            }
        ],
    )
    _write_json(mirror / "events" / "1234.json", [{"id": "event-1", "type": {"name": "Pass"}}])
    _write_json(mirror / "lineups" / "1234.json", [{"team_id": 1, "team_name": "Home", "lineup": []}])
    _write_json(
        mirror / "three-sixty" / "1234.json",
        [{"event_uuid": "event-1", "visible_area": [], "freeze_frame": []}],
    )

    client = StatsBombOpenDataClient(
        "https://example.com/data",
        local_data_dir=mirror,
        collections=("competitions", "matches", "events", "lineups", "three-sixty"),
    )
    writer = LocalBronzeWriter(tmp_path / "bronze")

    written_paths = [writer.write(asset).path for asset in client.fetch()]

    assert tmp_path / "bronze/statsbomb/open-data/competitions/competitions.json" in written_paths
    assert (
        tmp_path
        / "bronze/statsbomb/open-data/matches/competition_id=2/season_id=44/matches.json"
        in written_paths
    )
    assert tmp_path / "bronze/statsbomb/open-data/events/match_id=1234/events.json" in written_paths
    assert tmp_path / "bronze/statsbomb/open-data/lineups/match_id=1234/lineups.json" in written_paths
    assert (
        tmp_path / "bronze/statsbomb/open-data/three-sixty/match_id=1234/three-sixty.json"
        in written_paths
    )


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
