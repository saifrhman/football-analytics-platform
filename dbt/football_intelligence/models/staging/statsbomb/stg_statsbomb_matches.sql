select *
from {{ source('statsbomb_silver', 'matches') }}
