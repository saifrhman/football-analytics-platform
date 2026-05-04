# Architecture

The platform uses a medallion-style flow from source data to user-facing data
products.

## Medallion Layers

- Bronze stores source-faithful raw StatsBomb JSON under local object-style paths.
- Silver stores cleaned and normalized StatsBomb CSV tables before warehouse load.
- Gold stores dbt-built dimensional marts and analytics facts in BigQuery.

## Data Products

- FastAPI exposes curated BigQuery gold data as JSON.
- Streamlit visualizes xG, pass types, shot outcomes, pressures, and passers.

## Current Boundaries

Airflow and Terraform are scaffolding for future orchestration and cloud
provisioning. The verified end-to-end path currently runs through Python,
BigQuery, dbt, Streamlit, and FastAPI.
