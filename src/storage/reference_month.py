from __future__ import annotations

from datetime import date


def reference_month(posted_at: date | str, start_day: int = 1) -> str:
    """Return the financial reference month for a transaction date.

    The financial month starts on `start_day`, clamped to 1..28 to avoid
    ambiguous cycles in February.
    """
    value = date.fromisoformat(posted_at[:10]) if isinstance(posted_at, str) else posted_at
    day = min(max(int(start_day), 1), 28)
    year = value.year
    month = value.month

    if value.day < day:
        month -= 1
        if month == 0:
            month = 12
            year -= 1

    return f"{year:04d}-{month:02d}"
