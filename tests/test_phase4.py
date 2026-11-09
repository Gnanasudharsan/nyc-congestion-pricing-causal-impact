"""Phase 4 estimators on simulated data with known effects."""

import numpy as np
import pytest

from cordon.designs import did, heterogeneity, zone_effects
from test_designs import simulated_panel  # tests/ is on pythonpath (pyproject)


def test_stacked_cut_recovers_level_effects_and_their_difference() -> None:
    peak = simulated_panel(effect=-0.10, n_treated=15, n_control=20, seed=31)
    overnight = simulated_panel(effect=-0.03, n_treated=15, n_control=20, seed=32)
    rows = heterogeneity.stack({"peak": peak, "overnight": overnight})
    levels = ["peak", "overnight"]
    per_level = did.fit(heterogeneity.stacked_design(rows, levels, "day", "per_level"))
    assert per_level.value("post_year1:peak") == pytest.approx(-0.10, abs=0.01)
    assert per_level.value("post_year1:overnight") == pytest.approx(-0.03, abs=0.01)
    difference = did.fit(heterogeneity.stacked_design(rows, levels, "day", "difference"))
    assert difference.value("post_year1:overnight-peak") == pytest.approx(0.07, abs=0.012)
    # Same model, two parametrisations: the difference equals the gap in level effects.
    gap = per_level.value("post_year1:overnight") - per_level.value("post_year1:peak")
    assert difference.value("post_year1:overnight-peak") == pytest.approx(gap, abs=1e-8)
    assert per_level.n_clusters == 35  # clustered by the original unit, not unit|level


def test_shrinkage_pulls_noisy_estimates_towards_the_mean() -> None:
    rng = np.random.default_rng(4)
    truth = rng.normal(-0.05, 0.02, 60)
    sds = np.where(np.arange(60) < 30, 0.005, 0.08)  # half precise, half noisy
    estimates = truth + rng.normal(0, sds)
    shrunk, mu, tau2 = zone_effects.shrink(estimates, sds)
    assert mu == pytest.approx(-0.05, abs=0.01)
    assert tau2 == pytest.approx(0.02**2, rel=0.6)
    noisy = slice(30, 60)
    assert np.mean((shrunk[noisy] - truth[noisy]) ** 2) < np.mean(
        (estimates[noisy] - truth[noisy]) ** 2
    )
    assert np.allclose(shrunk[:30], estimates[:30], atol=0.003)  # precise ones barely move


def test_weighted_correlation_matches_unweighted_with_equal_weights() -> None:
    rng = np.random.default_rng(2)
    x, y = rng.normal(size=50), rng.normal(size=50)
    assert zone_effects.weighted_correlation(x, y, np.ones(50)) == pytest.approx(
        np.corrcoef(x, y)[0, 1]
    )
