"""Command-line entrypoint for StatsBomb bronze-to-silver transformations."""

from __future__ import annotations

import argparse
import logging

from football_intelligence.config.settings import get_settings
from football_intelligence.logging import configure_logging
from football_intelligence.transformations.statsbomb.normalizer import normalize_statsbomb_bronze
from football_intelligence.transformations.statsbomb.reader import StatsBombBronzeReader
from football_intelligence.transformations.statsbomb.writer import write_silver_tables

logger = logging.getLogger(__name__)


def main() -> None:
    """Transform local StatsBomb bronze JSON into silver CSV tables."""

    configure_logging()
    settings = get_settings()
    args = _parse_args()

    bronze_dir = args.bronze_open_data_dir or settings.statsbomb_bronze_open_data_dir
    silver_dir = args.silver_dir or f"{settings.local_silver_dir}/statsbomb"

    try:
        bronze_data = StatsBombBronzeReader(bronze_dir).read()
        tables = normalize_statsbomb_bronze(bronze_data)
        written = write_silver_tables(tables, silver_dir)
    except Exception:
        logger.exception("StatsBomb bronze-to-silver transformation failed")
        raise

    logger.info("StatsBomb bronze-to-silver transformation complete tables=%d", len(written))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Transform StatsBomb bronze JSON to silver CSV.")
    parser.add_argument(
        "--bronze-open-data-dir",
        help="Path to local bronze statsbomb/open-data directory.",
    )
    parser.add_argument("--silver-dir", help="Path to local StatsBomb silver output directory.")
    return parser.parse_args()


if __name__ == "__main__":
    main()
