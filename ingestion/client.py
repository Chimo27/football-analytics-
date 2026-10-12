import json
import os
import time
from datetime import date
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://api.football-data.org/v4"
MIN_INTERVAL = 6.5  # secondes entre 2 appels (plan gratuit : 10 requêtes/min)
MAX_RETRIES = 4
RAW_DIR = Path("data/raw")


class FootballDataClient:
    def __init__(self, token: str | None = None):
        self.token = token or os.getenv("FOOTBALL_DATA_TOKEN")
        if not self.token:
            raise ValueError("FOOTBALL_DATA_TOKEN manquant (fichier .env)")
        self.session = requests.Session()
        self.session.headers.update({"X-Auth-Token": self.token})
        self._last_call = 0.0

    def _wait_for_slot(self):
        elapsed = time.time() - self._last_call
        if elapsed < MIN_INTERVAL:
            time.sleep(MIN_INTERVAL - elapsed)
        self._last_call = time.time()

    def get(self, path: str, params: dict | None = None) -> dict:
        url = f"{BASE_URL}{path}"
        for attempt in range(1, MAX_RETRIES + 1):
            self._wait_for_slot()
            try:
                resp = self.session.get(url, params=params, timeout=30)
            except requests.RequestException as exc:
                wait = 2 ** attempt
                print(f"[retry {attempt}] erreur réseau: {exc} -> attente {wait}s")
                time.sleep(wait)
                continue

            if resp.status_code == 200:
                return resp.json()

            if resp.status_code == 429:  # trop de requêtes
                wait = int(resp.headers.get("Retry-After", 60))
                print(f"[retry {attempt}] 429 -> attente {wait}s")
                time.sleep(wait)
                continue

            if resp.status_code >= 500:
                wait = 2 ** attempt
                print(f"[retry {attempt}] {resp.status_code} -> attente {wait}s")
                time.sleep(wait)
                continue

            # 400 / 403 / 404 : inutile de réessayer
            raise RuntimeError(f"{resp.status_code} sur {url}: {resp.text[:200]}")

        raise RuntimeError(f"Échec après {MAX_RETRIES} tentatives: {url}")

    def get_matches(self, competition: str, season: int | None = None) -> dict:
        params = {"season": season} if season else None
        return self.get(f"/competitions/{competition}/matches", params)


def save_raw_snapshot(data: dict, name: str) -> Path:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    path = RAW_DIR / f"{name}_{date.today().isoformat()}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


if __name__ == "__main__":
    client = FootballDataClient()
    data = client.get_matches("PL")
    path = save_raw_snapshot(data, "PL_matches")
    print(f"{len(data.get('matches', []))} matchs sauvegardés dans {path}")