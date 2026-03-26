from __future__ import annotations

from datetime import UTC, datetime


def now_utc() -> datetime:
    """
    Return the current timezone-aware UTC datetime.
    """
    return datetime.now(UTC)


def to_utc(value: datetime) -> datetime:
    """
    Normalize a datetime to timezone-aware UTC.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def to_zulu_timestamp(value: datetime) -> str:
    """
    Convert datetime to ISO-8601 UTC Zulu format.
    Example: 2026-03-10T18:25:00Z
    """
    return to_utc(value).strftime("%Y-%m-%dT%H:%M:%SZ")
