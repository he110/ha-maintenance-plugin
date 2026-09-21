"""Maintenance schedule arithmetic. No Home Assistant imports — unit-testable."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

STATUS_OK = "ok"
STATUS_DUE = "due"
STATUS_OVERDUE = "overdue"


@dataclass(frozen=True)
class Schedule:
    last: dt.datetime  # timezone-aware
    next: dt.datetime  # timezone-aware
    days_until: int  # negative when overdue
    status: str


def parse_stored(value: str, tz: dt.tzinfo) -> dt.datetime:
    """Read a stored timestamp.

    Version 1.x stored naive ISO strings (`datetime.now().isoformat()`); they are read as
    local time. Newer versions store timezone-aware strings.
    """
    parsed = dt.datetime.fromisoformat(value)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=tz)


def compute(
    last: dt.datetime, interval_days: int, due_threshold: int, today: dt.date, tz: dt.tzinfo
) -> Schedule:
    """Same rules as 1.x: overdue below zero days, due within the threshold (inclusive)."""
    next_ = last + dt.timedelta(days=interval_days)
    days_until = (next_.astimezone(tz).date() - today).days
    if days_until < 0:
        status = STATUS_OVERDUE
    elif days_until <= due_threshold:
        status = STATUS_DUE
    else:
        status = STATUS_OK
    return Schedule(last=last, next=next_, days_until=days_until, status=status)
