"""Phase 5 pass rules and breakdown logic (deviation 18)."""

import polars as pl

from cordon.robustness import checks


def test_placebo_passes_when_interval_includes_zero_or_effect_is_small() -> None:
    many = {"n_clusters": 100, "p_value": 0.5}
    assert checks.placebo_passes({**many, "estimate": -0.08, "ci_low": -0.1, "ci_high": 0.01}, -0.1)
    assert checks.placebo_passes(
        {**many, "estimate": -0.02, "ci_low": -0.03, "ci_high": -0.01}, -0.1
    )  # significant but under half the primary
    assert not checks.placebo_passes(
        {**many, "estimate": -0.08, "ci_low": -0.1, "ci_high": -0.06}, -0.1
    )
    few = {"n_clusters": 7, "ci_low": -0.1, "ci_high": -0.06, "estimate": -0.08}
    assert checks.placebo_passes({**few, "p_value": 0.2}, -0.1)  # bootstrap p decides
    assert not checks.placebo_passes({**few, "p_value": 0.01}, -0.1)


def test_breakdown_is_the_smallest_mbar_whose_interval_includes_zero() -> None:
    bounds = pl.DataFrame(
        {
            "key": ["X"] * 4,
            "restriction": ["relative_magnitudes"] * 4,
            "parameter": [0.5, 1.0, 1.5, 2.0],
            "lb": [-0.2, -0.15, -0.1, -0.05],
            "ub": [-0.05, -0.01, 0.02, 0.06],
        }
    )
    label, excludes_at_one = checks.breakdown(bounds, "X")
    assert label == "1-1.5"
    assert excludes_at_one is True
    none = bounds.with_columns(pl.lit(None, dtype=pl.Float64).alias("lb"))
    assert checks.breakdown(none, "X") == ("not computed", None)
    first = bounds.with_columns(pl.lit(-1.0).alias("lb"), pl.lit(1.0).alias("ub"))
    assert checks.breakdown(first, "X") == ("<= 0.5", False)
