import os
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

from live import estimate_minute

load_dotenv()

URL = "https://api.football-data.org/v4/competitions/{code}/matches"
NOT_PLAYED = {"POSTPONED", "CANCELLED", "SUSPENDED"}


def fetch_matches(competition: str = "PL") -> list[dict]:
    token = os.getenv("FOOTBALL_DATA_TOKEN")
    if not token:
        raise ValueError("FOOTBALL_DATA_TOKEN manquant (fichier .env)")
    resp = requests.get(
        URL.format(code=competition),
        headers={"X-Auth-Token": token},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["matches"]


def _row(m: dict, kickoff: datetime, now: datetime) -> dict:
    full = (m.get("score") or {}).get("fullTime") or {}
    home, away = full.get("home"), full.get("away")
    score = "-" if home is None or away is None else f"{home} - {away}"

    status = m.get("status")
    if status in NOT_PLAYED:
        label = status.capitalize()
    else:
        label = estimate_minute(kickoff, m["id"], status=status, now=now)["label"]

    return {
        "Heure (UTC)": kickoff.strftime("%d/%m %H:%M"),
        "Domicile": m["homeTeam"].get("shortName") or m["homeTeam"].get("name"),
        "Score": score,
        "Extérieur": m["awayTeam"].get("shortName") or m["awayTeam"].get("name"),
        "Temps": label,
        "Statut API": status,
    }


def build_board(matches: list[dict], now: datetime | None = None):
    """Retourne (lignes, is_today). Matchs du jour, sinon les 5 prochains."""
    now = now or datetime.now(timezone.utc).replace(tzinfo=None)
    parsed = [(datetime.fromisoformat(m["utcDate"].replace("Z", "")), m) for m in matches]

    today = [(k, m) for k, m in parsed if k.date() == now.date()]
    if today:
        today.sort(key=lambda km: km[0])
        return [_row(m, k, now) for k, m in today], True

    upcoming = sorted((km for km in parsed if km[0] > now), key=lambda km: km[0])[:5]
    return [_row(m, k, now) for k, m in upcoming], False