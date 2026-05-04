# API Notes

Start the local FastAPI service:

```bash
PYTHONPATH=src uvicorn football_intelligence.api.main:app --reload
```

Interactive OpenAPI documentation is available at:

```text
http://127.0.0.1:8000/docs
```

Implemented endpoints:

- `GET /health`
- `GET /teams`
- `GET /players`
- `GET /matches`
- `GET /analytics/xg-summary`
- `GET /analytics/pass-types`
- `GET /analytics/shot-outcomes`
- `GET /analytics/pressures`

Analytics endpoints support optional `team_id`, `match_id`, `player_id`, and
`limit` query parameters.
