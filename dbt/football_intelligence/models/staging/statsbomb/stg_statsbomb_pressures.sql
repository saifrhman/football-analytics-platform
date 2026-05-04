select *
from {{ source('statsbomb_silver', 'pressures') }}
