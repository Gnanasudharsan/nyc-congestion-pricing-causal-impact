"""Claim labels: robust / fragile / not supported (analysis plan section 8).

Rules (plan §8; amendment §11; deviations 19, 21, 23):

- **Significance.**
  - Primary outcomes: Holm-adjusted p <= 0.05 across the six.
  - Secondary outcomes: BH q <= 0.05 within their family (traffic {T5a, T5b,
    T5c}, transit {R2, R3, R4}, air {A3, A4}, spillover {S2-S5, A2}).
- **Not supported:**
  - not significant after adjustment; or
  - a synthetic control whose pre-period fit fails the RMSPE check (it is then
    descriptive only).
- **Robust:** significant, and *all* of the following hold:
  - every falsification and re-estimation check passes
    (``results/robustness_checks.csv``);
  - DiD: breakdown M-bar >= 1, so the M-bar = 1 interval excludes zero (this
    also settles flagged pre-trends);
  - synthetic control: placebo p <= 0.10 and leave-one-out passes;
  - flagged outcomes (T2, R4, A1, A3, R2): the detrended estimate has the same
    sign and excludes zero (placebo p <= 0.10 for SC).
- **Fragile:** significant, but at least one condition fails. Every failure is
  listed.

Run: ``python -m cordon.robustness.labels``.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import polars as pl

from cordon.config import REPO_ROOT
from cordon.designs import multiple
from cordon.designs.run import DID_OUTCOMES, SYNTHETIC_OUTCOMES
from cordon.robustness.checks import breakdown

LOG = logging.getLogger(__name__)
RESULTS = REPO_ROOT / "results"
FLAGGED = {"T2", "R4", "A1", "A3", "R2"}  # amendment 1, section 11
SECONDARY_FAMILIES = {
    "traffic": ["T5a", "T5b", "T5c"],
    "transit": ["R2", "R3", "R4"],
    "air": ["A3", "A4"],
    "spillover": ["S2", "S3", "S4", "S5", "A2"],
}
DESCRIPTIONS: dict[str, str] = {o.key: o.description for o in DID_OUTCOMES}
DESCRIPTIONS.update({o.key: o.description for o in SYNTHETIC_OUTCOMES})
WEATHER_KEYS = {o.key for o in DID_OUTCOMES if o.weather}
SC_KEYS = {o.key for o in SYNTHETIC_OUTCOMES}


def headline_spec(key: str) -> str:
    """Name the specification whose p-value enters the multiplicity adjustment."""
    if key in SC_KEYS:
        return "synthetic"
    return "pooled_year1_weather" if key in WEATHER_KEYS else "pooled_year1"


def detrended_spec(key: str) -> str:
    """Name the amendment-1 secondary specification for an outcome."""
    if key in SC_KEYS:
        return "synthetic_detrended"
    return "pooled_year1_detrended_weather" if key in WEATHER_KEYS else "pooled_year1_detrended"


def lookup(estimates: pl.DataFrame, key: str, spec: str) -> dict[str, Any]:
    """Return the post-year-1 row of one specification."""
    rows = estimates.filter(
        (pl.col("key") == key) & (pl.col("spec") == spec) & (pl.col("term") == "post_year1")
    )
    return rows.row(0, named=True)


def adjusted_p_values(estimates: pl.DataFrame) -> dict[str, tuple[float, str]]:
    """Holm p for primaries, BH q within each secondary family."""
    out: dict[str, tuple[float, str]] = {}
    holm = pl.read_csv(RESULTS / "primary_holm.csv")
    for r in holm.iter_rows(named=True):
        out[r["key"]] = (float(r["p_holm"]), "Holm (6 primary outcomes)")
    for family, keys in SECONDARY_FAMILIES.items():
        p = [float(lookup(estimates, k, headline_spec(k))["p_value"]) for k in keys]
        for k, q in zip(keys, multiple.benjamini_hochberg(p), strict=True):
            out[k] = (q, f"BH within {family} ({len(keys)} outcomes)")
    return out


def failures_for(
    key: str,
    estimates: pl.DataFrame,
    checks: pl.DataFrame,
    bounds: pl.DataFrame,
    pretrends: pl.DataFrame,
) -> list[str]:
    """Every condition for 'robust' that this outcome does not meet."""
    failures = [
        f"{r['check']} fails"
        for r in checks.filter(
            (pl.col("key") == key) & (pl.col("passes") == False)  # noqa: E712
        ).iter_rows(named=True)
    ]
    headline = lookup(estimates, key, headline_spec(key))
    if key in SC_KEYS:
        if float(headline["p_value"]) > 0.10:
            failures.append(f"placebo p = {float(headline['p_value']):.2f} > 0.10")
    else:
        label, excludes = breakdown(bounds, key)
        pre = pretrends.filter((pl.col("key") == key) & ~pl.col("spec").str.contains("detrended"))
        pre_p = float(pre["p_value"].item()) if pre.height else float("nan")
        if excludes is None:
            failures.append(
                "HonestDiD not computable (too few clusters), so M-bar >= 1 unshown"
                + (f"; pre-trend p = {pre_p:.3f}" if not np.isnan(pre_p) else "")
            )
        elif not excludes:
            failures.append(f"breakdown M-bar = {label} < 1 (pre-trend p = {pre_p:.3g})")
    if key in FLAGGED:
        detrended = lookup(estimates, key, detrended_spec(key))
        if key in SC_KEYS:
            agrees = (
                np.sign(detrended["estimate"]) == np.sign(headline["estimate"])
                and float(detrended["p_value"]) <= 0.10
            )
        else:
            excludes_zero = detrended["ci_low"] > 0 or detrended["ci_high"] < 0
            agrees = (
                np.sign(detrended["estimate"]) == np.sign(headline["estimate"]) and excludes_zero
            )
        if not agrees:
            failures.append("detrended specification disagrees (amendment 1)")
    return failures


def ruled_out(headline: dict[str, Any], key: str) -> str:
    """For unsupported DiD claims: the effects the interval rules out (if reliable)."""
    if key in SC_KEYS:
        return "no interval for synthetic control; see the placebo range and MDE"
    unit = "%" if headline["reported_unit"] == "percent" else f" {headline['reported_unit']}"
    interval = (
        f"{float(headline['reported_ci_low']):+.1f}{unit} to "
        f"{float(headline['reported_ci_high']):+.1f}{unit}"
    )
    clusters = int(headline["n_clusters"])
    if clusters < 30:
        return (
            f"pre-registered p = {float(headline['p_value']):.3f} ({headline['p_method']}); "
            f"the cluster-robust interval {interval} is not reliable with {clusters} clusters, "
            "so no range is claimed as ruled out"
        )
    return f"95% CI {interval}; effects outside it are ruled out at 95% (unadjusted)"


def claims() -> pl.DataFrame:
    """One labelled row per outcome."""
    estimates = pl.read_csv(RESULTS / "estimates.csv", infer_schema_length=None)
    checks = pl.read_csv(RESULTS / "robustness_checks.csv", infer_schema_length=None)
    bounds = pl.read_csv(RESULTS / "honestdid_bounds.csv", infer_schema_length=None)
    pretrends = pl.read_csv(RESULTS / "pretrend_tests.csv")
    adjusted = adjusted_p_values(estimates)
    rows = []
    for key, (p_adj, method) in adjusted.items():
        headline = lookup(estimates, key, headline_spec(key))
        family = "primary" if method.startswith("Holm") else "secondary"
        failures: list[str] = []
        if key in SC_KEYS and headline.get("fit_ok") in (False, "false"):
            label, notes = "not supported", "descriptive only: pre-period fit fails the RMSPE check"
        elif p_adj > 0.05:
            label, notes = "not supported", ruled_out(headline, key)
        else:
            failures = failures_for(key, estimates, checks, bounds, pretrends)
            label = "robust" if not failures else "fragile"
            notes = "; ".join(failures)
        breakdown_label = "" if key in SC_KEYS else breakdown(bounds, key)[0]
        rows.append(
            {
                "key": key,
                "family": family,
                "description": DESCRIPTIONS[key],
                "estimate": headline["reported"],
                "unit": headline["reported_unit"],
                "adjusted_p": p_adj,
                "adjustment": method,
                "breakdown_mbar": breakdown_label,
                "label": label,
                "reasons": notes,
            }
        )
    return pl.DataFrame(rows, infer_schema_length=None)


def main() -> None:
    """Write results/claims.csv."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    table = claims()
    table.write_csv(RESULTS / "claims.csv")
    with pl.Config(tbl_rows=-1, fmt_str_lengths=80):
        print(table.select("key", "estimate", "adjusted_p", "breakdown_mbar", "label"))


if __name__ == "__main__":
    main()
