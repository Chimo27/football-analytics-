select
    team_id,
    name as team_name,
    short_name,
    tla,
    crest as crest_url
from {{ source('raw', 'raw_teams') }}