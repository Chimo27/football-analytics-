from datetime import datetime, timedelta

from dashboard.live import estimate_minute

KICKOFF = datetime(2026, 10, 12, 15, 0)


def at(minutes):
    return estimate_minute(KICKOFF, match_id=123, now=KICKOFF + timedelta(minutes=minutes))


def test_before_kickoff():
    assert at(-5)["phase"] == "NS"


def test_first_half():
    assert at(10)["label"] == "~11'"


def test_second_half_starts_after_break():
    assert at(70)["phase"] == "H2"


def test_status_has_priority():
    assert estimate_minute(KICKOFF, 123, status="FINISHED")["label"] == "Terminé"
    assert estimate_minute(KICKOFF, 123, status="PAUSED")["label"] == "Mi-temps"


def test_stable_between_calls():
    assert at(46) == at(46)