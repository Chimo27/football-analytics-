import duckdb

con = duckdb.connect("data/warehouse.duckdb", read_only=True)
rows = con.execute("""
    select t.team_name, count(*) as played, sum(points) as pts, sum(goal_diff) as gd
    from fct_team_match f
    join dim_team t using (team_id)
    group by 1
    order by pts desc, gd desc
    limit 10
""").fetchall()

print(f"{'Équipe':30} {'J':>3} {'Pts':>4} {'Diff':>5}")
for name, played, pts, gd in rows:
    print(f"{name:30} {played:>3} {pts:>4} {gd:>5}")