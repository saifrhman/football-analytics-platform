"""Command-line entrypoint for Transfermarkt ingestion."""

from __future__ import annotations

import argparse
import json
import logging
from dataclasses import asdict
from pathlib import Path

from football_intelligence.config.settings import get_settings
from football_intelligence.ingestion.transfermarkt.client import TransfermarktClient
from football_intelligence.ingestion.transfermarkt.parsers import (
    parse_squad_market_values_html,
    parse_transfers_html,
)
from football_intelligence.ingestion.transfermarkt.silver import (
    write_market_values,
    write_transfers,
)
from football_intelligence.io.local import LocalObjectWriter
from football_intelligence.logging import configure_logging

logger = logging.getLogger(__name__)


def main() -> None:
    """Run Transfermarkt collection and silver-ready parsing."""

    configure_logging()
    settings = get_settings()
    args = _parse_args()

    squad_urls = _split_csv(args.squad_urls or settings.transfermarkt_squad_urls)
    transfer_urls = _split_csv(args.transfer_urls or settings.transfermarkt_transfer_urls)

    client = TransfermarktClient(
        base_url=args.base_url or settings.transfermarkt_base_url,
        user_agent=args.user_agent or settings.transfermarkt_user_agent,
        request_delay_seconds=args.delay_seconds or settings.transfermarkt_request_delay_seconds,
        squad_urls=squad_urls,
        transfer_urls=transfer_urls,
    )
    bronze_writer = LocalObjectWriter(args.bronze_dir or settings.local_bronze_dir)
    silver_dir = Path(args.silver_dir or settings.local_silver_dir)

    market_value_records = []
    transfer_records = []
    collected_pages = []
    raw_assets = 0

    try:
        for asset in client.fetch():
            bronze_result = bronze_writer.write_asset(asset)
            raw_assets += 1
            asset_dataset = getattr(asset, "dataset", "")
            asset_url = getattr(asset, "url", str(bronze_result.path))
            collected_pages.append(
                {
                    "dataset": asset_dataset,
                    "url": asset_url,
                    "bronze_path": str(bronze_result.path),
                    "bytes_written": bronze_result.bytes_written,
                }
            )
            html = asset.payload.decode("utf-8", errors="replace")

            if asset_dataset == "squads":
                market_value_records.extend(
                    parse_squad_market_values_html(html, source_url=asset_url)
                )
            elif asset_dataset == "transfers":
                transfer_records.extend(parse_transfers_html(html, source_url=asset_url))
    finally:
        client.close()

    bronze_writer.write_bytes(
        "transfermarkt/raw_json/collected_pages.json",
        json.dumps(collected_pages, indent=2).encode("utf-8"),
    )
    bronze_writer.write_bytes(
        "transfermarkt/raw_json/ingestion_failures.json",
        json.dumps([asdict(failure) for failure in client.failures], indent=2).encode("utf-8"),
    )
    market_csv, market_json = write_market_values(market_value_records, silver_dir)
    transfers_csv, transfers_json = write_transfers(transfer_records, silver_dir)

    logger.info(
        "Transfermarkt ingestion complete raw_assets=%d market_value_rows=%d transfer_rows=%d "
        "failures=%d market_csv=%s market_json=%s transfers_csv=%s transfers_json=%s",
        raw_assets,
        len(market_value_records),
        len(transfer_records),
        len(client.failures),
        market_csv,
        market_json,
        transfers_csv,
        transfers_json,
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest Transfermarkt pages responsibly.")
    parser.add_argument("--base-url", help="Transfermarkt base URL.")
    parser.add_argument("--user-agent", help="Descriptive scraping user agent.")
    parser.add_argument("--delay-seconds", type=float, help="Delay between requests.")
    parser.add_argument("--squad-urls", help="Comma-separated squad market value URLs.")
    parser.add_argument("--transfer-urls", help="Comma-separated transfer URLs.")
    parser.add_argument("--bronze-dir", help="Local bronze root directory.")
    parser.add_argument("--silver-dir", help="Local silver output root directory.")
    return parser.parse_args()


def _split_csv(value: str | None) -> tuple[str, ...]:
    if not value:
        return ()
    return tuple(item.strip() for item in value.split(",") if item.strip())


if __name__ == "__main__":
    main()
