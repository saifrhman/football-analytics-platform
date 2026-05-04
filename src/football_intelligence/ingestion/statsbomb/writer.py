"""Local bronze writer for StatsBomb raw assets."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path

from football_intelligence.ingestion.base import RawAsset

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WriteResult:
    """Metadata for a written bronze asset."""

    path: Path
    bytes_written: int


class LocalBronzeWriter:
    """Write raw assets under a local bronze root using cloud-like object paths."""

    def __init__(self, bronze_root: str | Path) -> None:
        self.bronze_root = Path(bronze_root).expanduser()

    def write(self, asset: RawAsset) -> WriteResult:
        """Persist an asset to the configured local bronze directory."""

        destination = self.bronze_root / asset.path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(asset.payload)
        logger.info("Wrote bronze asset %s bytes=%d", destination, len(asset.payload))
        return WriteResult(path=destination, bytes_written=len(asset.payload))
