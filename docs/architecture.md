# Architecture

This document will capture the platform architecture as it evolves.

## Medallion Layers

- Bronze stores source-faithful raw assets.
- Silver stores cleaned, normalized, and conformed entities.
- Gold stores dimensional marts and analytics aggregates.

## Data Products

- FastAPI exposes curated warehouse data.
- Streamlit visualizes team, player, match, and market intelligence.
