"""Local filesystem object writers for medallion development layers."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from football_intelligence.ingestion.base import RawAsset

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LocalWriteResult:
    """Metadata for a written local object."""

    path: Path
    bytes_written: int


class LocalObjectWriter:
    """Write assets under a local root using cloud-like object paths."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).expanduser()

    def write_asset(self, asset: RawAsset) -> LocalWriteResult:
        """Persist a raw asset under the local object root."""

        destination = self.root / asset.path
        return self.write_bytes(destination.relative_to(self.root), asset.payload)

    def write_bytes(self, object_path: str | Path, payload: bytes) -> LocalWriteResult:
        """Persist bytes under the local object root."""

        destination = self.root / object_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(payload)
        logger.info("Wrote local object %s bytes=%d", destination, len(payload))
        return LocalWriteResult(path=destination, bytes_written=len(payload))
