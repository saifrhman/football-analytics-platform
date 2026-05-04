# Pipeline Operating Guide

Run the safe StatsBomb sample pipeline first:

```bash
make ingest-statsbomb-sample
make transform-statsbomb-silver-sample
make load-statsbomb-bigquery
make dbt-run
make dbt-test
```

The sample ingestion target uses competition `2`, season `44`, and
`--match-limit 5` to keep local runs bounded.

Expected local outputs:

- bronze JSON under `data/bronze/statsbomb/open-data`
- silver CSV tables under `data/silver/statsbomb`

Expected warehouse outputs:

- silver tables in `BIGQUERY_DATASET_SILVER`
- gold dbt models in `BIGQUERY_DATASET_GOLD`

Use full ingestion only when larger-scale cloud or chunked processing is ready.
