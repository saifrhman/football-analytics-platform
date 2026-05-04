select *
from {{ source('statsbomb_silver', 'passes') }}
