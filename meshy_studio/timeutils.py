"""Time helpers. All human-facing times are rendered in US Pacific time."""
from __future__ import annotations

from datetime import datetime, timezone

try:
    from zoneinfo import ZoneInfo

    PACIFIC = ZoneInfo("America/Los_Angeles")
except Exception:  # pragma: no cover - zoneinfo data missing
    PACIFIC = timezone.utc

PACIFIC_TZ_NAME = "America/Los_Angeles"


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def to_pacific(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(PACIFIC)


def format_pacific(dt: datetime) -> str:
    """e.g. 'Sep 14, 2026, 1:05:09 PM PDT'."""
    return to_pacific(dt).strftime("%b %d, %Y, %-I:%M:%S %p %Z")


def iso_utc(dt: datetime | None = None) -> str:
    dt = dt or now_utc()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()
