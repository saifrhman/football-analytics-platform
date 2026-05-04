select *
from {{ source('statsbomb_silver', 'events') }}
