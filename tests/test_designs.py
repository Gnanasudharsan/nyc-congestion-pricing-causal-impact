"""Estimators tested on simulated data with known effects (Phase 3 requirement)."""

from datetime import date, timedelta

import numpy as np
import polars as pl
import pytest

from cordon.designs import did, multiple, specs, synth, windows
from cordon.designs.fixed_effects import demean, encode

TRUE_EFFECT = -0.10


def simulated_panel(
    effect: float = TRUE_EFFECT,
    treated_trend: float = 0.0,
    n_treated: int = 6,
    n_control: int = 10,
    noise: float = 0.05,
    seed: int = 7,
) -> pl.DataFrame:
    """Daily log outcome with unit x week-of-year seasonality, common shocks, a step effect.

    ``treated_trend`` adds a linear trend (per year) to treated units only.
    """
    rng = np.random.default_rng(seed)
    days = [
        date(2023, 1, 1) + timedelta(days=i)
        for i in range((date(2025, 12, 31) - date(2023, 1, 1)).days + 1)
    ]
    common = rng.normal(0, 0.1, len(days))
    rows = []
    for u in range(n_treated + n_control):
        is_treated = u < n_treated
        level = rng.normal(5, 1)
        seasonal_amplitude = rng.normal(0.2, 0.05)
        phase = rng.uniform(0, 2 * np.pi)
        for i, day in enumerate(days):
            week = day.isocalendar().week
            value = level + seasonal_amplitude * np.sin(2 * np.pi * week / 52 + phase) + common[i]
            if is_treated:
                value += treated_trend * windows.years_since_start(day)
                if day >= date(2025, 1, 5):
                    value += effect
            value += rng.normal(0, noise)
            rows.append(
                {
                    "period": day,
                    "group": "treated" if is_treated else "control",
                    "unit": f"u{u:02d}",
                    "value": value,
                }
            )
    return pl.DataFrame(rows)


@pytest.fixture(scope="module")
def panel() -> pl.DataFrame:
    return simulated_panel()


# --------------------------------------------------------------------------- building blocks


def test_demean_matches_explicit_dummy_regression() -> None:
    rng = np.random.default_rng(0)
    n = 400
    a = rng.integers(0, 12, n)
    b = rng.integers(0, 9, n)
    x = rng.normal(size=n)
    y = 2.0 * x + rng.normal(size=12)[a] + rng.normal(size=9)[b] + rng.normal(0, 0.1, n)
    x_tilde = demean(x, [encode(a), encode(b)])
    y_tilde = demean(y, [encode(a), encode(b)])
    slope_fwl = float(x_tilde @ y_tilde / (x_tilde @ x_tilde))
    dummies = np.column_stack(
        [x, np.eye(12)[a], np.eye(9)[b][:, 1:]]
    )  # drop one b dummy to avoid collinearity
    slope_full = float(np.linalg.lstsq(dummies, y, rcond=None)[0][0])
    assert slope_fwl == pytest.approx(slope_full, abs=1e-8)


def test_pooled_estimate_matches_pyfixest(panel: pl.DataFrame) -> None:
    pf = pytest.importorskip("pyfixest")
    spec = specs.DidSpec("pooled", "day")
    estimate = did.fit(specs.build_design(panel, spec))
    frame = specs.sample(specs.label_rows(panel, "day"), "year1").with_columns(
        ((pl.col("group") == "treated") & (pl.col("window") == "anticipation"))
        .cast(pl.Int8)
        .alias("anticipation"),
        ((pl.col("group") == "treated") & (pl.col("window") == "post_year1"))
        .cast(pl.Int8)
        .alias("post_year1"),
        (pl.col("unit") + "_" + pl.col("season").cast(pl.Utf8)).alias("unit_season"),
        pl.col("period").cast(pl.Utf8).alias("day"),
    )
    reference = pf.feols(
        "value ~ anticipation + post_year1 | unit_season + day",
        data=frame.to_pandas(),
        vcov={"CRV1": "unit"},
    )
    assert estimate.value("post_year1") == pytest.approx(reference.coef()["post_year1"], abs=1e-8)
    assert estimate.se("post_year1") == pytest.approx(reference.se()["post_year1"], rel=1e-6)


def test_coefficients_are_linear_in_the_outcome(panel: pl.DataFrame) -> None:
    design = specs.build_design(panel, specs.DidSpec("pooled", "day", trends=True))
    estimate = did.fit(design)
    assert np.allclose(estimate.weights.T @ design.y, estimate.coef, atol=1e-8)


# --------------------------------------------------------------------------- known effects


def test_pooled_did_recovers_the_true_effect(panel: pl.DataFrame) -> None:
    estimate = did.fit(specs.build_design(panel, specs.DidSpec("pooled", "day")))
    low, high = did.normal_interval(estimate, "post_year1")
    assert low < TRUE_EFFECT < high
    assert estimate.value("post_year1") == pytest.approx(TRUE_EFFECT, abs=0.01)
    assert estimate.value("anticipation") == pytest.approx(0.0, abs=0.01)


def test_event_study_is_flat_before_and_steps_after() -> None:
    panel = simulated_panel(n_treated=15, n_control=25, seed=21)
    raw = did.fit(specs.build_design(panel, specs.DidSpec("event_study", "day")))
    estimate = specs.relative_to_reference(raw)
    pre = specs.pre_bins(estimate.names)
    assert pre[0] == "bin_-12" and pre[-1] == "bin_-3"  # 2024 bins only; 2023 is the baseline
    post = [n for n in estimate.names if n.startswith("bin_") and n not in pre]
    assert "bin_-1" not in estimate.names and "bin_-2" not in estimate.names
    assert max(abs(estimate.value(n)) for n in pre) < 0.03
    assert np.mean([estimate.value(n) for n in post]) == pytest.approx(TRUE_EFFECT, abs=0.01)
    _, p_value = did.joint_wald_test(estimate, pre)
    assert p_value > 0.01
    small = did.fit(specs.build_design(simulated_panel(), specs.DidSpec("event_study", "day")))
    assert np.isnan(did.joint_wald_test(specs.relative_to_reference(small), pre)[1])


def test_detrending_removes_a_pre_existing_differential_trend() -> None:
    trending = simulated_panel(treated_trend=-0.05)
    primary = did.fit(specs.build_design(trending, specs.DidSpec("pooled", "day")))
    detrended = did.fit(specs.build_design(trending, specs.DidSpec("pooled", "day", trends=True)))
    # The primary estimate absorbs the trend; the detrended one recovers the step.
    assert abs(primary.value("post_year1") - TRUE_EFFECT) > 0.03
    assert detrended.value("post_year1") == pytest.approx(TRUE_EFFECT, abs=0.015)
    low, high = did.normal_interval(detrended, "post_year1")
    assert low < TRUE_EFFECT < high


def test_weather_adjustment_removes_a_treated_only_weather_response() -> None:
    rows = simulated_panel(effect=0.0, n_treated=2, n_control=2, noise=0.02)
    days = rows["period"].unique().sort()
    rng = np.random.default_rng(3)
    # Post-period is warmer; treated sites respond to temperature, controls do not.
    temperature = np.array(
        [rng.normal(15, 5) + (4.0 if d >= date(2025, 1, 5) else 0.0) for d in days]
    )
    weather = pl.DataFrame(
        {
            "date": days,
            "temp_mean_c": temperature,
            "rh_mean_pct": rng.normal(60, 10, len(days)),
            "wind_mean_kmh": rng.normal(12, 3, len(days)),
            "precip_mm": rng.exponential(2, len(days)),
            "pbl_mean_m": rng.normal(800, 150, len(days)),
            "wind_sector": rng.choice(["N", "E", "S", "W"], len(days)),
        }
    )
    lookup = dict(zip(days.to_list(), temperature.tolist(), strict=True))
    rows = rows.with_columns(
        pl.when(pl.col("group") == "treated")
        .then(pl.col("value") + 0.03 * pl.col("period").replace_strict(lookup))
        .otherwise(pl.col("value"))
        .alias("value")
    )
    naive = did.fit(specs.build_design(rows, specs.DidSpec("pooled", "day")))
    adjusted = did.fit(
        specs.build_design(rows, specs.DidSpec("pooled", "day", weather=True), weather=weather)
    )
    assert naive.value("post_year1") == pytest.approx(0.12, abs=0.03)  # 0.03 x 4 degrees
    assert adjusted.value("post_year1") == pytest.approx(0.0, abs=0.02)


# --------------------------------------------------------------------------- inference


def test_wild_bootstrap_enumerates_few_clusters_and_rejects_a_large_effect() -> None:
    rows = simulated_panel(effect=-0.5, n_treated=2, n_control=3, noise=0.05)
    design = specs.build_design(rows, specs.DidSpec("pooled", "day"))
    estimate = did.fit(design)
    result = did.wild_cluster_bootstrap(design, estimate, "post_year1", draws=9999, seed=1)
    assert result.enumerated and result.draws == 6**5
    # With 5 clusters the bootstrap cannot reject strongly, but should lean that way.
    assert result.p_value < 0.2


def test_wild_bootstrap_does_not_reject_without_an_effect() -> None:
    rows = simulated_panel(effect=0.0, n_treated=12, n_control=20, noise=0.05, seed=11)
    design = specs.build_design(rows, specs.DidSpec("pooled", "day"))
    estimate = did.fit(design)
    result = did.wild_cluster_bootstrap(design, estimate, "post_year1", draws=999, seed=1)
    assert result.p_value > 0.05


def test_randomization_inference_reaches_its_minimum_for_a_large_effect() -> None:
    rows = simulated_panel(effect=-0.5, n_treated=2, n_control=5, noise=0.02)
    result = specs.randomization_inference(
        rows, specs.DidSpec("pooled", "day"), lambda e: e.value("post_year1")
    )
    assert len(result.permuted) == 21
    assert result.p_value == pytest.approx(1 / 21)


def test_holm_and_bh_match_statsmodels() -> None:
    from statsmodels.stats.multitest import multipletests

    p = [0.001, 0.04, 0.03, 0.2, 0.008, 0.5]
    assert np.allclose(multiple.holm(p), multipletests(p, method="holm")[1])
    assert np.allclose(multiple.benjamini_hochberg(p), multipletests(p, method="fdr_bh")[1])


# --------------------------------------------------------------------------- synthetic control


def monthly_windows(n_periods: int) -> tuple[list[date], synth.Windows]:
    months = [date(2023 + (i // 12), i % 12 + 1, 1) for i in range(n_periods)]
    labels = np.array([windows.window_of(m, "month") for m in months])
    return months, synth.Windows(
        pre=labels == "pre",
        anticipation=labels == "anticipation",
        post_year1=labels == "post_year1",
        post_extended=labels == "post_extended",
        years=np.array([windows.years_since_start(m) for m in months]),
    )


def test_synthetic_control_recovers_weights_and_effect() -> None:
    rng = np.random.default_rng(5)
    _, masks = monthly_windows(36)
    factors = rng.normal(size=(36, 3)).cumsum(axis=0) * 0.05
    donors = factors @ rng.uniform(0.2, 1.5, size=(3, 12)) + rng.normal(0, 0.005, (36, 12))
    true_weights = np.zeros(12)
    true_weights[[1, 4, 7]] = [0.5, 0.3, 0.2]
    treated = donors @ true_weights + 2.0  # a level difference the centring removes
    treated[masks.post_year1] += -0.08
    result = synth.placebo_inference(treated, donors, masks)
    assert result.fit.effect_year1 == pytest.approx(-0.08, abs=0.01)
    assert result.fit.weights[[1, 4, 7]].sum() > 0.9
    assert result.p_value == pytest.approx(result.min_p_value)
    assert result.fit_ok


def test_detrended_synthetic_control_removes_a_treated_trend() -> None:
    rng = np.random.default_rng(6)
    _, masks = monthly_windows(36)
    donors = rng.normal(0, 0.01, (36, 10)) + rng.normal(size=(36, 1)).cumsum(axis=0) * 0.02
    treated = donors.mean(axis=1) + 0.05 * masks.years  # treated-only drift
    treated[masks.post_year1] += -0.06
    plain = synth.fit_one(treated, donors, masks, detrend=False)
    detrended = synth.fit_one(treated, donors, masks, detrend=True)
    assert abs(plain.effect_year1 - (-0.06)) > 0.03
    assert detrended.effect_year1 == pytest.approx(-0.06, abs=0.015)


# --------------------------------------------------------------------------- windows


@pytest.mark.parametrize(
    ("period", "frequency", "expected"),
    [
        (date(2024, 11, 13), "day", "pre"),
        (date(2024, 11, 14), "day", "anticipation"),
        (date(2025, 1, 4), "day", "anticipation"),
        (date(2025, 1, 5), "day", "post_year1"),
        (date(2026, 1, 2), "day", "gap"),
        (date(2026, 1, 4), "day", "post_extended"),
        (date(2024, 11, 4), "week", "pre"),  # ends Nov 10
        (date(2024, 11, 11), "week", "anticipation"),  # straddles Nov 14
        (date(2024, 12, 30), "week", "anticipation"),  # Jan 5 is its last day
        (date(2025, 1, 6), "week", "post_year1"),
        (date(2024, 10, 1), "month", "pre"),
        (date(2024, 11, 1), "month", "anticipation"),
        (date(2025, 1, 1), "month", "post_year1"),
        (date(2026, 1, 1), "month", "post_extended"),
    ],
)
def test_windows(period: date, frequency: str, expected: str) -> None:
    assert windows.window_of(period, frequency) == expected


def test_event_bins_match_the_calendar_definition() -> None:
    assert windows.event_bin(date(2024, 11, 13), "day") == -1
    assert windows.event_bin(date(2024, 9, 19), "day") == -2
    assert windows.event_bin(date(2024, 9, 18), "day") == -3
    assert windows.event_bin(date(2025, 1, 5), "day") == 0
    assert windows.event_bin(date(2025, 2, 2), "day") == 1
    assert windows.event_bin(date(2024, 10, 1), "month") == -1
    assert windows.event_bin(date(2024, 9, 1), "month") == -2
    assert windows.event_bin(date(2025, 3, 1), "month") == 2
    assert windows.event_bin(date(2024, 12, 1), "month") is None
