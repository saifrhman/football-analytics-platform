# Data Model

The verified warehouse path is StatsBomb silver to dbt gold.

## Active Gold Dimensions

- `dim_competitions`
- `dim_matches`
- `dim_players`
- `dim_seasons`
- `dim_teams`

## Active Gold Facts

- `fact_events`
- `fact_shots`
- `fact_passes`
- `fact_pressures`

## Supporting Views

- `stg_statsbomb_competitions`
- `stg_statsbomb_events`
- `stg_statsbomb_matches`
- `stg_statsbomb_passes`
- `stg_statsbomb_players`
- `stg_statsbomb_pressures`
- `stg_statsbomb_shots`
- `stg_statsbomb_teams`
- `stg_statsbomb_three_sixty_freeze_frames`
- `int_events_enriched`

## Disabled Until Transfermarkt Silver Loads Exist

- `stg_transfermarkt_player_market_values`
- `fact_player_market_values`
- `fact_transfers`
