"""FastAPI application exposing curated football intelligence data."""

from fastapi import FastAPI

from football_intelligence import __version__

app = FastAPI(
    title="Football Intelligence Platform API",
    version=__version__,
)


@app.get("/health")
def health() -> dict[str, str]:
    """Return service health status."""

    return {"status": "ok", "version": __version__}


@app.get("/players")
def list_players() -> list[dict[str, object]]:
    """Placeholder endpoint for curated player dimension data."""

    return []


@app.get("/matches")
def list_matches() -> list[dict[str, object]]:
    """Placeholder endpoint for curated match dimension data."""

    return []


@app.get("/analytics/xg-trend")
def xg_trend() -> list[dict[str, object]]:
    """Placeholder endpoint for xG trend data."""

    return []
