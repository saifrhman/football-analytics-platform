select *
from {{ source('statsbomb_silver', 'teams') }}
