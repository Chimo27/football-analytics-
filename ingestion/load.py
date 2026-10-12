from pathlib import Path

import duckdb

from ingestion.client import FootballDataClient, save_raw_snapshot
from ingestion.normalize import normalize_matches

DB_PATH = Path("data/warehouse.duckdb")

DDL = """
CREATE TABLE IF NOT EXISTS raw_competitions (
    competition_id BIGINT PRIMARY KEY,
    code VARCHAR, name VARCHAR, type VARCHAR
);
CREATE TABLE IF NOT EXISTS raw_teams (
    team_id BIGINT PRIMARY KEY,
    name VARCHAR, short_name VARCHAR, tla VARCHAR, crest VARCHAR
);
CREATE TABLE IF NOT EXISTS raw_matches (
    match_id BIGINT PRIMARY KEY,
    competition_code VARCHAR, season_id BIGINT, season_start DATE,
    matchday INTEGER, stage VARCHAR, status VARCHAR, utc_date TIMESTAMP,
    home_team_id BIGINT, away_team_id BIGINT, winner VARCHAR,
    home_goals INTEGER, away_goals INTEGER,
    ht_home_goals INTEGER, ht_away_goals INTEGER,
    ingested_at TIMESTAMP DEFAULT current_timestamp
);
"""


def upsert(con, table: str, rows: list[dict]):
    if not rows:
        return
    cols = list(rows[0].keys())
    placeholders = ", ".join("?" for _ in cols)
    sql = (
        f"INSERT OR REPLACE INTO {table} ({', '.join(cols)}) "
        f"VALUES ({placeholders})"
    )
    con.executemany(sql, [[r[c] for c in cols] for r in rows])


def run(competition: str = "PL"):
    client = FootballDataClient()
    payload = client.get_matches(competition)
    save_raw_snapshot(payload, f"{competition}_matches")  # snapshot

    data = normalize_matches(payload)

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DB_PATH))
    con.execute(DDL)
    upsert(con, "raw_competitions", data["competitions"])
    upsert(con, "raw_teams", data["teams"])
    upsert(con, "raw_matches", data["matches"])

    n = con.execute("SELECT count(*) FROM raw_matches").fetchone()[0]
    print(f"OK: {len(data['matches'])} matchs traités, {n} en base")
    con.close()


if __name__ == "__main__":
    run("PL")