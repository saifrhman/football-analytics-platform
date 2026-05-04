"""Silver-ready writers for cleaned Transfermarkt outputs."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from football_intelligence.ingestion.transfermarkt.models import (
    PlayerMarketValueRecord,
    TransferRecord,
)


def write_market_values(
    records: list[PlayerMarketValueRecord],
    output_dir: str | Path,
) -> tuple[Path, Path]:
    """Write player market value records as CSV and JSON."""

    return _write_records(records, Path(output_dir), "transfermarkt/player_market_values")


def write_transfers(records: list[TransferRecord], output_dir: str | Path) -> tuple[Path, Path]:
    """Write transfer records as CSV and JSON."""

    return _write_records(records, Path(output_dir), "transfermarkt/transfers")


def _write_records(records: list[Any], output_dir: Path, dataset: str) -> tuple[Path, Path]:
    rows = [asdict(record) for record in records]
    csv_path = output_dir / f"{dataset}.csv"
    json_path = output_dir / f"{dataset}.json"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)

    if rows:
        with csv_path.open("w", encoding="utf-8", newline="") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
    else:
        csv_path.write_text("", encoding="utf-8")

    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    return csv_path, json_path
