select
    match_id,
    competition_code,
    season_id,
    matchday,
    stage,
    status,
    match_date,
    utc_date,
    home_team_id,
    away_team_id,
    home_goals,
    away_goals,
    home_goals + away_goals as total_goals,
    ht_home_goals,
    ht_away_goals,
    winner
from {{ ref('stg_matches') }}