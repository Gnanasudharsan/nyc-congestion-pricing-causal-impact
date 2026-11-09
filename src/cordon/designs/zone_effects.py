"""Zone-level spillover effects and the equity lens (analysis plan section 9; deviation 15).

**EXPLORATORY.** The associations below are not causal claims: neighbourhood
characteristics are not randomly assigned, and they correlate with distance to
the zone, transit access, and trip mix.

Steps:
1. **Zone effects.** One regression with S1's border-ring zones and S3's upper
   Manhattan + Bronx zones as treated units, each with its own treated x
   anticipation and treated x post-year-1 indicator. All far-control zones are
   the shared comparison. Same fixed effects as the pre-registered DiD.
2. **Noise per zone.** With one treated cluster per coefficient, a
   cluster-robust SE is unreliable. Each zone's sampling SD is instead taken
   from placebo-in-time estimates on pre-period data only, at the 14 placebo
   dates used for the Phase 2 MDEs. This measures how much that zone's estimate
   moves by chance.
3. **Empirical-Bayes shrinkage.** Normal-normal model with the DerSimonian-Laird
   between-zone variance tau^2. Shrunk effect = mu + tau^2 / (tau^2 + s_z^2) x
   (b_z - mu).
4. **Associations.** For each covariate (median household income, no-vehicle
   share, poverty rate, adult asthma ED-visit rate):
   - the population-weighted correlation with the shrunk effects;
   - a population-weighted regression of the shrunk effect on the standardised
     covariate, with HC1 SEs. A multivariable regression with all four is
     reported too.
   SEs ignore the estimation error in the shrunk effects (generated
   regressand), so they are, if anything, too small.

Run: ``python -m cordon.designs.zone_effects``.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

import numpy as np
import polars as pl
import statsmodels.api as sm

from cordon.config import FINAL_DIR, REPO_ROOT
from cordon.designs import did, panels, specs
from cordon.designs.fixed_effects import encode
from cordon.robustness.mde import PRE_END, placebo_dates

LOG = logging.getLogger(__name__)
ZONE_OUTPUT = REPO_ROOT / "results" / "zone_spillover_effects.csv"
ASSOCIATION_OUTPUT = REPO_ROOT / "results" / "equity_associations.csv"
COVARIATES = {
    "median_income_popweighted": "Median household income",
    "share_no_vehicle": "Households without a vehicle (share)",
    "poverty_rate": "Poverty rate",
    "asthma_ed_rate_adults": "Adult asthma ED visits per 10,000 (2017-2019)",
}


def spillover_rows() -> pl.DataFrame:
    """Treated rows from S1 and S3, plus the shared far-control rows."""
    ring = panels.tlc_count_panel("border_ring").with_columns(pl.lit("S1").alias("design"))
    upper = panels.tlc_count_panel("upper_manhattan_bronx").with_columns(
        pl.lit("S3").alias("design")
    )
    control = ring.filter(pl.col("group") == "control")
    return pl.concat(
        [
            ring.filter(pl.col("group") == "treated"),
            upper.filter(pl.col("group") == "treated"),
            control,
        ]
    )


def zone_design(frame: pl.DataFrame, zones: list[str], start: date) -> did.Design:
    """Per-zone indicators for periods on/after ``start`` (and anticipation, if present)."""
    unit = frame["unit"].to_numpy()
    period = frame["period"].to_numpy()
    window = frame["window"].to_numpy()
    columns, names = [], []
    after = period >= np.datetime64(start)
    for zone in zones:
        is_zone = unit == zone
        if (window == "anticipation").any():
            columns.append(is_zone & (window == "anticipation"))
            names.append(f"anticipation:{zone}")
            columns.append(is_zone & (window == "post_year1"))
        else:
            columns.append(is_zone & after)
        names.append(f"effect:{zone}")
    return did.Design(
        y=frame["value"].to_numpy().astype(np.float64),
        x=np.column_stack(columns).astype(np.float64),
        names=tuple(names),
        fixed_effects=(
            encode((frame["unit"] + "_" + frame["season"].cast(pl.Utf8)).to_numpy()),
            encode(frame["period"].cast(pl.Utf8).to_numpy()),
        ),
        clusters=encode(frame["unit"].to_numpy()),
    )


def zone_estimates(rows: pl.DataFrame) -> pl.DataFrame:
    """Post-year-1 effect per spillover zone, with placebo-based sampling SDs."""
    labelled = specs.label_rows(rows, "day")
    zones = sorted(rows.filter(pl.col("group") == "treated")["unit"].unique().to_list())
    actual = did.fit(zone_design(specs.sample(labelled, "year1"), zones, date(2025, 1, 5)))
    pre = labelled.filter(pl.col("window") == "pre")
    placebo = np.array(
        [
            [did.fit(zone_design(pre, zones, d)).value(f"effect:{z}") for z in zones]
            for d in placebo_dates()
        ]
    )
    LOG.info(
        "zone effects: %d zones, %d placebo dates (pre-period ends %s)",
        len(zones),
        len(placebo),
        PRE_END,
    )
    design_of = dict(rows.select("unit", "design").unique().iter_rows())
    return pl.DataFrame(
        {
            "location_id": [int(z) for z in zones],
            "design": [design_of[z] for z in zones],
            "estimate": [actual.value(f"effect:{z}") for z in zones],
            "placebo_sd": placebo.std(axis=0, ddof=1),
            "placebo_mean": placebo.mean(axis=0),
        }
    )


def shrink(estimates: np.ndarray, sds: np.ndarray) -> tuple[np.ndarray, float, float]:
    """DerSimonian-Laird empirical-Bayes shrinkage. Returns (shrunk, mu, tau^2)."""
    w = 1 / sds**2
    mu_fixed = float((w * estimates).sum() / w.sum())
    q = float((w * (estimates - mu_fixed) ** 2).sum())
    tau2 = max(0.0, (q - (len(estimates) - 1)) / (w.sum() - (w**2).sum() / w.sum()))
    w_random = 1 / (sds**2 + tau2)
    mu = float((w_random * estimates).sum() / w_random.sum())
    shrunk = mu + tau2 / (tau2 + sds**2) * (estimates - mu)
    return shrunk, mu, tau2


def weighted_correlation(x: np.ndarray, y: np.ndarray, w: np.ndarray) -> float:
    """Population-weighted Pearson correlation."""
    mx, my = np.average(x, weights=w), np.average(y, weights=w)
    cov = np.average((x - mx) * (y - my), weights=w)
    return float(
        cov / np.sqrt(np.average((x - mx) ** 2, weights=w) * np.average((y - my) ** 2, weights=w))
    )


def associations(zones: pl.DataFrame) -> list[dict[str, Any]]:
    """Weighted correlations and regressions of shrunk effects on covariates."""
    complete = zones.drop_nulls([*COVARIATES, "population"]).filter(pl.col("population") > 0)
    y = complete["shrunk_percent"].to_numpy()
    w = complete["population"].to_numpy()
    standardised = {}
    for column in COVARIATES:
        x = complete[column].to_numpy()
        mean = np.average(x, weights=w)
        sd = np.sqrt(np.average((x - mean) ** 2, weights=w))
        standardised[column] = (x - mean) / sd
    rows = []
    for column, label in COVARIATES.items():
        fit = sm.WLS(y, sm.add_constant(standardised[column]), weights=w).fit(cov_type="HC1")
        rows.append(
            {
                "model": "bivariate",
                "covariate": column,
                "label": label,
                "weighted_correlation": weighted_correlation(complete[column].to_numpy(), y, w),
                "slope_per_sd": float(fit.params[1]),
                "se": float(fit.bse[1]),
                "p_value": float(fit.pvalues[1]),
                "n_zones": complete.height,
            }
        )
    x_all = sm.add_constant(np.column_stack([standardised[c] for c in COVARIATES]))
    fit = sm.WLS(y, x_all, weights=w).fit(cov_type="HC1")
    for i, (column, label) in enumerate(COVARIATES.items(), start=1):
        rows.append(
            {
                "model": "multivariable",
                "covariate": column,
                "label": label,
                "weighted_correlation": None,
                "slope_per_sd": float(fit.params[i]),
                "se": float(fit.bse[i]),
                "p_value": float(fit.pvalues[i]),
                "n_zones": complete.height,
            }
        )
    return rows


def main() -> None:
    """Write zone effects and equity associations to results/."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    zones = zone_estimates(spillover_rows())
    shrunk, mu, tau2 = shrink(zones["estimate"].to_numpy(), zones["placebo_sd"].to_numpy())
    zones = zones.with_columns(
        pl.Series("shrunk", shrunk),
        pl.Series("shrunk_percent", 100 * np.expm1(shrunk)),
        pl.Series("raw_percent", 100 * np.expm1(zones["estimate"].to_numpy())),
        pl.lit(mu).alias("eb_mean"),
        pl.lit(tau2).alias("eb_tau2"),
    )
    equity = pl.read_csv(FINAL_DIR / "zone_equity.csv")
    groups = pl.read_csv(FINAL_DIR / "zone_groups.csv").select("location_id", "zone", "borough")
    zones = zones.join(groups, on="location_id", how="left").join(
        equity, on="location_id", how="left"
    )
    ZONE_OUTPUT.parent.mkdir(exist_ok=True)
    zones.write_csv(ZONE_OUTPUT)
    pl.DataFrame(associations(zones), infer_schema_length=None).write_csv(ASSOCIATION_OUTPUT)
    LOG.info("EB mean %.4f, tau^2 %.6f", mu, tau2)


if __name__ == "__main__":
    main()
