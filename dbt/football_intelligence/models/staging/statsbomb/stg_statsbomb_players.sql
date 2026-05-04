select *
from {{ source('statsbomb_silver', 'players') }}
