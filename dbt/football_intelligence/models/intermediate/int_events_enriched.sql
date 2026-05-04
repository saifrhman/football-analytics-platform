select
  event_id,
  match_id,
  player_id,
  team_id,
  event_type,
  event_timestamp
from {{ ref('stg_statsbomb_events') }}
