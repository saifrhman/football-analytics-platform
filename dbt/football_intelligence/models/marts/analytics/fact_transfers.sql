{{ config(enabled=false) }}

select *
from {{ source('transfermarkt_silver', 'transfers') }}
