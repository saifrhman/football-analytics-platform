select *
from {{ source('statsbomb_silver', 'competitions') }}
