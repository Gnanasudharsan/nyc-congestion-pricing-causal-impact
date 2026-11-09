"""Difference-in-differences and event studies with a single treatment date.

Pre-registered specification (analysis plan sections 4-5, ADR 0005):

    y_ut = sum_k beta_k * D_k,ut + alpha_(u x season) + gamma_t + e_ut

- ``D_k`` are treated-unit indicators for a window (pooled DiD) or for 4-week
  event-time bins (event study). Season is ISO week-of-year for daily data and
  month-of-year for monthly data.
- The anticipation window (2024-11-14 to 2025-01-04) always has its own
  indicator, so it never contaminates the baseline (ADR 0007).

Optional pre-fitted adjustment (ADR 0011 detrending; A3 weather slopes):

1. On pre-period rows only, regress y on adjustment columns Z (for example
   unit-specific linear trends) plus the same fixed effects.
2. Subtract Z * gamma_hat from y on *every* row (extrapolating the pre-period
   fit forward), then run the specification above.

Fitting the adjustment on the pre-period only means post-period effects cannot
bend it (Wolfers 2006; Borusyak, Jaravel & Spiess 2024).

Why everything here is "linear in y": both steps are least squares, so each
coefficient equals ``w' y`` for a fixed weight vector ``w`` that depends only on
the design. We compute ``w`` once. Then
- the cluster-robust variance is ``sum over clusters of (w_g' e_g)^2``, and
- every wild-bootstrap replication is a weighted sum of cluster scores. Each
  replication therefore re-estimates the adjustment exactly, as ADR 0011
  requires, without re-running any regression.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt
from scipy import stats

from cordon.designs.fixed_effects import FloatArray, IntArray, demean, encode

BoolArray = npt.NDArray[np.bool_]
BOOTSTRAP_CHUNK = 32  # cluster blocks processed together (memory vs speed)

# Webb (2014) six-point weights: better than Rademacher with few clusters.
WEBB_WEIGHTS = np.array(
    [-np.sqrt(1.5), -1.0, -np.sqrt(0.5), np.sqrt(0.5), 1.0, np.sqrt(1.5)], dtype=np.float64
)


@dataclass(frozen=True)
class Design:
    """Arrays for one regression. Rows are unit-periods."""

    y: FloatArray  # outcome, shape (n,)
    x: FloatArray  # treatment regressors, shape (n, k)
    names: tuple[str, ...]  # one name per column of x
    fixed_effects: tuple[IntArray, ...]  # integer codes per fixed-effect set
    clusters: IntArray  # cluster code per row
    adjust: FloatArray | None = None  # pre-fitted adjustment columns Z, shape (n, m)
    adjust_rows: BoolArray | None = None  # rows used to fit Z (the pre-period)


@dataclass(frozen=True)
class Estimate:
    """Coefficients plus everything needed for inference."""

    names: tuple[str, ...]
    coef: FloatArray
    vcov: FloatArray  # cluster-robust (CRV1)
    weights: FloatArray  # (n, k): coef == weights.T @ y
    residuals: FloatArray  # residuals of the final regression, shape (n,)
    clusters: IntArray
    n_obs: int
    n_clusters: int
    n_params: int  # K used in the small-sample factor

    def index(self, name: str) -> int:
        """Position of a named coefficient."""
        return self.names.index(name)

    def se(self, name: str) -> float:
        """Cluster-robust standard error of a named coefficient."""
        i = self.index(name)
        return float(np.sqrt(self.vcov[i, i]))

    def value(self, name: str) -> float:
        """Point estimate of a named coefficient."""
        return float(self.coef[self.index(name)])


# --------------------------------------------------------------------------- fitting


def restrict_codes(codes: IntArray, rows: BoolArray) -> IntArray:
    """Fixed-effect codes for a subset of rows, re-encoded to 0..levels-1."""
    return encode(codes[rows])


def adjustment_projection(design: Design) -> tuple[FloatArray, FloatArray] | None:
    """Pre-period-demeaned Z and the pseudo-inverse of its cross-product."""
    if design.adjust is None or design.adjust_rows is None:
        return None
    rows = design.adjust_rows
    pre_effects = [restrict_codes(codes, rows) for codes in design.fixed_effects]
    z_pre = demean(design.adjust[rows], pre_effects)
    gram_inverse = np.linalg.pinv(z_pre.T @ z_pre, rcond=1e-10, hermitian=True)
    return z_pre, gram_inverse


def adjusted_outcome(
    design: Design, y: FloatArray, projection: tuple[FloatArray, FloatArray] | None
) -> FloatArray:
    """Step 1: subtract the pre-period-fitted adjustment from every row."""
    if projection is None or design.adjust is None or design.adjust_rows is None:
        return y
    z_pre, gram_inverse = projection
    gamma = gram_inverse @ (z_pre.T @ y[design.adjust_rows])
    return y - design.adjust @ gamma


def cluster_scores(weights: FloatArray, residuals: FloatArray, clusters: IntArray) -> FloatArray:
    """Per-cluster sums of weight x residual, shape (clusters, k)."""
    n_clusters = int(clusters.max()) + 1
    contributions = weights * residuals[:, None]
    scores = np.zeros((n_clusters, weights.shape[1]))
    np.add.at(scores, clusters, contributions)
    return scores


def small_sample_factor(n_obs: int, n_params: int, n_clusters: int) -> float:
    """CRV1 correction G/(G-1) x (N-1)/(N-K), the ``fixest``/``pyfixest`` default."""
    return (n_clusters / (n_clusters - 1)) * ((n_obs - 1) / (n_obs - n_params))


def is_nested(codes: IntArray, clusters: IntArray) -> bool:
    """Check whether every fixed-effect level lies inside a single cluster."""
    pairs = np.unique(np.column_stack([codes, clusters]), axis=0)
    return len(pairs) == len(np.unique(codes))


def counted_parameters(design: Design, clusters: IntArray) -> int:
    """K for the small-sample factor, following ``pyfixest``'s default (``k_fixef="nonnested"``).

    All fixed-effect levels count, minus one for each fixed-effect set after the
    first (they share the intercept). Sets nested within the cluster variable are
    then removed, except for one level each.
    """
    levels = [int(codes.max()) + 1 for codes in design.fixed_effects]
    if not levels:
        return int(design.x.shape[1])
    nested = [is_nested(codes, clusters) for codes in design.fixed_effects]
    count = sum(levels) - (len(levels) - 1)
    count -= sum(n for n, is_n in zip(levels, nested, strict=True) if is_n)
    count += sum(nested)
    return int(design.x.shape[1]) + count


@dataclass(frozen=True)
class Prepared:
    """Parts of a design that do not depend on the outcome, computed once."""

    design: Design
    x_tilde: FloatArray  # treatment regressors with fixed effects removed
    projection: tuple[FloatArray, FloatArray] | None  # pre-period adjustment, if any


def prepare(design: Design) -> Prepared:
    """Demean the regressors and set up the pre-period adjustment."""
    return Prepared(
        design=design,
        x_tilde=demean(design.x, list(design.fixed_effects)),
        projection=adjustment_projection(design),
    )


def residuals_of(prepared: Prepared, y: FloatArray) -> FloatArray:
    """Residuals of the full (two-step) fit for one or several outcome columns.

    The map from y to residuals is linear, which the bootstrap relies on.
    """
    design = prepared.design
    y_adjusted = adjusted_outcome(design, y, prepared.projection)
    y_tilde = demean(y_adjusted, list(design.fixed_effects))
    coef, *_ = np.linalg.lstsq(prepared.x_tilde, y_tilde, rcond=None)
    return np.asarray(y_tilde - prepared.x_tilde @ coef, dtype=np.float64)


def fit(design: Design) -> Estimate:
    """Estimate the coefficients and their cluster-robust covariance."""
    prepared = prepare(design)
    y_adjusted = adjusted_outcome(design, design.y, prepared.projection)
    y_tilde = demean(y_adjusted, list(design.fixed_effects))
    x_tilde = prepared.x_tilde

    xtx_inverse = np.linalg.inv(x_tilde.T @ x_tilde)
    weights = x_tilde @ xtx_inverse  # coef = weights.T @ y_adjusted
    coef = weights.T @ y_tilde
    residuals = y_tilde - x_tilde @ coef

    if prepared.projection is not None and design.adjust is not None:
        # coef = W'y - (W'Z) (Z~'Z~)^+ Z~' y_pre, so pre-period rows get extra weight.
        z_pre, gram_inverse = prepared.projection
        correction = z_pre @ (gram_inverse @ (design.adjust.T @ weights))
        weights = weights.copy()
        weights[design.adjust_rows] -= correction

    clusters = encode(design.clusters)
    n_clusters = int(clusters.max()) + 1
    scores = cluster_scores(weights, residuals, clusters)
    n_params = counted_parameters(design, clusters)
    factor = small_sample_factor(len(design.y), n_params, n_clusters)
    vcov = factor * scores.T @ scores
    return Estimate(
        names=design.names,
        coef=coef,
        vcov=vcov,
        weights=weights,
        residuals=residuals,
        clusters=clusters,
        n_obs=len(design.y),
        n_clusters=n_clusters,
        n_params=n_params,
    )


# --------------------------------------------------------------------------- inference


def normal_interval(estimate: Estimate, name: str, level: float = 0.95) -> tuple[float, float]:
    """Wald interval using the cluster-robust SE and a t(G-1) critical value."""
    critical = float(stats.t.ppf(0.5 + level / 2, df=estimate.n_clusters - 1))
    value, se = estimate.value(name), estimate.se(name)
    return value - critical * se, value + critical * se


def wald_p_value(estimate: Estimate, name: str) -> float:
    """Two-sided p-value from t(G-1)."""
    t_stat = estimate.value(name) / estimate.se(name)
    return float(2 * stats.t.sf(abs(t_stat), df=estimate.n_clusters - 1))


MIN_CLUSTERS_FOR_WALD = 30  # ADR 0005: below this, use randomization inference


def joint_wald_test(estimate: Estimate, names: list[str]) -> tuple[float, float]:
    """F-test that the named coefficients are jointly zero. Returns (F, p).

    Uses F(q, G-1). Returns (nan, nan) with fewer than 30 clusters: a cluster-robust
    covariance of many coefficients from few clusters is badly estimated, and the
    test over-rejects (simulated: F = 14.6 under a true null with 16 clusters).
    """
    q = len(names)
    if estimate.n_clusters < MIN_CLUSTERS_FOR_WALD or q > estimate.n_clusters - 1:
        return float("nan"), float("nan")
    idx = [estimate.index(name) for name in names]
    beta = estimate.coef[idx]
    block = estimate.vcov[np.ix_(idx, idx)]
    f_stat = float(beta @ np.linalg.solve(block, beta)) / q
    return f_stat, float(stats.f.sf(f_stat, q, estimate.n_clusters - 1))


def webb_draws(n_clusters: int, draws: int, seed: int) -> FloatArray:
    """Bootstrap weight matrix (draws x clusters); enumerates all draws when feasible."""
    if 6**n_clusters <= draws:
        grid = itertools.product(range(6), repeat=n_clusters)
        return np.asarray([WEBB_WEIGHTS[list(combo)] for combo in grid], dtype=np.float64)
    rng = np.random.default_rng(seed)
    return np.asarray(rng.choice(WEBB_WEIGHTS, size=(draws, n_clusters)), dtype=np.float64)


@dataclass(frozen=True)
class BootstrapResult:
    """Restricted wild cluster bootstrap-t for one coefficient."""

    p_value: float
    draws: int
    enumerated: bool


def wild_cluster_bootstrap(
    design: Design, estimate: Estimate, name: str, draws: int, seed: int
) -> BootstrapResult:
    """Restricted (null-imposed) wild cluster bootstrap-t, Webb weights.

    Under H0 (coefficient = 0) we refit without that column, then build
    bootstrap outcomes y* = fitted_restricted + v_g * residual_restricted. Because
    the whole estimator is linear in y, each replication's coefficient and
    cluster-robust SE are weighted sums we can compute for all draws at once.
    """
    j = estimate.index(name)
    keep = [i for i in range(design.x.shape[1]) if i != j]
    full = prepare(design)
    if keep:
        restricted = prepare(
            Design(
                y=design.y,
                x=design.x[:, keep],
                names=tuple(design.names[i] for i in keep),
                fixed_effects=design.fixed_effects,
                clusters=design.clusters,
                adjust=design.adjust,
                adjust_rows=design.adjust_rows,
            )
        )
        restricted_residuals = residuals_of(restricted, design.y)
    else:
        y_adjusted = adjusted_outcome(design, design.y, full.projection)
        restricted_residuals = demean(y_adjusted, list(design.fixed_effects))
    fitted = design.y - restricted_residuals

    clusters = estimate.clusters
    n_clusters = estimate.n_clusters
    w = estimate.weights[:, j]
    # Constant part (from the restricted fitted values) and per-cluster parts.
    base_coef = float(w @ fitted)
    cluster_coef = np.bincount(clusters, weights=w * restricted_residuals, minlength=n_clusters)
    base_scores = np.bincount(
        clusters, weights=w * residuals_of(full, fitted), minlength=n_clusters
    )
    score_matrix = np.zeros((n_clusters, n_clusters))  # [g, h]: score in g from cluster h
    for chunk_start in range(0, n_clusters, BOOTSTRAP_CHUNK):
        chunk = range(chunk_start, min(chunk_start + BOOTSTRAP_CHUNK, n_clusters))
        blocks = np.column_stack(
            [np.where(clusters == h, restricted_residuals, 0.0) for h in chunk]
        )
        block_residuals = residuals_of(full, blocks)
        for column, h in enumerate(chunk):
            score_matrix[:, h] = np.bincount(
                clusters, weights=w * block_residuals[:, column], minlength=n_clusters
            )

    v = webb_draws(n_clusters, draws, seed)
    coef_star = base_coef + v @ cluster_coef
    scores_star = base_scores[None, :] + v @ score_matrix.T
    factor = small_sample_factor(len(design.y), counted_parameters(design, clusters), n_clusters)
    se_star = np.sqrt(factor * (scores_star**2).sum(axis=1))
    t_star = coef_star / se_star
    t_obs = estimate.value(name) / estimate.se(name)
    p_value = float(np.mean(np.abs(t_star) >= abs(t_obs)))
    return BootstrapResult(p_value=p_value, draws=len(v), enumerated=6**n_clusters <= draws)


def percent(log_points: float) -> float:
    """Convert a log-point effect to a percentage change, 100 x (exp(b) - 1)."""
    return float(100 * np.expm1(log_points))
