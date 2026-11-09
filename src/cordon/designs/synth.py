"""Demeaned synthetic control with placebo-in-space inference (ADR 0009, ADR 0011).

Estimator:
1. Centre every unit's series, treated and donors alike, on its own pre-period
   mean. The detrended variant (ADR 0011) instead removes a linear trend fitted on
   the unit's own pre-period.
2. Choose non-negative donor weights that sum to 1 and minimise the pre-period
   mean squared gap between the treated series and the weighted donors.
3. The effect in a window is the mean gap (treated minus synthetic) over the
   periods in that window.

Inference (Abadie, Diamond & Hainmueller 2010):
- Treat each donor in turn as if it were treated, using the other donors as its
  pool (the real treated unit is never a donor).
- Rank the treated unit's post/pre RMSPE ratio among all units. The p-value is
  rank / (number of donors + 1), so the smallest attainable p is 1 / (J + 1).
- Fit diagnostic: if the treated unit's pre-period RMSPE exceeds the median
  placebo pre-period RMSPE, the estimate is reported as descriptive only.

Synthetic controls have no standard error. Alongside the p-value we report the
2.5th to 97.5th percentile range of the placebo effects, labelled as such: it
shows how large a "gap" arises by chance among untreated units.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy import optimize

from cordon.designs.fixed_effects import FloatArray


@dataclass(frozen=True)
class Windows:
    """Boolean masks over periods (rows of the outcome matrix)."""

    pre: np.ndarray
    anticipation: np.ndarray
    post_year1: np.ndarray
    post_extended: np.ndarray
    years: FloatArray  # time regressor for detrending


@dataclass(frozen=True)
class Fit:
    """One synthetic-control fit."""

    weights: FloatArray
    treated: FloatArray  # centred (or detrended) treated series
    synthetic: FloatArray
    gap: FloatArray
    pre_rmspe: float
    post_rmspe: float
    effect_year1: float
    effect_anticipation: float
    effect_extended: float

    @property
    def rmspe_ratio(self) -> float:
        """Post-period RMSPE divided by pre-period RMSPE."""
        return self.post_rmspe / self.pre_rmspe


@dataclass(frozen=True)
class PlaceboResult:
    """Treated fit plus the placebo distribution."""

    fit: Fit
    placebo_ratios: FloatArray
    placebo_effects: FloatArray
    placebo_pre_rmspe: FloatArray
    p_value: float
    min_p_value: float
    fit_ok: bool  # treated pre-RMSPE <= median placebo pre-RMSPE
    donor_names: list[str] = field(default_factory=list)

    @property
    def placebo_range(self) -> tuple[float, float]:
        """2.5th and 97.5th percentiles of placebo year-1 effects."""
        low, high = np.percentile(self.placebo_effects, [2.5, 97.5])
        return float(low), float(high)


def centre(series: FloatArray, windows: Windows, detrend: bool) -> FloatArray:
    """Remove each column's pre-period mean, or its pre-period linear trend."""
    pre = windows.pre
    if not detrend:
        return np.asarray(series - series[pre].mean(axis=0), dtype=np.float64)
    design = np.column_stack([np.ones(int(pre.sum())), windows.years[pre]])
    coef, *_ = np.linalg.lstsq(design, series[pre], rcond=None)
    full = np.column_stack([np.ones(len(windows.years)), windows.years])
    return np.asarray(series - full @ coef, dtype=np.float64)


def fit_weights(target: FloatArray, donors: FloatArray) -> FloatArray:
    """Non-negative weights summing to 1 that minimise ||target - donors @ w||^2.

    Solved exactly with non-negative least squares (an active-set method, so no
    convergence tuning). The sum-to-one constraint is imposed by appending a row
    of ones with a very large weight: any departure from sum(w) = 1 costs far more
    than the fit can gain.
    """
    n_periods, n_donors = donors.shape
    penalty = 1e4 * max(1.0, float(np.abs(donors).max())) * np.sqrt(n_periods)
    augmented = np.vstack([donors, np.full((1, n_donors), penalty)])
    rhs = np.concatenate([target, [penalty]])
    weights, _ = optimize.nnls(augmented, rhs, maxiter=50 * n_donors)
    if weights.sum() <= 0:
        raise RuntimeError("synthetic-control weights are all zero")
    return np.asarray(weights / weights.sum(), dtype=np.float64)


def mean_over(values: FloatArray, mask: np.ndarray) -> float:
    """Mean of values where mask is true; nan if the mask is empty."""
    return float(values[mask].mean()) if mask.any() else float("nan")


def fit_one(target: FloatArray, donors: FloatArray, windows: Windows, detrend: bool) -> Fit:
    """Fit a synthetic control for one treated series against a donor matrix."""
    treated = centre(target[:, None], windows, detrend)[:, 0]
    pool = centre(donors, windows, detrend)
    weights = fit_weights(treated[windows.pre], pool[windows.pre])
    synthetic = pool @ weights
    gap = treated - synthetic
    return Fit(
        weights=weights,
        treated=treated,
        synthetic=synthetic,
        gap=gap,
        pre_rmspe=float(np.sqrt(np.mean(gap[windows.pre] ** 2))),
        post_rmspe=float(np.sqrt(np.mean(gap[windows.post_year1] ** 2))),
        effect_year1=mean_over(gap, windows.post_year1),
        effect_anticipation=mean_over(gap, windows.anticipation),
        effect_extended=mean_over(gap, windows.post_extended),
    )


def placebo_inference(
    target: FloatArray,
    donors: FloatArray,
    windows: Windows,
    detrend: bool = False,
    donor_names: list[str] | None = None,
) -> PlaceboResult:
    """Fit the treated unit and every in-space placebo."""
    treated_fit = fit_one(target, donors, windows, detrend)
    ratios, effects, pre_rmspe = [], [], []
    for j in range(donors.shape[1]):
        others = np.delete(donors, j, axis=1)
        placebo = fit_one(donors[:, j], others, windows, detrend)
        ratios.append(placebo.rmspe_ratio)
        effects.append(placebo.effect_year1)
        pre_rmspe.append(placebo.pre_rmspe)
    ratio_array = np.array(ratios)
    n_units = len(ratios) + 1
    rank = 1 + int((ratio_array >= treated_fit.rmspe_ratio).sum())
    return PlaceboResult(
        fit=treated_fit,
        placebo_ratios=ratio_array,
        placebo_effects=np.array(effects),
        placebo_pre_rmspe=np.array(pre_rmspe),
        p_value=rank / n_units,
        min_p_value=1 / n_units,
        fit_ok=treated_fit.pre_rmspe <= float(np.median(pre_rmspe)),
        donor_names=donor_names or [],
    )
