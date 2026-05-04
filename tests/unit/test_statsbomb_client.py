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
    _write_json(
        mirror / "events" / "1234.json",
        [{"id": "event-1", "type": {"name": "Pass"}}],
    )
    _write_json(
        mirror / "lineups" / "1234.json",
        [{"team_id": 1, "team_name": "Home", "lineup": []}],
    )
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

    competitions_path = tmp_path / (
        "bronze/statsbomb/open-data/competitions/competitions.json"
    )
    matches_path = tmp_path / (
        "bronze/statsbomb/open-data/matches/competition_id=2/season_id=44/matches.json"
    )
    events_path = tmp_path / "bronze/statsbomb/open-data/events/match_id=1234/events.json"
    lineups_path = tmp_path / (
        "bronze/statsbomb/open-data/lineups/match_id=1234/lineups.json"
    )
    three_sixty_path = tmp_path / (
        "bronze/statsbomb/open-data/three-sixty/match_id=1234/three-sixty.json"
    )

    assert competitions_path in written_paths
    assert matches_path in written_paths
    assert events_path in written_paths
    assert lineups_path in written_paths
    assert three_sixty_path in written_paths


def test_statsbomb_client_applies_match_limit_after_discovery(tmp_path: Path) -> None:
    mirror = _statsbomb_mirror(
        tmp_path,
        competitions=[(2, 44)],
        matches_by_competition={(2, 44): [100, 101, 102]},
    )
    client = StatsBombOpenDataClient(
        "https://example.com/data",
        local_data_dir=mirror,
        collections=("matches", "events"),
        match_limit=2,
    )

    assets = list(client.fetch())

    assert _asset_paths(assets) == [
        "statsbomb/open-data/matches/competition_id=2/season_id=44/matches.json",
        "statsbomb/open-data/events/match_id=100/events.json",
        "statsbomb/open-data/events/match_id=101/events.json",
    ]
    assert _match_ids_from_matches_asset(assets) == [100, 101]


def test_statsbomb_client_match_ids_still_filter_selected_matches(tmp_path: Path) -> None:
    mirror = _statsbomb_mirror(
        tmp_path,
        competitions=[(2, 44)],
        matches_by_competition={(2, 44): [100, 101, 102]},
    )
    client = StatsBombOpenDataClient(
        "https://example.com/data",
        local_data_dir=mirror,
        collections=("matches", "events"),
        match_ids=(101, 102),
    )

    assets = list(client.fetch())

    assert _asset_paths(assets) == [
        "statsbomb/open-data/matches/competition_id=2/season_id=44/matches.json",
        "statsbomb/open-data/events/match_id=101/events.json",
        "statsbomb/open-data/events/match_id=102/events.json",
    ]
    assert _match_ids_from_matches_asset(assets) == [101, 102]


def test_statsbomb_client_limits_matches_after_competition_and_season_filters(
    tmp_path: Path,
) -> None:
    mirror = _statsbomb_mirror(
        tmp_path,
        competitions=[(2, 44), (2, 45), (3, 44)],
        matches_by_competition={
            (2, 44): [100, 101],
            (2, 45): [200],
            (3, 44): [300],
        },
    )
    client = StatsBombOpenDataClient(
        "https://example.com/data",
        local_data_dir=mirror,
        collections=("matches", "events"),
        competition_ids=(2,),
        season_ids=(44,),
        match_limit=1,
    )

    assets = list(client.fetch())

    assert _asset_paths(assets) == [
        "statsbomb/open-data/matches/competition_id=2/season_id=44/matches.json",
        "statsbomb/open-data/events/match_id=100/events.json",
    ]
    assert _match_ids_from_matches_asset(assets) == [100]


def _statsbomb_mirror(
    tmp_path: Path,
    *,
    competitions: list[tuple[int, int]],
    matches_by_competition: dict[tuple[int, int], list[int]],
) -> Path:
    mirror = tmp_path / "open-data" / "data"
    _write_json(
        mirror / "competitions.json",
        [
            {
                "competition_id": competition_id,
                "season_id": season_id,
                "competition_name": f"Competition {competition_id}",
                "season_name": f"Season {season_id}",
            }
            for competition_id, season_id in competitions
        ],
    )

    for (competition_id, season_id), match_ids in matches_by_competition.items():
        _write_json(
            mirror / "matches" / str(competition_id) / f"{season_id}.json",
            [_match_record(match_id) for match_id in match_ids],
        )
        for match_id in match_ids:
            _write_json(
                mirror / "events" / f"{match_id}.json",
                [{"id": f"event-{match_id}", "type": {"name": "Pass"}}],
            )

    return mirror


def _match_record(match_id: int) -> dict[str, object]:
    return {
        "match_id": match_id,
        "match_date": "2020-02-01",
        "home_team": {"home_team_id": 1},
        "away_team": {"away_team_id": 2},
    }


def _asset_paths(assets: list[object]) -> list[str]:
    return [asset.path for asset in assets]


def _match_ids_from_matches_asset(assets: list[object]) -> list[int]:
    matches_asset = next(asset for asset in assets if "/matches/" in asset.path)
    return [record["match_id"] for record in json.loads(matches_asset.payload)]


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
