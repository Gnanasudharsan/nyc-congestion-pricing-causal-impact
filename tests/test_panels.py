"""Panel helpers used by the Phase 3 designs."""

from datetime import date

import numpy as np
import polars as pl
import pytest

from cordon.designs import panels, synth


def test_fill_missing_days_adds_zero_rows_between_first_and_last_date() -> None:
    daily = pl.DataFrame(
        {
            "date": [date(2024, 1, 1), date(2024, 1, 3), date(2024, 1, 2)],
            "zone": [1, 1, 2],
            "role": ["treated", "treated", "control"],
            "trips": [5, 7, 2],
        }
    )
    filled = panels.fill_missing_days(daily, "zone", "trips").sort("zone", "date")
    assert filled.height == 6  # 2 zones x 3 days
    zone1 = filled.filter(pl.col("zone") == 1)["trips"].to_list()
    assert zone1 == [5, 0, 7]


def test_two_way_imputation_recovers_additive_cells_and_keeps_observed_ones() -> None:
    rng = np.random.default_rng(0)
    truth = rng.normal(size=(30, 1)) + rng.normal(size=(1, 8))  # period + unit effects
    observed = truth.copy()
    holes = [(3, 1), (10, 5), (22, 7)]
    for i, j in holes:
        observed[i, j] = np.nan
    filled = panels.impute_two_way(observed)
    for i, j in holes:
        assert filled[i, j] == pytest.approx(truth[i, j], abs=1e-6)
    mask = ~np.isnan(observed)
    assert np.array_equal(filled[mask], observed[mask])


def test_study_windows_for_weekly_periods() -> None:
    weeks = [date(2024, 11, 4), date(2024, 11, 11), date(2025, 1, 6), date(2026, 1, 5)]
    masks = panels.study_windows(weeks, "week")
    assert masks.pre.tolist() == [True, False, False, False]
    assert masks.anticipation.tolist() == [False, True, False, False]
    assert masks.post_year1.tolist() == [False, False, True, False]
    assert masks.post_extended.tolist() == [False, False, False, True]


def test_nnls_weights_are_a_convex_combination() -> None:
    rng = np.random.default_rng(1)
    donors = rng.normal(size=(40, 6))
    target = donors @ np.array([0.6, 0.4, 0, 0, 0, 0])
    weights = synth.fit_weights(target, donors)
    assert weights.min() >= 0
    assert weights.sum() == pytest.approx(1.0)
    assert weights[:2] == pytest.approx([0.6, 0.4], abs=1e-4)
