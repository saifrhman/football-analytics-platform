from pathlib import Path

from football_intelligence.ingestion.transfermarkt.parsers import (
    parse_money_to_eur,
    parse_squad_market_values_html,
    parse_transfers_html,
)

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "transfermarkt"


def test_parse_squad_market_values_html() -> None:
    html = (FIXTURE_DIR / "squad_sample.html").read_text(encoding="utf-8")

    records = parse_squad_market_values_html(html, source_url="fixture://squad")

    assert len(records) == 2
    assert records[0].player_id == "1001"
    assert records[0].player_name == "Player One"
    assert records[0].age == 24
    assert records[0].nationality == "England"
    assert records[0].position == "Centre-Forward"
    assert records[0].market_value_eur == 12_500_000
    assert records[1].market_value_eur == 750_000


def test_parse_transfers_html() -> None:
    html = (FIXTURE_DIR / "transfers_sample.html").read_text(encoding="utf-8")

    records = parse_transfers_html(html, source_url="fixture://transfers")

    assert len(records) == 2
    assert records[0].player_id == "1001"
    assert records[0].from_club == "Old FC"
    assert records[0].to_club == "Example FC"
    assert records[0].transfer_fee_eur == 8_000_000
    assert records[0].season == "2024/25"
    assert records[1].transfer_fee_text == "Free transfer"
    assert records[1].transfer_fee_eur is None


def test_parse_money_to_eur() -> None:
    assert parse_money_to_eur("€1.25m") == 1_250_000
    assert parse_money_to_eur("€500k") == 500_000
    assert parse_money_to_eur("Free transfer") is None
