import random
from datetime import datetime, timezone

HALF = 45          # durée d'une mi-temps (minutes)
BREAK = 15         # pause entre les mi-temps
MAX_STOPPAGE = 5   # temps additionnel max par mi-temps


def _stoppage(match_id: int, half: int) -> int:
    """Temps additionnel pseudo-aléatoire mais stable pour un match donné."""
    return random.Random(f"{match_id}-{half}").randint(0, MAX_STOPPAGE)


def estimate_minute(kickoff_utc: datetime, match_id: int,
                    status: str | None = None,
                    now: datetime | None = None) -> dict:
    """Estime la minute de jeu. kickoff_utc et now sont en UTC, sans fuseau."""
    if status == "FINISHED":
        return {"phase": "FT", "label": "Terminé"}
    if status == "PAUSED":
        return {"phase": "HT", "label": "Mi-temps"}

    now = now or datetime.now(timezone.utc).replace(tzinfo=None)
    elapsed = (now - kickoff_utc).total_seconds() / 60

    if elapsed < 0:
        return {"phase": "NS", "label": "À venir"}

    s1 = _stoppage(match_id, 1)
    s2 = _stoppage(match_id, 2)
    end_h1 = HALF + s1
    start_h2 = end_h1 + BREAK
    end_h2 = start_h2 + HALF + s2

    if elapsed < HALF:
        return {"phase": "H1", "label": f"~{int(elapsed) + 1}'"}
    if elapsed < end_h1:
        return {"phase": "H1", "label": f"~45+{int(elapsed - HALF) + 1}'"}
    if elapsed < start_h2:
        return {"phase": "HT", "label": "Mi-temps"}
    if elapsed < start_h2 + HALF:
        return {"phase": "H2", "label": f"~{HALF + int(elapsed - start_h2) + 1}'"}
    if elapsed < end_h2:
        return {"phase": "H2", "label": f"~90+{int(elapsed - start_h2 - HALF) + 1}'"}
    return {"phase": "FT?", "label": "Fin imminente"}