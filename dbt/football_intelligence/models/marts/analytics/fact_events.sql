select *
from {{ ref('stg_statsbomb_events') }}
