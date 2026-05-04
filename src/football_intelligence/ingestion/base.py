"""Shared ingestion interfaces."""

from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class RawAsset:
    """Raw source object ready to persist to the bronze layer."""

    source: str
    path: str
    payload: bytes
    content_type: str = "application/json"


class IngestionClient(ABC):
    """Base contract for source-specific ingestion clients."""

    @abstractmethod
    def fetch(self) -> Iterable[RawAsset]:
        """Yield raw assets from the upstream source."""
