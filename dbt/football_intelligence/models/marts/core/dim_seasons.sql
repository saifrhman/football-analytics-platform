select distinct
  season_id,
  season_name
from {{ ref('stg_statsbomb_competitions') }}
