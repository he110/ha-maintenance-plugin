import datetime as dt
import importlib.util
import pathlib
import sys
from zoneinfo import ZoneInfo

_spec = importlib.util.spec_from_file_location(
    "schedule",
    pathlib.Path(__file__).resolve().parents[2] / "custom_components" / "maintainable" / "schedule.py",
)
schedule = importlib.util.module_from_spec(_spec)
sys.modules["schedule"] = schedule  # dataclasses look the module up
_spec.loader.exec_module(schedule)

MSK = ZoneInfo("Europe/Moscow")
TODAY = dt.date(2026, 9, 21)


def at(day: dt.date, hour: int = 12) -> dt.datetime:
    return dt.datetime(day.year, day.month, day.day, hour, tzinfo=MSK)


def test_thresholds_match_1x():
    # interval 30, threshold 7 — the fixed rules of 1.x.
    cases = {
        0: ("ok", 30),
        22: ("ok", 8),
        23: ("due", 7),
        30: ("due", 0),
        31: ("overdue", -1),
    }
    for ago, (status, days) in cases.items():
        result = schedule.compute(at(TODAY - dt.timedelta(days=ago)), 30, 7, TODAY, MSK)
        assert (result.status, result.days_until) == (status, days), ago


def test_threshold_is_configurable():
    result = schedule.compute(at(TODAY - dt.timedelta(days=16)), 30, 14, TODAY, MSK)
    assert (result.status, result.days_until) == ("due", 14)


def test_naive_legacy_value_is_local_time():
    parsed = schedule.parse_stored("2026-08-06T16:36:46.197676", MSK)
    assert parsed.tzinfo is MSK and parsed.hour == 16


def test_aware_value_kept():
    parsed = schedule.parse_stored("2026-08-06T16:36:46+00:00", MSK)
    assert parsed.utcoffset() == dt.timedelta(0)


def test_days_counted_in_local_dates():
    # Late evening in Moscow: the calendar day is Moscow's, not UTC's.
    last = dt.datetime(2026, 8, 22, 23, 30, tzinfo=MSK)
    result = schedule.compute(last, 30, 7, TODAY, MSK)
    assert result.next.astimezone(MSK).date() == dt.date(2026, 9, 21)
    assert result.days_until == 0
