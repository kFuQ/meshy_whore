"""Time helpers. All human-facing times are rendered in the user's local
time zone (the machine's configured zone)."""
from __future__ import annotations

from datetime import datetime, timezone


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def to_local(dt: datetime) -> datetime:
    """Convert an aware/naive datetime to the machine's local time zone."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    # astimezone() with no argument targets the local zone.
    return dt.astimezone()


def format_local(dt: datetime) -> str:
    """e.g. 'Sep 14, 2026, 1:05:09 PM PDT' in the user's local zone."""
    local = to_local(dt)
    # %Z resolves to the local zone abbreviation; strip padding on the hour.
    try:
        return local.strftime("%b %d, %Y, %-I:%M:%S %p %Z").strip()
    except ValueError:
        # %-I is not portable on every platform (e.g. Windows); fall back.
        return local.strftime("%b %d, %Y, %I:%M:%S %p %Z").strip()


def iso_utc(dt: datetime | None = None) -> str:
    dt = dt or now_utc()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()
