{{ config(enabled=false) }}

select *
from {{ source('transfermarkt_silver', 'player_market_values') }}
