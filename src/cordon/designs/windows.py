"""Study windows and event-time bins for daily, weekly, and monthly periods (ADR 0007).

Daily periods use the calendar definitions in ``cordon.features.calendar``.

Weekly periods are labelled by the Monday that starts the week:
- **pre:** the week ends before the anticipation window starts (2024-11-14);
- **post:** the week starts on or after the treatment date (2025-01-05);
- **anticipation:** anything in between, including the week of 2024-12-30, which is
  mostly before tolling.

Monthly periods follow the analysis plan:
- **pre:** Jan 2023 to Oct 2024;
- **anticipation:** Nov to Dec 2024;
- **post, year 1:** 2025;
- **post, extended:** 2026 onward.

**Event bins:**
- Daily: 4-week bins counted back from the anticipation start and forward from the
  treatment date. Bins -2 and -1 together are the 8-week reference period.
- Monthly: months counted the same way. Sep and Oct 2024 (bins -2 and -1) are the
  reference period, the monthly counterpart of the daily reference window.

**Extended window, daily data:** 2026-01-01 to 2026-01-03 is dropped, so the extended
post-period starts exactly at the 2026-01-04 fare and toll change.
"""

from __future__ import annotations

from datetime import date, timedelta

from cordon.features.calendar import ANTICIPATION_START, PRE_START, TREATMENT, YEAR1_END

EXTENDED_START = date(2026, 1, 4)  # MTA fare and toll increase (level shift)
REFERENCE_BINS = (-2, -1)
FREQUENCIES = ("day", "week", "month")


def window_of(period: date, frequency: str) -> str:
    """One of before_study, pre, anticipation, post_year1, gap, post_extended."""
    if frequency == "day":
        start, end = period, period
    elif frequency == "week":
        start, end = period, period + timedelta(days=6)
    elif frequency == "month":
        start = period.replace(day=1)
        end = (start.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    else:
        raise ValueError(f"unknown frequency {frequency}")
    if start < PRE_START:
        return "before_study"
    if end < ANTICIPATION_START:
        return "pre"
    if frequency == "month":
        if start < TREATMENT.replace(day=1):
            return "anticipation"
        return "post_year1" if start <= YEAR1_END else "post_extended"
    if start < TREATMENT:
        return "anticipation"
    if start <= YEAR1_END:
        return "post_year1"
    if frequency == "day" and start < EXTENDED_START:
        return "gap"
    return "post_extended"


def months_between(earlier: date, later: date) -> int:
    """Whole months from earlier to later (both taken at the first of the month)."""
    return (later.year - earlier.year) * 12 + (later.month - earlier.month)


def event_bin(period: date, frequency: str) -> int | None:
    """Event-time bin, or None inside the anticipation window."""
    window = window_of(period, frequency)
    if window == "anticipation":
        return None
    if frequency == "day":
        if window == "pre":
            return (period - ANTICIPATION_START).days // 28
        return (period - TREATMENT).days // 28
    if frequency == "month":
        if window == "pre":
            return months_between(ANTICIPATION_START.replace(day=1), period)
        return months_between(TREATMENT.replace(day=1), period)
    raise ValueError("event bins are defined for daily and monthly data only")


def years_since_start(period: date) -> float:
    """Time in years since 2023-01-01, the regressor for linear trends."""
    return (period - PRE_START).days / 365.25
