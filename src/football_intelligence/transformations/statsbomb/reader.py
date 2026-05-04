"""Bronze file discovery for StatsBomb Open Data."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from football_intelligence.transformations.statsbomb.types import JsonObject
from football_intelligence.transformations.statsbomb.utils import read_json_array

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MatchScopedRecords:
    """JSON records loaded from a match-scoped bronze file."""

    match_id: int
    path: Path
    records: list[JsonObject]


@dataclass(frozen=True)
class StatsBombBronzeData:
    """All supported StatsBomb bronze collections."""

    competitions: list[JsonObject]
    matches: list[JsonObject]
    events: list[MatchScopedRecords]
    lineups: list[MatchScopedRecords]
    three_sixty: list[MatchScopedRecords]


class StatsBombBronzeReader:
    """Read raw StatsBomb bronze files from a local open-data root."""

    def __init__(self, bronze_open_data_dir: str | Path) -> None:
        self.root = Path(bronze_open_data_dir).expanduser()

    def read(self) -> StatsBombBronzeData:
        """Read all supported bronze collections, skipping absent optional groups."""

        if not self.root.exists():
            raise FileNotFoundError(f"StatsBomb bronze directory does not exist: {self.root}")

        return StatsBombBronzeData(
            competitions=self._read_optional_array(self.root / "competitions/competitions.json"),
            matches=self._read_matches(),
            events=self._read_match_scoped("events", "events.json"),
            lineups=self._read_match_scoped("lineups", "lineups.json"),
            three_sixty=self._read_match_scoped("three-sixty", "three-sixty.json"),
        )

    def _read_optional_array(self, path: Path) -> list[JsonObject]:
        if not path.exists():
            logger.warning("StatsBomb bronze file not found: %s", path)
            return []
        logger.info("Reading StatsBomb bronze file %s", path)
        return read_json_array(path)

    def _read_matches(self) -> list[JsonObject]:
        matches_root = self.root / "matches"
        if not matches_root.exists():
            logger.warning("StatsBomb matches bronze directory not found: %s", matches_root)
            return []

        records: list[JsonObject] = []
        for path in sorted(matches_root.glob("competition_id=*/season_id=*/matches.json")):
            logger.info("Reading StatsBomb matches file %s", path)
            records.extend(read_json_array(path))
        return records

    def _read_match_scoped(self, directory: str, file_name: str) -> list[MatchScopedRecords]:
        collection_root = self.root / directory
        if not collection_root.exists():
            logger.warning(
                "StatsBomb %s bronze directory not found: %s",
                directory,
                collection_root,
            )
            return []

        groups: list[MatchScopedRecords] = []
        for path in sorted(collection_root.glob(f"match_id=*/{file_name}")):
            match_id = _match_id_from_path(path)
            logger.info("Reading StatsBomb %s file %s", directory, path)
            groups.append(
                MatchScopedRecords(
                    match_id=match_id,
                    path=path,
                    records=read_json_array(path),
                )
            )
        return groups


def _match_id_from_path(path: Path) -> int:
    for part in path.parts:
        if part.startswith("match_id="):
            return int(part.removeprefix("match_id="))
    raise ValueError(f"Could not infer match_id from path: {path}")
