select
    match_id,
    competition_code,
    season_id,
    season_start,
    matchday,
    stage,
    status,
    utc_date,
    cast(utc_date as date) as match_date,
    home_team_id,
    away_team_id,
    winner,
    home_goals,
    away_goals,
    ht_home_goals,
    ht_away_goals
from {{ source('raw', 'raw_matches') }}