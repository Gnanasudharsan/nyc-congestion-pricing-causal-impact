"""Decide whether a dataset's date coverage supports a causal design.

Before/after, DiD, and synthetic control designs all need observations before
tolling began. This module turns raw coverage strings into a yes/no decision
with an explicit, documented threshold.
"""

from __future__ import annotations

from datetime import date

from cordon.config import TREATMENT_DATE

# Minimum pre-period for a causal design: one full year, so that every calendar
# week has at least one untreated observation for seasonal alignment.
MIN_PRE_PERIOD_DAYS = 365


def parse_coverage_date(value: str | int | None) -> date | None:
    """Parse the date formats we see in coverage fields.

    Handles ISO timestamps ("2019-01-01T00:00:00.000"), plain dates, year-month
    strings ("2023-01"), and bare years (2016 or "2016", read as January 1).
    """
    if value is None:
        return None
    text = str(value).strip()
    if text == "":
        return None
    if text.isdigit() and len(text) == 4:
        return date(int(text), 1, 1)
    text = text[:10]
    if len(text) == 7:
        text = f"{text}-01"
    return date.fromisoformat(text)


def pre_period_days(coverage_start: str | int | None) -> int:
    """Days of data available before the treatment date (0 if none)."""
    start = parse_coverage_date(coverage_start)
    if start is None:
        return 0
    return max((TREATMENT_DATE - start).days, 0)


def has_usable_pre_period(coverage_start: str | int | None) -> bool:
    """Return True if a dataset has at least MIN_PRE_PERIOD_DAYS before treatment."""
    return pre_period_days(coverage_start) >= MIN_PRE_PERIOD_DAYS
