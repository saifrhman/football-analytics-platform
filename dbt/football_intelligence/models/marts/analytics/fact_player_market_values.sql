{{ config(enabled=false) }}

select
  player_id,
  valuation_date,
  market_value_eur
from {{ ref('stg_transfermarkt_player_market_values') }}
