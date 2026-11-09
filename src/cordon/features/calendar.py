"""Daily calendar features: day of week, ISO week, holidays, study periods.

Holidays come from the ``holidays`` package (US federal plus New York State
observances). Study-period labels follow ADR 0007.
"""

from __future__ import annotations

from datetime import date

import holidays
import polars as pl

PRE_START = date(2023, 1, 1)
ANTICIPATION_START = date(2024, 11, 14)
TREATMENT = date(2025, 1, 5)
YEAR1_END = date(2025, 12, 31)
REFERENCE_START = date(2024, 9, 19)


def study_period(day: date) -> str:
    """Label a day as pre, anticipation, post_year1, post_extended, or before_study."""
    if day < PRE_START:
        return "before_study"
    if day < ANTICIPATION_START:
        return "pre"
    if day < TREATMENT:
        return "anticipation"
    if day <= YEAR1_END:
        return "post_year1"
    return "post_extended"


def build_calendar(start: date, end: date) -> pl.DataFrame:
    """One row per day from start to end inclusive."""
    years = range(start.year, end.year + 1)
    federal = holidays.country_holidays("US", years=years)
    new_york = holidays.country_holidays("US", subdiv="NY", years=years)

    days = pl.date_range(start, end, interval="1d", eager=True).alias("date")
    frame = pl.DataFrame({"date": days})
    frame = frame.with_columns(
        pl.col("date").dt.weekday().alias("day_of_week"),  # 1 = Monday ... 7 = Sunday
        pl.col("date").dt.week().alias("iso_week"),
        pl.col("date").dt.iso_year().alias("iso_year"),
        pl.col("date").dt.month().alias("month"),
        pl.col("date").dt.year().alias("year"),
        pl.col("date")
        .map_elements(lambda d: d in federal, return_dtype=pl.Boolean)
        .alias("is_federal_holiday"),
        pl.col("date")
        .map_elements(lambda d: d in new_york, return_dtype=pl.Boolean)
        .alias("is_ny_holiday"),
        pl.col("date").map_elements(study_period, return_dtype=pl.Utf8).alias("study_period"),
        (pl.col("date") >= REFERENCE_START)
        .and_(pl.col("date") < ANTICIPATION_START)
        .alias("is_reference_bin"),
    )
    frame = frame.with_columns(
        (pl.col("day_of_week") >= 6).alias("is_weekend"),
        # A week is a "holiday week" if any day in its ISO week is a NY holiday.
        pl.col("is_ny_holiday").any().over(["iso_year", "iso_week"]).alias("is_holiday_week"),
        # Days since treatment (negative before), used for event-study binning.
        (pl.col("date") - pl.lit(TREATMENT)).dt.total_days().alias("days_from_treatment"),
    )
    days_from_anticipation = (pl.col("date") - pl.lit(ANTICIPATION_START)).dt.total_days()
    return frame.with_columns(
        # 4-week event-study bins (ADR 0007). Pre-period bins count back from the start of
        # the anticipation window, so the 8-week reference period is exactly bins -2 and -1.
        # Post-period bins count forward from the treatment date (bin 0 = first 28 days).
        # The anticipation window has no numeric bin (null); it is estimated as its own term.
        pl.when(pl.col("date") < ANTICIPATION_START)
        .then(days_from_anticipation.floordiv(28))
        .when(pl.col("date") >= TREATMENT)
        .then(pl.col("days_from_treatment").floordiv(28))
        .otherwise(None)
        .alias("event_bin_4wk"),
    )
