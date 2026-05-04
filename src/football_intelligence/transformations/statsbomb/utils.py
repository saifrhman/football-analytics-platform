"""Utility helpers for safely flattening StatsBomb JSON."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from football_intelligence.transformations.statsbomb.types import JsonObject


def read_json_array(path: Path) -> list[JsonObject]:
    """Read a JSON file that is expected to contain an array of objects."""

    with path.open(encoding="utf-8") as file:
        payload = json.load(file)

    if not isinstance(payload, list):
        raise ValueError(f"Expected JSON array in {path}")

    rows: list[JsonObject] = []
    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            raise ValueError(f"Expected object at {path}[{index}]")
        rows.append(item)
    return rows


def nested_get(record: JsonObject | None, *keys: str) -> Any:
    """Safely read a nested value from dictionaries."""

    value: Any = record
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def as_int(value: Any) -> int | None:
    """Convert a value to int where safe."""

    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value)
    return None


def as_float(value: Any) -> float | None:
    """Convert a value to float where safe."""

    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def as_text(value: Any) -> str | None:
    """Convert present values to text while preserving nulls."""

    if value is None:
        return None
    return str(value)


def json_text(value: Any) -> str | None:
    """Serialize nested data for CSV columns that intentionally keep detail."""

    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def location_x(value: Any) -> float | None:
    """Extract the first coordinate from a StatsBomb location array."""

    if isinstance(value, list) and value:
        return as_float(value[0])
    return None


def location_y(value: Any) -> float | None:
    """Extract the second coordinate from a StatsBomb location array."""

    if isinstance(value, list) and len(value) > 1:
        return as_float(value[1])
    return None
