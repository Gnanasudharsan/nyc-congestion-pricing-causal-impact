from datetime import date, datetime

import polars as pl
import pytest

from cordon.features.calendar import build_calendar, study_period
from cordon.features.weather import daily_weather, wind_sector


def test_study_periods_match_adr_0007() -> None:
    assert study_period(date(2022, 12, 31)) == "before_study"
    assert study_period(date(2024, 11, 13)) == "pre"
    assert study_period(date(2024, 11, 14)) == "anticipation"
    assert study_period(date(2025, 1, 4)) == "anticipation"
    assert study_period(date(2025, 1, 5)) == "post_year1"
    assert study_period(date(2026, 1, 1)) == "post_extended"


def test_reference_window_is_exactly_bins_minus_two_and_minus_one() -> None:
    cal = build_calendar(date(2024, 9, 1), date(2025, 2, 10))
    reference = cal.filter(pl.col("is_reference_bin"))
    assert reference["date"].min() == date(2024, 9, 19)
    assert reference["date"].max() == date(2024, 11, 13)
    assert set(reference["event_bin_4wk"].to_list()) == {-2, -1}
    anticipation = cal.filter(pl.col("study_period") == "anticipation")
    assert anticipation["event_bin_4wk"].null_count() == anticipation.height
    first_post = cal.filter(pl.col("date") == date(2025, 1, 5))
    assert first_post["event_bin_4wk"].item() == 0


def test_holidays_and_holiday_weeks() -> None:
    cal = build_calendar(date(2024, 11, 25), date(2024, 12, 8))
    thanksgiving = cal.filter(pl.col("date") == date(2024, 11, 28))
    assert thanksgiving["is_federal_holiday"].item()
    same_week = cal.filter(pl.col("date") == date(2024, 11, 25))
    assert same_week["is_holiday_week"].item()
    next_week = cal.filter(pl.col("date") == date(2024, 12, 2))
    assert not next_week["is_holiday_week"].item()


@pytest.mark.parametrize(
    ("u", "v", "expected"),
    [(0.0, -10.0, "N"), (-10.0, 0.0, "E"), (0.0, 10.0, "S"), (10.0, 0.0, "W"), (7.0, 7.0, "SW")],
)
def test_wind_sector_uses_from_direction(u: float, v: float, expected: str) -> None:
    # (u, v) is the direction the wind blows TOWARD; sectors name where it comes FROM.
    assert wind_sector(u, v) == expected


def test_daily_weather_handles_dst_fall_back_day() -> None:
    # 2024-11-03 has 25 local hours; daily aggregation must keep them on one date.
    times = [datetime(2024, 11, 3, h % 24) for h in range(25)]
    hourly = pl.DataFrame(
        {
            "time": times,
            "temp_c": [10.0] * 25,
            "precip_mm": [0.1] * 25,
            "snow_cm": [0.0] * 25,
            "wind_kmh": [10.0] * 25,
            "wind_dir_deg": [270.0] * 25,
            "rh_pct": [50.0] * 25,
            "pbl_m": [500.0] * 25,
        }
    )
    daily = daily_weather(hourly)
    assert daily.height == 1
    assert daily["weather_hours"].item() == 25
    assert daily["precip_mm"].item() == pytest.approx(2.5)
    assert daily["wind_sector"].item() == "W"


def test_subway_chunks_never_cross_the_table_seam() -> None:
    from cordon.clean.subway import table_for, week_starts

    starts = week_starts(date(2024, 12, 20), date(2025, 1, 20))
    assert date(2025, 1, 1) in starts
    assert table_for(date(2024, 12, 31)) == "wujg-7c2s"
    assert table_for(date(2025, 1, 1)) == "5wq4-mkjj"
