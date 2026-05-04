import json
from pathlib import Path

from football_intelligence.ingestion.transfermarkt.models import PlayerMarketValueRecord
from football_intelligence.ingestion.transfermarkt.silver import write_market_values


def test_write_market_values_outputs_csv_and_json(tmp_path: Path) -> None:
    records = [
        PlayerMarketValueRecord(
            player_id="1001",
            player_name="Player One",
            age=24,
            nationality="England",
            position="Centre-Forward",
            club="Example FC",
            market_value_eur=12_500_000,
            source_url="fixture://squad",
        )
    ]

    csv_path, json_path = write_market_values(records, tmp_path)

    assert csv_path.read_text(encoding="utf-8").startswith("player_id,player_name")
    assert json.loads(json_path.read_text(encoding="utf-8"))[0]["player_id"] == "1001"
