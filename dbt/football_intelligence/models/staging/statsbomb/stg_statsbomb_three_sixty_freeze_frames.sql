select *
from {{ source('statsbomb_silver', 'three_sixty_freeze_frames') }}
