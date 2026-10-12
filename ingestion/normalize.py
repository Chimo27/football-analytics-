def normalize_matches(payload: dict) -> dict:
    """Transforme le JSON de l'API en listes de lignes prêtes pour DuckDB."""
    comp = payload["competition"]
    competitions = [{
        "competition_id": comp["id"],
        "code": comp["code"],
        "name": comp["name"],
        "type": comp.get("type"),
    }]

    teams, matches = {}, []
    for m in payload["matches"]:
        for side in ("homeTeam", "awayTeam"):
            t = m[side]
            if t.get("id") is None:  # équipe pas encore connue (phases finales)
                continue
            teams[t["id"]] = {
                "team_id": t["id"],
                "name": t.get("name"),
                "short_name": t.get("shortName"),
                "tla": t.get("tla"),
                "crest": t.get("crest"),
            }

        score = m.get("score", {})
        full = score.get("fullTime", {}) or {}
        half = score.get("halfTime", {}) or {}
        season = m.get("season", {}) or {}

        matches.append({
            "match_id": m["id"],
            "competition_code": comp["code"],
            "season_id": season.get("id"),
            "season_start": season.get("startDate"),
            "matchday": m.get("matchday"),
            "stage": m.get("stage"),
            "status": m.get("status"),
            "utc_date": m["utcDate"].replace("Z", ""),
            "home_team_id": m["homeTeam"].get("id"),
            "away_team_id": m["awayTeam"].get("id"),
            "winner": score.get("winner"),
            "home_goals": full.get("home"),
            "away_goals": full.get("away"),
            "ht_home_goals": half.get("home"),
            "ht_away_goals": half.get("away"),
        })

    return {
        "competitions": competitions,
        "teams": list(teams.values()),
        "matches": matches,
    }