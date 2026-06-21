from __future__ import annotations

from datetime import date

import pytest

from src.storage.reference_month import reference_month


@pytest.mark.parametrize(
    ("posted_at", "start_day", "expected"),
    [
        (date(2026, 6, 20), 1, "2026-06"),
        (date(2026, 6, 14), 15, "2026-05"),
        (date(2026, 6, 15), 15, "2026-06"),
        (date(2026, 6, 30), 15, "2026-06"),
        (date(2026, 7, 14), 15, "2026-06"),
        (date(2026, 1, 10), 15, "2025-12"),
        (date(2026, 12, 20), 15, "2026-12"),
        (date(2027, 1, 5), 15, "2026-12"),
        (date(2026, 2, 27), 28, "2026-01"),
        (date(2026, 2, 28), 31, "2026-02"),
    ],
)
def test_reference_month_respects_financial_month_start(
    posted_at: date,
    start_day: int,
    expected: str,
):
    assert reference_month(posted_at, start_day) == expected


def test_reference_month_accepts_iso_string_and_defaults_to_calendar_month():
    assert reference_month("2026-06-14") == "2026-06"
    assert reference_month("2026-06-14T10:30:00", 15) == "2026-05"
