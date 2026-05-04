"""StatsBomb Open Data ingestion client."""

import json
import logging
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from football_intelligence.ingestion.base import IngestionClient, RawAsset
from football_intelligence.ingestion.statsbomb.parsers import (
    CompetitionRecord,
    parse_competition_record,
    parse_match_record,
)

logger = logging.getLogger(__name__)

DEFAULT_COLLECTIONS = ("competitions", "matches", "events", "lineups", "three-sixty")


class StatsBombIngestionError(RuntimeError):
    """Raised when StatsBomb Open Data cannot be read or parsed."""


@dataclass(frozen=True)
class _CompetitionMatchSelection:
    competition: CompetitionRecord
    matches: list[dict[str, Any]]
    match_ids: list[int]


class StatsBombOpenDataClient(IngestionClient):
    """Client for StatsBomb Open Data JSON assets.

    The client supports the public GitHub raw URL and a local mirror of the
    StatsBomb `open-data/data` directory. It discovers match-scoped assets from
    competitions and matches metadata, then yields source-faithful raw JSON
    assets ready for the bronze layer.
    """

    def __init__(
        self,
        base_url: str,
        *,
        local_data_dir: str | Path | None = None,
        collections: Iterable[str] = DEFAULT_COLLECTIONS,
        competition_ids: Iterable[int] | None = None,
        season_ids: Iterable[int] | None = None,
        match_ids: Iterable[int] | None = None,
        match_limit: int | None = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        if match_limit is not None and match_limit < 0:
            raise ValueError("match_limit must be greater than or equal to 0")

        self.base_url = base_url.rstrip("/")
        self.local_data_dir = Path(local_data_dir).expanduser() if local_data_dir else None
        self.collections = self._normalize_collections(collections)
        self.competition_ids = set(competition_ids or [])
        self.season_ids = set(season_ids or [])
        self.match_ids = set(match_ids or [])
        self.match_limit = match_limit
        self.timeout_seconds = timeout_seconds
        self._http_client = httpx.Client(timeout=timeout_seconds, follow_redirects=True)

    def fetch(self) -> Iterable[RawAsset]:
        """Yield StatsBomb raw assets for the configured collections."""

        logger.info("Starting StatsBomb ingestion collections=%s", ",".join(self.collections))

        competitions = self._read_json_list("competitions.json", required=True)
        parsed_competitions = [parse_competition_record(record) for record in competitions]
        filtered_competitions = [
            competition
            for competition in parsed_competitions
            if not self.competition_ids or competition.competition_id in self.competition_ids
            if not self.season_ids or competition.season_id in self.season_ids
        ]
        logger.info(
            "Selected StatsBomb competitions=%s",
            sorted({competition.competition_id for competition in filtered_competitions}),
        )
        logger.info(
            "Selected StatsBomb seasons=%s",
            sorted({competition.season_id for competition in filtered_competitions}),
        )

        if "competitions" in self.collections:
            yield RawAsset(
                source="statsbomb",
                path="statsbomb/open-data/competitions/competitions.json",
                payload=self._encode_json(competitions),
            )

        discovered_matches: list[tuple[CompetitionRecord, dict[str, Any], int]] = []
        for competition in filtered_competitions:
            matches_path = f"matches/{competition.competition_id}/{competition.season_id}.json"
            matches = self._read_json_list(matches_path, required=True)
            parsed_matches = [parse_match_record(record) for record in matches]
            discovered_matches.extend(
                (competition, match_record, parsed_match.match_id)
                for match_record, parsed_match in zip(matches, parsed_matches, strict=True)
                if not self.match_ids or parsed_match.match_id in self.match_ids
            )

        logger.info("Discovered StatsBomb matches=%d", len(discovered_matches))
        selected_matches = self._limit_matches(discovered_matches)
        logger.info("Selected StatsBomb matches after match-limit=%d", len(selected_matches))

        match_selections = self._group_matches_by_competition(selected_matches)
        for match_selection in match_selections:
            if "matches" in self.collections:
                yield RawAsset(
                    source="statsbomb",
                    path=(
                        "statsbomb/open-data/matches/"
                        f"competition_id={match_selection.competition.competition_id}/"
                        f"season_id={match_selection.competition.season_id}/matches.json"
                    ),
                    payload=self._encode_json(match_selection.matches),
                )

        selected_match_ids = sorted(
            {
                match_id
                for match_selection in match_selections
                for match_id in match_selection.match_ids
            }
        )
        for match_id in selected_match_ids:
            if "events" in self.collections:
                yield self._match_scoped_asset(
                    source_path=f"events/{match_id}.json",
                    bronze_path=f"statsbomb/open-data/events/match_id={match_id}/events.json",
                    required=True,
                )

            if "lineups" in self.collections:
                yield self._match_scoped_asset(
                    source_path=f"lineups/{match_id}.json",
                    bronze_path=f"statsbomb/open-data/lineups/match_id={match_id}/lineups.json",
                    required=True,
                )

            if "three-sixty" in self.collections:
                asset = self._optional_match_scoped_asset(
                    source_path=f"three-sixty/{match_id}.json",
                    bronze_path=(
                        f"statsbomb/open-data/three-sixty/match_id={match_id}/three-sixty.json"
                    ),
                )
                if asset is not None:
                    yield asset

        logger.info("Finished StatsBomb ingestion asset discovery")

    def close(self) -> None:
        """Close underlying network resources."""

        self._http_client.close()

    def _match_scoped_asset(
        self,
        source_path: str,
        bronze_path: str,
        *,
        required: bool,
    ) -> RawAsset:
        payload = self._read_bytes(source_path, required=required)
        return RawAsset(source="statsbomb", path=bronze_path, payload=payload)

    def _optional_match_scoped_asset(self, source_path: str, bronze_path: str) -> RawAsset | None:
        try:
            return self._match_scoped_asset(source_path, bronze_path, required=False)
        except FileNotFoundError:
            logger.info("Optional StatsBomb asset not found: %s", source_path)
            return None

    def _read_json_list(self, source_path: str, *, required: bool) -> list[dict[str, Any]]:
        payload = self._read_bytes(source_path, required=required)
        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise StatsBombIngestionError(f"Invalid JSON in StatsBomb asset {source_path}") from exc

        if not isinstance(parsed, list):
            raise StatsBombIngestionError(f"Expected JSON array in StatsBomb asset {source_path}")

        return [self._ensure_mapping(record, source_path) for record in parsed]

    def _read_bytes(self, source_path: str, *, required: bool) -> bytes:
        if self.local_data_dir is not None:
            return self._read_local_bytes(source_path, required=required)

        return self._read_remote_bytes(source_path, required=required)

    def _read_local_bytes(self, source_path: str, *, required: bool) -> bytes:
        file_path = self.local_data_dir / source_path
        if not file_path.exists():
            if required:
                raise FileNotFoundError(f"Required StatsBomb file not found: {file_path}")
            raise FileNotFoundError(str(file_path))

        logger.debug("Reading local StatsBomb asset %s", file_path)
        return file_path.read_bytes()

    @retry(
        retry=retry_if_exception_type((httpx.HTTPError, StatsBombIngestionError)),
        wait=wait_exponential(multiplier=1, min=1, max=30),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    def _read_remote_bytes(self, source_path: str, *, required: bool) -> bytes:
        url = self._remote_url(source_path)
        logger.debug("Downloading StatsBomb asset %s", url)
        response = self._http_client.get(url)

        if response.status_code == 404 and not required:
            raise FileNotFoundError(url)

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise StatsBombIngestionError(
                f"Failed to download required StatsBomb asset {url}: {exc.response.status_code}"
            ) from exc

        return response.content

    def _remote_url(self, source_path: str) -> str:
        parsed = urlparse(self.base_url)
        if not parsed.scheme:
            raise StatsBombIngestionError(
                "Remote StatsBomb base URL must include a scheme, or set STATSBOMB_LOCAL_DATA_DIR"
            )

        return f"{self.base_url}/{source_path.lstrip('/')}"

    @staticmethod
    def _ensure_mapping(record: Any, source_path: str) -> dict[str, Any]:
        if not isinstance(record, dict):
            raise StatsBombIngestionError(
                f"Expected object records in StatsBomb asset {source_path}"
            )
        return record

    @staticmethod
    def _encode_json(records: list[dict[str, Any]]) -> bytes:
        return json.dumps(records, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

    def _limit_matches(
        self,
        matches: list[tuple[CompetitionRecord, dict[str, Any], int]],
    ) -> list[tuple[CompetitionRecord, dict[str, Any], int]]:
        if self.match_limit is None:
            return matches
        return matches[: self.match_limit]

    @staticmethod
    def _group_matches_by_competition(
        matches: list[tuple[CompetitionRecord, dict[str, Any], int]],
    ) -> list[_CompetitionMatchSelection]:
        grouped: dict[tuple[int, int], _CompetitionMatchSelection] = {}
        for competition, match_record, match_id in matches:
            key = (competition.competition_id, competition.season_id)
            if key not in grouped:
                grouped[key] = _CompetitionMatchSelection(
                    competition=competition,
                    matches=[],
                    match_ids=[],
                )
            grouped[key].matches.append(match_record)
            grouped[key].match_ids.append(match_id)
        return list(grouped.values())

    @staticmethod
    def _normalize_collections(collections: Iterable[str]) -> tuple[str, ...]:
        normalized = tuple(collection.strip() for collection in collections if collection.strip())
        unknown = sorted(set(normalized) - set(DEFAULT_COLLECTIONS))
        if unknown:
            raise ValueError(f"Unknown StatsBomb collection(s): {', '.join(unknown)}")
        return normalized
