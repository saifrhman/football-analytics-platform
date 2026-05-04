"""Command-line entrypoint for StatsBomb bronze ingestion."""

from __future__ import annotations

import argparse
import logging

from football_intelligence.config.settings import get_settings
from football_intelligence.ingestion.statsbomb.client import StatsBombOpenDataClient
from football_intelligence.ingestion.statsbomb.writer import LocalBronzeWriter
from football_intelligence.logging import configure_logging

logger = logging.getLogger(__name__)


def main() -> None:
    """Run StatsBomb Open Data ingestion into the local bronze directory."""

    configure_logging()
    settings = get_settings()
    args = _parse_args()

    client = StatsBombOpenDataClient(
        base_url=args.base_url or settings.statsbomb_open_data_base_url,
        local_data_dir=args.local_data_dir or settings.statsbomb_local_data_dir,
        collections=_split_csv(args.collections or settings.statsbomb_collections),
        competition_ids=_split_int_csv(args.competition_ids or settings.statsbomb_competition_ids),
        season_ids=_split_int_csv(args.season_ids or settings.statsbomb_season_ids),
        match_ids=_split_int_csv(args.match_ids or settings.statsbomb_match_ids),
        match_limit=args.match_limit,
    )
    writer = LocalBronzeWriter(args.bronze_dir or settings.local_bronze_dir)

    assets_written = 0
    bytes_written = 0
    try:
        for asset in client.fetch():
            result = writer.write(asset)
            assets_written += 1
            bytes_written += result.bytes_written
    finally:
        client.close()

    logger.info(
        "StatsBomb ingestion complete assets_written=%d total_bytes_written=%d",
        assets_written,
        bytes_written,
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest StatsBomb Open Data into local bronze.")
    parser.add_argument("--base-url", help="StatsBomb open-data base URL.")
    parser.add_argument("--local-data-dir", help="Local StatsBomb open-data/data mirror.")
    parser.add_argument("--bronze-dir", help="Local bronze root directory.")
    parser.add_argument("--collections", help="Comma-separated collections to ingest.")
    parser.add_argument("--competition-ids", help="Comma-separated competition IDs.")
    parser.add_argument("--season-ids", help="Comma-separated season IDs.")
    parser.add_argument("--match-ids", help="Comma-separated match IDs.")
    parser.add_argument(
        "--match-limit",
        type=int,
        help="Maximum number of matches to ingest after competition, season, and match filters.",
    )
    return parser.parse_args()


def _split_csv(value: str | None) -> tuple[str, ...]:
    if not value:
        return ()
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _split_int_csv(value: str | None) -> tuple[int, ...]:
    return tuple(int(item) for item in _split_csv(value))


if __name__ == "__main__":
    main()
