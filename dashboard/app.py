from datetime import datetime
from pathlib import Path

import duckdb
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from live_feed import build_board, fetch_matches

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "warehouse.duckdb"
GREEN, YELLOW, RED, BLUE = "#00D26A", "#F5C542", "#FF5C5C", "#4C8DFF"

st.set_page_config(page_title="Football Analytics", page_icon="⚽", layout="wide")

st.markdown(
    """
<style>
.block-container {padding-top: 2rem; max-width: 1300px;}
#MainMenu, footer {visibility: hidden;}
[data-testid="stMetric"] {
    background: linear-gradient(145deg, #161B26, #1c2333);
    border: 1px solid #2a3350; border-radius: 16px;
    padding: 16px 20px; box-shadow: 0 4px 14px rgba(0,0,0,.25);
}
[data-testid="stMetricLabel"] {color: #8b95b0;}
[data-testid="stMetricValue"] {font-weight: 700;}
.hero {
    padding: 22px 28px; border-radius: 20px; margin-bottom: 18px;
    background: linear-gradient(120deg, #0f3d2e 0%, #12203a 60%, #1b1440 100%);
    border: 1px solid #2a3350;
}
.hero h1 {margin: 0; font-size: 2rem;}
.hero p {margin: 4px 0 0; color: #a9b4cf;}
.badge {
    display: inline-block; width: 26px; height: 26px; line-height: 26px;
    text-align: center; border-radius: 50%; font-weight: 700;
    font-size: .8rem; margin-right: 4px; color: #0b0f19;
}
.badge.W {background: #00d26a;} .badge.D {background: #f5c542;} .badge.L {background: #ff5c5c;}
</style>
""",
    unsafe_allow_html=True,
)


@st.cache_data(ttl=600)
def query(sql: str):
    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        return con.execute(sql).df()
    finally:
        con.close()


def style(fig, height=340):
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=height,
        margin=dict(l=10, r=10, t=50, b=10),
        legend=dict(orientation="h", y=-0.2),
    )
    return fig


# ---------- Data ----------
tm = query("""
    select t.team_name as team, o.team_name as opponent, f.match_date,
           f.matchday, f.is_home, f.goals_for, f.goals_against,
           f.goal_diff, f.result, f.points
    from fct_team_match f
    join dim_team t on t.team_id = f.team_id
    join dim_team o on o.team_id = f.opponent_id
    order by f.match_date, f.matchday
""")
matches = query("""
    select match_id, matchday, match_date, total_goals, winner
    from fct_match where status = 'FINISHED'
""")

try:
    updated = query("select max(ingested_at) as t from raw_matches")["t"].iloc[0]
    updated_txt = f"Data updated {updated:%d/%m/%Y %H:%M} UTC"
except Exception:
    updated_txt = ""

# ---------- Sidebar ----------
with st.sidebar:
    st.header("Filters")
    md_min, md_max = int(tm["matchday"].min()), int(tm["matchday"].max())
    if md_min < md_max:
        md_range = st.slider("Matchdays", md_min, md_max, (md_min, md_max))
    else:
        md_range = (md_min, md_max)
    st.caption(updated_txt)

tm_f = tm[tm["matchday"].between(*md_range)]
matches_f = matches[matches["matchday"].between(*md_range)]

st.markdown(
    f"""<div class="hero"><h1>⚽ Football Analytics</h1>
    <p>Premier League · matchdays {md_range[0]}–{md_range[1]} · {updated_txt}</p></div>""",
    unsafe_allow_html=True,
)


def build_standings(df):
    g = df.groupby("team")
    s = g.agg(
        J=("result", "size"),
        V=("result", lambda r: int((r == "W").sum())),
        N=("result", lambda r: int((r == "D").sum())),
        D=("result", lambda r: int((r == "L").sum())),
        BP=("goals_for", "sum"),
        BC=("goals_against", "sum"),
        Diff=("goal_diff", "sum"),
        Pts=("points", "sum"),
    ).reset_index()
    s = s.sort_values(["Pts", "Diff", "BP"], ascending=False).reset_index(drop=True)
    s.insert(0, "#", range(1, len(s) + 1))
    icons = {"W": "🟢", "D": "🟡", "L": "🔴"}
    s["Form"] = s["team"].map(
        lambda t: "".join(icons[r] for r in df[df["team"] == t].tail(5)["result"])
    )
    return s.rename(columns={"team": "Team"})


standings = build_standings(tm_f)

tab_over, tab_table, tab_team, tab_live = st.tabs(
    ["📊 Overview", "🏆 Standings", "🔎 Team analysis", "🔴 Live"]
)

# ---------- Overview ----------
with tab_over:
    n = len(matches_f)
    goals = int(matches_f["total_goals"].sum())
    pct = lambda w: round(100 * (matches_f["winner"] == w).mean(), 1) if n else 0

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Matches played", n)
    c2.metric("Goals scored", goals)
    c3.metric("Goals / match", round(goals / n, 2) if n else 0)
    c4.metric("Home wins", f"{pct('HOME_TEAM')} %")
    c5.metric("Draws", f"{pct('DRAW')} %")

    left, right = st.columns(2)
    with left:
        res = matches_f["winner"].value_counts().reindex(
            ["HOME_TEAM", "DRAW", "AWAY_TEAM"], fill_value=0
        )
        fig = go.Figure(go.Pie(
            labels=["Home win", "Draw", "Away win"], values=res.values, hole=0.6,
            marker=dict(colors=[GREEN, YELLOW, BLUE]),
        ))
        fig.update_layout(title="Match results")
        st.plotly_chart(style(fig), width="stretch")
    with right:
        per_md = matches_f.groupby("matchday")["total_goals"].mean().reset_index()
        fig = px.area(per_md, x="matchday", y="total_goals",
                      title="Average goals per matchday")
        fig.update_traces(line_color=GREEN, fillcolor="rgba(0,210,106,.18)")
        st.plotly_chart(style(fig), width="stretch")

    left, right = st.columns(2)
    with left:
        top_att = standings.nlargest(8, "BP").sort_values("BP")
        fig = px.bar(top_att, x="BP", y="Team", orientation="h",
                     title="Best attacks (goals scored)")
        fig.update_traces(marker_color=GREEN)
        st.plotly_chart(style(fig), width="stretch")
    with right:
        top_def = standings.nsmallest(8, "BC").sort_values("BC", ascending=False)
        fig = px.bar(top_def, x="BC", y="Team", orientation="h",
                     title="Best defences (goals conceded)")
        fig.update_traces(marker_color=BLUE)
        st.plotly_chart(style(fig), width="stretch")

# ---------- Standings ----------
with tab_table:
    st.dataframe(
        standings,
        hide_index=True,
        width="stretch",
        height=760,
        column_config={
            "Pts": st.column_config.ProgressColumn(
                "Pts", min_value=0, max_value=int(max(standings["Pts"].max(), 1)),
                format="%d",
            ),
            "Form": st.column_config.TextColumn("Last 5"),
        },
    )

# ---------- Team analysis ----------
with tab_team:
    team = st.selectbox("Choose a team", standings["Team"].tolist())
    t = tm_f[tm_f["team"] == team].sort_values("match_date").copy()
    row = standings[standings["Team"] == team].iloc[0]

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Rank", f"#{int(row['#'])}")
    m2.metric("Points", int(row["Pts"]))
    m3.metric("W - D - L", f"{row['V']} - {row['N']} - {row['D']}")
    m4.metric("Goals for : against", f"{row['BP']} : {row['BC']}")

    badges = "".join(
        f'<span class="badge {r}">{r}</span>' for r in t.tail(5)["result"]
    )
    st.markdown(f"**Last 5 matches**&nbsp;&nbsp;{badges}", unsafe_allow_html=True)

    t["cum_points"] = t["points"].cumsum()
    left, right = st.columns(2)
    with left:
        fig = px.line(t, x="matchday", y="cum_points", markers=True,
                      title="Cumulative points")
        fig.update_traces(line_color=GREEN)
        st.plotly_chart(style(fig), width="stretch")
    with right:
        fig = go.Figure()
        fig.add_bar(x=t["matchday"], y=t["goals_for"], name="Scored",
                    marker_color=GREEN)
        fig.add_bar(x=t["matchday"], y=t["goals_against"], name="Conceded",
                    marker_color=RED)
        fig.update_layout(barmode="group", title="Goals per match")
        st.plotly_chart(style(fig), width="stretch")

    ha = t.assign(venue=t["is_home"].map({True: "Home", False: "Away"}))
    ha = ha.groupby("venue").agg(points=("points", "sum")).reset_index()
    fig = px.bar(ha, x="venue", y="points", color="venue",
                 color_discrete_map={"Home": GREEN, "Away": BLUE},
                 title="Points: home vs away")
    fig.update_layout(showlegend=False)
    st.plotly_chart(style(fig, 280), width="stretch")

    shown = t.assign(venue=t["is_home"].map({True: "Home", False: "Away"}))
    shown = shown[["match_date", "matchday", "opponent", "venue",
                   "goals_for", "goals_against", "result"]]
    st.dataframe(shown.sort_values("match_date", ascending=False),
                 hide_index=True, width="stretch")

# ---------- Live ----------
@st.cache_data(ttl=60)
def load_live():
    return fetch_matches("PL")


@st.fragment(run_every=60)
def live_section():
    st.caption(
        "Free plan: delayed scores, estimated match minute (~). "
        f"Last refresh: {datetime.now().strftime('%H:%M:%S')}"
    )
    try:
        rows, is_today = build_board(load_live())
    except Exception as exc:
        st.warning(f"Live data unavailable: {exc}")
        return
    if not rows:
        st.info("No matches to display.")
        return
    if not is_today:
        st.info("No match today: here are the next ones.")
    st.dataframe(rows, hide_index=True, width="stretch")


with tab_live:
    live_section()