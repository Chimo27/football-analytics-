from pathlib import Path

import duckdb
import streamlit as st

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "warehouse.duckdb"

st.set_page_config(page_title="Football Analytics", page_icon="⚽", layout="wide")


@st.cache_data(ttl=600)
def query(sql: str):
    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        return con.execute(sql).df()
    finally:
        con.close()


st.title("⚽ Football Analytics - Premier League")

# ---------- KPIs globaux ----------
kpi = query("""
    select
        count(*)                                              as matches,
        sum(total_goals)                                      as goals,
        round(avg(total_goals), 2)                            as avg_goals,
        round(100.0 * avg((winner = 'HOME_TEAM')::int), 1)    as home_win_pct,
        round(100.0 * avg((winner = 'DRAW')::int), 1)         as draw_pct,
        round(100.0 * avg((winner = 'AWAY_TEAM')::int), 1)    as away_win_pct
    from fct_match
    where status = 'FINISHED'
""").iloc[0]

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Matchs joués", int(kpi["matches"]))
c2.metric("Buts marqués", int(kpi["goals"]))
c3.metric("Buts / match", kpi["avg_goals"])
c4.metric("Victoires domicile", f"{kpi['home_win_pct']} %")
c5.metric("Matchs nuls", f"{kpi['draw_pct']} %")

# ---------- Classement ----------
st.subheader("Classement")
standings = query("""
    select
        row_number() over (order by sum(points) desc,
                                    sum(goal_diff) desc,
                                    sum(goals_for) desc)          as rang,
        t.team_name                                               as equipe,
        count(*)                                                  as j,
        sum((result = 'W')::int)                                  as v,
        sum((result = 'D')::int)                                  as n,
        sum((result = 'L')::int)                                  as d,
        sum(goals_for)                                            as bp,
        sum(goals_against)                                        as bc,
        sum(goal_diff)                                            as diff,
        sum(points)                                               as pts
    from fct_team_match f
    join dim_team t using (team_id)
    group by t.team_name
    order by rang
""")
st.dataframe(standings, hide_index=True, use_container_width=True)

# ---------- Analyse par équipe ----------
st.subheader("Analyse par équipe")
teams = standings["equipe"].tolist()
team = st.selectbox("Choisir une équipe", teams)

team_matches = query(f"""
    select
        f.match_date, f.matchday, f.is_home, o.team_name as adversaire,
        f.goals_for, f.goals_against, f.result, f.points
    from fct_team_match f
    join dim_team t using (team_id)
    join dim_team o on o.team_id = f.opponent_id
    where t.team_name = '{team.replace("'", "''")}'
    order by f.match_date
""")

last5 = team_matches.tail(5)["result"].tolist()
st.markdown("**Forme (5 derniers matchs) :** " + " ".join(last5))

d1, d2 = st.columns(2)
home = team_matches[team_matches["is_home"]]
away = team_matches[~team_matches["is_home"]]
d1.metric("Points à domicile", int(home["points"].sum()))
d2.metric("Points à l'extérieur", int(away["points"].sum()))

st.line_chart(
    team_matches.assign(points_cumules=team_matches["points"].cumsum())
    .set_index("match_date")["points_cumules"]
)
st.dataframe(team_matches, hide_index=True, use_container_width=True)