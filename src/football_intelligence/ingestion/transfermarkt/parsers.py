"""Parsers for Transfermarkt squad and transfer HTML."""

from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup
from bs4.element import Tag

from football_intelligence.ingestion.transfermarkt.models import (
    PlayerMarketValueRecord,
    TransferRecord,
)

PLAYER_ID_RE = re.compile(r"/spieler/(\d+)")
EURO_RE = re.compile(r"€\s*([0-9]+(?:[.,][0-9]+)?)\s*([kKmM]?)")


def parse_squad_market_values_html(
    html: str | bytes,
    *,
    source_url: str,
) -> list[PlayerMarketValueRecord]:
    """Parse a Transfermarkt squad page into silver-ready market value rows."""

    soup = BeautifulSoup(html, "html.parser")
    rows = _data_rows(soup)
    records: list[PlayerMarketValueRecord] = []
    for row in rows:
        player_link = _first_player_link(row)
        if player_link is None:
            continue

        cells = _cell_texts(row)
        value_text = _last_market_value_text(row)
        player_name = player_link.get_text(" ", strip=True)
        records.append(
            PlayerMarketValueRecord(
                player_id=_player_id_from_href(player_link.get("href")),
                player_name=player_name,
                age=_first_int(cells, min_value=14, max_value=60),
                nationality=_nationality(row),
                position=_position(cells, player_name),
                club=_meta_content(soup, "og:title"),
                market_value_eur=parse_money_to_eur(value_text),
                source_url=source_url,
            )
        )

    return records


def parse_transfers_html(html: str | bytes, *, source_url: str) -> list[TransferRecord]:
    """Parse a Transfermarkt transfers page into silver-ready transfer rows."""

    soup = BeautifulSoup(html, "html.parser")
    rows = _data_rows(soup)
    records: list[TransferRecord] = []
    for row in rows:
        player_link = _first_player_link(row)
        if player_link is None:
            continue

        cells = _cell_texts(row)
        fee_text = _fee_text(cells)
        records.append(
            TransferRecord(
                player_id=_optional_player_id_from_href(player_link.get("href")),
                player_name=player_link.get_text(" ", strip=True),
                from_club=_club_from_selector(
                    row,
                    ".verein-flagge-transfer-cell .vereinprofil_tooltip",
                ),
                to_club=_club_from_selector(
                    row,
                    ".verein-flagge-transfer-cell + td .vereinprofil_tooltip",
                ),
                transfer_fee_eur=parse_money_to_eur(fee_text),
                transfer_fee_text=fee_text,
                season=_season_from_text(soup.get_text(" ", strip=True)),
                source_url=source_url,
            )
        )

    return records


def parse_money_to_eur(value: str | None) -> int | None:
    """Convert Transfermarkt value text such as `€1.20m` to whole euros."""

    if not value:
        return None

    normalized = value.replace("\xa0", " ").strip()
    match = EURO_RE.search(normalized)
    if match is None:
        return None

    amount = float(match.group(1).replace(",", "."))
    suffix = match.group(2).lower()
    multiplier = 1_000_000 if suffix == "m" else 1_000 if suffix == "k" else 1
    return int(amount * multiplier)


def _data_rows(soup: BeautifulSoup) -> list[Tag]:
    rows = soup.select("tr.odd, tr.even, tr[data-player-id]")
    if rows:
        return [row for row in rows if isinstance(row, Tag)]
    return [row for row in soup.select("tbody tr") if isinstance(row, Tag)]


def _first_player_link(row: Tag) -> Tag | None:
    for link in row.select("a[href*='/profil/spieler/'], a[href*='/spieler/']"):
        if isinstance(link, Tag) and link.get_text(strip=True):
            return link
    return None


def _player_id_from_href(href: Any) -> str:
    player_id = _optional_player_id_from_href(href)
    if player_id is None:
        raise ValueError("Could not parse Transfermarkt player ID from href")
    return player_id


def _optional_player_id_from_href(href: Any) -> str | None:
    if not isinstance(href, str):
        return None
    match = PLAYER_ID_RE.search(href)
    return match.group(1) if match else None


def _cell_texts(row: Tag) -> list[str]:
    return [
        cell.get_text(" ", strip=True)
        for cell in row.select("td")
        if cell.get_text(strip=True)
    ]


def _last_market_value_text(row: Tag) -> str | None:
    candidates = [
        cell.get_text(" ", strip=True)
        for cell in row.select("td")
        if "€" in cell.get_text(" ", strip=True)
    ]
    return candidates[-1] if candidates else None


def _first_int(values: list[str], *, min_value: int, max_value: int) -> int | None:
    for value in values:
        if value.isdigit():
            parsed = int(value)
            if min_value <= parsed <= max_value:
                return parsed
    return None


def _nationality(row: Tag) -> str | None:
    titles = [
        image.get("title") or image.get("alt")
        for image in row.select("img")
        if image.get("title") or image.get("alt")
    ]
    return str(titles[0]) if titles else None


def _position(cells: list[str], player_name: str) -> str | None:
    ignored = {player_name}
    for value in cells:
        if value in ignored or value.isdigit() or "€" in value:
            continue
        if len(value) <= 40:
            return value
    return None


def _meta_content(soup: BeautifulSoup, property_name: str) -> str | None:
    meta = soup.find("meta", property=property_name)
    if isinstance(meta, Tag):
        content = meta.get("content")
        return str(content) if content else None
    return None


def _fee_text(cells: list[str]) -> str | None:
    for value in reversed(cells):
        lower = value.lower()
        if "€" in value or lower in {"free transfer", "loan", "end of loan", "?"}:
            return value
    return None


def _club_from_selector(row: Tag, selector: str) -> str | None:
    club = row.select_one(selector)
    if club is None:
        return None
    return club.get_text(" ", strip=True) or str(club.get("title") or "") or None


def _season_from_text(text: str) -> str | None:
    match = re.search(r"\b(20\d{2}/\d{2}|19\d{2}/\d{2})\b", text)
    return match.group(1) if match else None
