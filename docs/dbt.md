# dbt Notes

The dbt project lives under `dbt/football_intelligence`.

Useful commands from the repository root:

```bash
make dbt-parse
make dbt-run
make dbt-test
make dbt-docs-generate
```

Serve generated dbt docs locally:

```bash
cd dbt/football_intelligence
dbt docs serve
```

Active gold models include `dim_competitions`, `dim_matches`, `dim_players`,
`dim_seasons`, `dim_teams`, `fact_events`, `fact_passes`, `fact_pressures`,
and `fact_shots`.

Transfermarkt dbt models are disabled until Transfermarkt silver tables are
loaded.
