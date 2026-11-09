import itertools
from datetime import date, timedelta

import numpy as np
import polars as pl
import pytest

from cordon.robustness import mde
from cordon.viz import descriptive


def _weekly_rows(gap_slope_per_year: float, noise: float = 0.0, seed: int = 0) -> pl.DataFrame:
    """Two groups of 3 units over the pre-period; treated gap grows linearly."""
    rng = np.random.default_rng(seed)
    weeks = [date(2023, 1, 2) + timedelta(weeks=i) for i in range(98)]
    rows = []
    for group in ("treated", "control"):
        for unit in range(3):
            for i, week in enumerate(weeks):
                seasonal = np.sin(i / 8)
                trend = gap_slope_per_year * (i * 7 / 365.25) if group == "treated" else 0.0
                value = 5 + unit + seasonal + trend + noise * rng.normal()
                rows.append(
                    {"period": week, "group": group, "unit": f"{group}{unit}", "value": value}
                )
    return pl.DataFrame(rows)


def test_pre_period_stats_recover_known_gap_trend() -> None:
    series = descriptive.group_series(_weekly_rows(gap_slope_per_year=0.5))
    stats = descriptive.pre_period_stats(series, "week")
    assert stats["gap_slope_per_year"] == pytest.approx(0.5, abs=1e-6)
    assert stats["correlation"] > 0.9


def test_group_series_removes_unit_levels() -> None:
    series = descriptive.group_series(_weekly_rows(gap_slope_per_year=0.0))
    gap = series.pivot(on="group", index="period", values="value")
    assert np.allclose(gap["treated"].to_numpy(), gap["control"].to_numpy())


def test_sc_proxy_is_zero_without_effect_and_recovers_a_step() -> None:
    rows = _weekly_rows(gap_slope_per_year=0.0)
    placebo = date(2024, 1, 7)
    assert mde.sc_proxy_estimate(rows, placebo) == pytest.approx(0.0, abs=1e-9)
    stepped = rows.with_columns(
        pl.when((pl.col("group") == "treated") & (pl.col("period") >= placebo))
        .then(pl.col("value") - 2.0)
        .otherwise(pl.col("value"))
        .alias("value")
    )
    assert mde.sc_proxy_estimate(stepped, placebo) == pytest.approx(-2.0, rel=0.05)


def test_placebo_dates_are_inside_the_pre_period_with_room_on_both_sides() -> None:
    dates = mde.placebo_dates()
    assert dates[0] == date(2023, 7, 2)
    assert dates[-1] <= date(2024, 6, 30)
    assert all((b - a).days == 28 for a, b in itertools.pairwise(dates))


def test_to_weekly_requires_five_days() -> None:
    days = [date(2024, 1, 1) + timedelta(days=i) for i in range(11)]  # Mon..Thu next week
    rows = pl.DataFrame(
        {"period": days, "group": "treated", "unit": "u", "value": [1.0] * len(days)}
    )
    weekly = descriptive.to_weekly(rows)
    assert weekly["period"].to_list() == [date(2024, 1, 1)]
