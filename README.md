# football-intelligence-platform

Production-oriented football data engineering platform for ingesting, modelling,
serving, and visualising open football data.

## Goal

Build an end-to-end football intelligence platform aligned with elite football
club data engineering workflows: robust ingestion, lakehouse-style storage,
dimensional modelling, orchestration, CI/CD, cloud infrastructure, APIs, and
analytics dashboards.

## Data Sources

- StatsBomb Open Data: competitions, matches, events, lineups, and 360 data.
- Transfermarkt public web data: market values, transfers, squad composition,
  player ages, nationalities, and fees, scraped responsibly.

## Architecture

The repository follows a medallion/lakehouse design.

- Bronze: raw JSON and scraped source snapshots stored in object storage.
- Silver: cleaned and normalized warehouse tables.
- Gold: analytics-ready marts for dashboards and APIs.

## Target Stack

- Python for ingestion, quality checks, APIs, and dashboards.
- GCS and BigQuery for storage and warehouse layers.
- dbt for warehouse transformations and tests.
- Airflow for orchestration.
- Docker Compose for local development.
- Terraform for cloud infrastructure.
- FastAPI for curated data access.
- Streamlit for football analytics data products.
- GitHub Actions for linting, testing, and dbt validation.

## Repository Layout

```text
.
├── airflow/                 # Airflow DAGs and plugins
├── dbt/football_intelligence # dbt project
├── docker/                  # Service-specific Dockerfiles
├── docs/                    # Architecture and operating notes
├── infra/terraform/         # GCS and BigQuery infrastructure skeleton
├── scripts/                 # Local developer and CI helper scripts
├── src/football_intelligence # Python application package
└── tests/                   # Unit and integration tests
```

## Quick Start

1. Copy `.env.example` to `.env` and fill in local values.
2. Build local services:

```bash
make build
```

3. Run the development stack:

```bash
make up
```

4. Run checks:

```bash
make lint
make test
```

## StatsBomb Bronze Ingestion

StatsBomb Open Data ingestion writes source-faithful JSON into the local bronze
directory using object-storage style paths. By default, the bronze root is
`./data/bronze`.

Warning: do not run full StatsBomb ingestion as your first local ingestion.
The open-data repository contains enough match-scoped event, lineup, and 360
assets to make local runs slow and bulky. For local development, start with the
bounded sample command and only use full ingestion after cloud or chunked
processing is ready.

Recommended local development command:

```bash
make ingest-statsbomb-sample
```

Sample ingestion command:

```bash
python3 -m football_intelligence.ingestion.statsbomb.run \
  --competition-ids 2 \
  --season-ids 44 \
  --match-limit 5 \
  --bronze-dir ./data/bronze
```

The `--match-limit` value is applied after `--competition-ids`,
`--season-ids`, and `--match-ids`, so samples stay bounded even when filters
match many fixtures.

Full ingestion from the public GitHub raw data source should wait until cloud
storage, orchestration, or chunked processing is in place:

```bash
make ingest-statsbomb
```

Or call the module directly:

```bash
python3 -m football_intelligence.ingestion.statsbomb.run \
  --bronze-dir ./data/bronze \
  --collections competitions,matches,events,lineups,three-sixty
```

To ingest from a local clone or mirror of `statsbomb/open-data/data`, set
`STATSBOMB_LOCAL_DATA_DIR` or pass `--local-data-dir`:

```bash
python3 -m football_intelligence.ingestion.statsbomb.run \
  --local-data-dir ./external/statsbomb-open-data/data \
  --bronze-dir ./data/bronze
```

Useful filters:

```bash
python3 -m football_intelligence.ingestion.statsbomb.run \
  --competition-ids 2 \
  --season-ids 44 \
  --match-ids 1234 \
  --match-limit 5
```

Expected bronze layout:

```text
data/bronze/statsbomb/open-data/
├── competitions/competitions.json
├── matches/competition_id=<id>/season_id=<id>/matches.json
├── events/match_id=<id>/events.json
├── lineups/match_id=<id>/lineups.json
└── three-sixty/match_id=<id>/three-sixty.json
```

## StatsBomb Silver Transformation

The StatsBomb silver transformation reads raw bronze JSON and writes cleaned,
flattened CSV tables for dbt loading, warehouse modelling, APIs, and dashboard
features.

Run:

```bash
make transform-statsbomb-silver
```

For local development, transform the small sample you ingested first:

```bash
make transform-statsbomb-silver-sample
```

Sample transformation command:

```bash
python3 -m football_intelligence.transformations.statsbomb.run \
  --bronze-open-data-dir ./data/bronze/statsbomb/open-data \
  --silver-dir ./data/silver/statsbomb
```

Or call the module directly:

```bash
python3 -m football_intelligence.transformations.statsbomb.run \
  --bronze-open-data-dir ./data/bronze/statsbomb/open-data \
  --silver-dir ./data/silver/statsbomb
```

Expected input layout:

```text
data/bronze/statsbomb/open-data/
├── competitions/competitions.json
├── matches/competition_id=<id>/season_id=<id>/matches.json
├── events/match_id=<id>/events.json
├── lineups/match_id=<id>/lineups.json
└── three-sixty/match_id=<id>/three-sixty.json
```

Expected output layout:

```text
data/silver/statsbomb/
├── competitions.csv
├── matches.csv
├── teams.csv
├── players.csv
├── events.csv
├── shots.csv
├── passes.csv
├── pressures.csv
└── three_sixty_freeze_frames.csv
```

## StatsBomb BigQuery Loading

The StatsBomb BigQuery loader reads local silver CSV files from
`./data/silver/statsbomb` and loads them into the configured silver BigQuery
dataset with explicit table schemas. Development loads use `WRITE_TRUNCATE`, so
each run replaces the target tables.

Set the required environment variables before loading:

```bash
export GCP_PROJECT_ID=<your-gcp-project>
export BIGQUERY_DATASET_SILVER=<your-silver-dataset>
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
```

Load the StatsBomb silver tables:

```bash
make load-statsbomb-bigquery
```

Or call the module directly:

```bash
python3 -m football_intelligence.loaders.bigquery.statsbomb_silver \
  --silver-dir ./data/silver/statsbomb
```

The loader writes these tables: `competitions`, `matches`, `teams`, `players`,
`events`, `shots`, `passes`, `pressures`, and
`three_sixty_freeze_frames`.

Silver table purpose:

- `competitions.csv`: one row per competition-season.
- `matches.csv`: cleaned match metadata with competition, season, team, score,
  stadium, and referee identifiers.
- `teams.csv`: deduplicated team dimension seeds from matches, lineups, and
  events.
- `players.csv`: deduplicated player dimension seeds from lineups and events.
- `events.csv`: flattened event fact base preserving `event_id`, `match_id`,
  `team_id`, `player_id`, `possession`, and `timestamp`.
- `shots.csv`: shot-specific event details including xG, outcome, technique,
  body part, and shot end location.
- `passes.csv`: pass-specific event details including recipient, pass type,
  height, outcome, body part, and end location.
- `pressures.csv`: pressure-specific event details for defensive analysis and
  heatmaps.
- `three_sixty_freeze_frames.csv`: one row per 360 freeze-frame player with
  event, match, player, teammate, actor, keeper, and location fields.

## Transfermarkt Ingestion

Transfermarkt ingestion is intentionally URL-driven and conservative. Configure
only the squad and transfer pages you want to collect, use a descriptive user
agent, and keep a delay between requests. The default delay is 2 seconds.

Example `.env` values:

```bash
TRANSFERMARKT_USER_AGENT=football-intelligence-platform/0.1 your-email@example.com
TRANSFERMARKT_REQUEST_DELAY_SECONDS=3
TRANSFERMARKT_SQUAD_URLS=https://www.transfermarkt.com/example/kader/verein/1/saison_id/2024/plus/1
TRANSFERMARKT_TRANSFER_URLS=https://www.transfermarkt.com/example/transfers/verein/1/saison_id/2024
LOCAL_BRONZE_DIR=./data/bronze
LOCAL_SILVER_DIR=./data/silver
```

Run:

```bash
make ingest-transfermarkt
```

Or call the module directly:

```bash
python3 -m football_intelligence.ingestion.transfermarkt.run \
  --delay-seconds 3 \
  --squad-urls "https://www.transfermarkt.com/example/kader/verein/1/saison_id/2024/plus/1" \
  --transfer-urls "https://www.transfermarkt.com/example/transfers/verein/1/saison_id/2024" \
  --bronze-dir ./data/bronze \
  --silver-dir ./data/silver
```

Raw bronze outputs:

```text
data/bronze/transfermarkt/
├── raw_html/squads/<url_hash>.html
├── raw_html/transfers/<url_hash>.html
├── raw_json/collected_pages.json
└── raw_json/ingestion_failures.json
```

Silver-ready outputs:

```text
data/silver/transfermarkt/
├── player_market_values.csv
├── player_market_values.json
├── transfers.csv
└── transfers.json
```

The parser tests use saved HTML fixtures under `tests/fixtures/transfermarkt`
and do not hit the live website.

## Development Status

This repository is currently at the initial scaffold stage. The next increments
will implement source ingestion, bronze storage contracts, dbt staging models,
warehouse marts, API endpoints, and dashboard views.

## Responsible Scraping

Transfermarkt scraping will be implemented with rate limiting, clear user-agent
configuration, retries, robots.txt awareness where applicable, and cached raw
responses to avoid unnecessary repeated requests.

## Security

Credentials and local paths must be supplied through environment variables or
cloud identity. Do not commit `.env`, service account keys, warehouse secrets,
or local data extracts.
