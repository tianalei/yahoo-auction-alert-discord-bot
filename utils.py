"""Shared utility helpers."""

from datetime import datetime


def format_relative_updated(updated: datetime, now: datetime | None = None) -> str:
    """Format time since `updated` as a Chinese relative offset (floor at each tier)."""
    if now is None:
        now = datetime.now(updated.tzinfo) if updated.tzinfo else datetime.now()
    elif updated.tzinfo and now.tzinfo is None:
        now = now.replace(tzinfo=updated.tzinfo)
    elif now.tzinfo and updated.tzinfo is None:
        updated = updated.replace(tzinfo=now.tzinfo)

    delta = now - updated
    seconds = int(delta.total_seconds())
    if seconds < 0:
        seconds = 0

    if seconds < 60:
        return f"{seconds}s前"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}min前"
    hours = seconds // 3600
    if hours < 24:
        return f"{hours}h前"
    days = seconds // 86400
    if days < 30:
        return f"{days}天前"
    months = days // 30
    if months < 12:
        return f"{months}月前"
    years = months // 12
    return f"{years}年前"
