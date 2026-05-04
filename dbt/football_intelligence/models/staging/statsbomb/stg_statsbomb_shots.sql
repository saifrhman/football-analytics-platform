select *
from {{ source('statsbomb_silver', 'shots') }}
