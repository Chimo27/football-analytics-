with finished as (
    select * from {{ ref('stg_matches') }}
    where status = 'FINISHED'
),

home as (
    select
        cast(match_id as varchar) || '_home' as team_match_id,
        match_id, match_date, competition_code, season_id, matchday,
        home_team_id as team_id,
        away_team_id as opponent_id,
        true as is_home,
        home_goals as goals_for,
        away_goals as goals_against
    from finished
),

away as (
    select
        cast(match_id as varchar) || '_away' as team_match_id,
        match_id, match_date, competition_code, season_id, matchday,
        away_team_id as team_id,
        home_team_id as opponent_id,
        false as is_home,
        away_goals as goals_for,
        home_goals as goals_against
    from finished
),

unioned as (
    select * from home
    union all
    select * from away
)

select
    *,
    goals_for - goals_against as goal_diff,
    case
        when goals_for > goals_against then 'W'
        when goals_for = goals_against then 'D'
        else 'L'
    end as result,
    case
        when goals_for > goals_against then 3
        when goals_for = goals_against then 1
        else 0
    end as points
from unioned