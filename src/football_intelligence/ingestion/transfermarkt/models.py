"""Silver-ready Transfermarkt record models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PlayerMarketValueRecord:
    """Cleaned squad/player market value record."""

    player_id: str
    player_name: str
    age: int | None
    nationality: str | None
    position: str | None
    club: str | None
    market_value_eur: int | None
    source_url: str


@dataclass(frozen=True)
class TransferRecord:
    """Cleaned player transfer record."""

    player_id: str | None
    player_name: str
    from_club: str | None
    to_club: str | None
    transfer_fee_eur: int | None
    transfer_fee_text: str | None
    season: str | None
    source_url: str
