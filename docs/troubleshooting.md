# Troubleshooting

## Missing environment variables

Copy `.env.example` to `.env` and set `GCP_PROJECT_ID`,
`BIGQUERY_DATASET_SILVER`, `BIGQUERY_DATASET_GOLD`, and `GCP_REGION`.

## GCP authentication errors

Use Google Application Default Credentials locally:

```bash
gcloud auth application-default login
```

If you use a service account key, keep it outside Git and set
`GOOGLE_APPLICATION_CREDENTIALS` to the local path.

## dbt errors

Run `make dbt-parse` first. If `dbt run` or `dbt test` fails, include the dbt
command output and compiled SQL when opening an issue.

## BigQuery query errors

Check that silver tables were loaded, dbt gold models were built, and your user
or service account has dataset access. Include the BigQuery job ID if available.
