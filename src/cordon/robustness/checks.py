"""Phase 5 robustness and falsification checks (analysis plan section 7; deviations 18-22).

Every check writes one row to ``results/robustness_checks.csv`` with the
estimate, its interval or p-value, the primary estimate it is compared with,
and whether it passes. The pass rules were fixed before any check was run
(deviation 18):

- **placebo** (placebo date, placebo outcome): passes if the 95% interval
  includes zero, or the estimate is less than half the primary estimate in
  magnitude. With fewer than 30 clusters, "includes zero" means wild-bootstrap
  p >= 0.05.
- **re-estimation** (control groups, dropped windows, did2s, leave-one-out
  donors, data variants): passes if the sign matches the primary estimate.
- **dose-response:** passes if |overnight| <= |peak|.
- HonestDiD bounds go to ``results/honestdid_bounds.csv`` and DoWhy refuters to
  ``results/dowhy_refuters.csv``.

Run: ``python -m cordon.robustness.checks`` (about 45-90 minutes; the HonestDiD
bounds dominate).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import date
from typing import Any

import numpy as np
import polars as pl

from cordon.config import FINAL_DIR, PROCESSED_DIR, RANDOM_SEED, REPO_ROOT
from cordon.designs import did, panels, specs, synth
from cordon.designs.fixed_effects import demean, encode
from cordon.designs.run import DID_OUTCOMES, SYNTHETIC_OUTCOMES, DidOutcome, SyntheticOutcome
from cordon.robustness import honest
from cordon.robustness.mde import fitted_sc_estimate

LOG = logging.getLogger(__name__)
RESULTS = REPO_ROOT / "results"
PLACEBO_DATE = date(2024, 1, 7)  # analysis plan section 7, check 2
PAUSE_WINDOW = (date(2024, 5, 15), date(2024, 7, 15))  # ADR 0007
FEW_CLUSTERS = did.MIN_CLUSTERS_FOR_WALD
BOOTSTRAP_DRAWS = 9_999
MBAR_GRID = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0]
SD_MULTIPLES = [0.0, 0.5, 1.0, 2.0]
SMOOTHNESS_KEYS = {"T2", "R2"}  # amendment 1; A3 has too few clusters
DOWHY_KEYS = {"T2", "A3"}


# --------------------------------------------------------------------------- helpers


def pooled_effect(rows: pl.DataFrame, outcome: DidOutcome, weather: pl.DataFrame) -> dict[str, Any]:
    """Pooled year-1 estimate with interval and a p-value suited to the cluster count."""
    spec = specs.DidSpec(
        "pooled",
        outcome.frequency,
        weather=outcome.weather,
        weather_columns=outcome.weather_columns,
    )
    design = specs.build_design(rows, spec, weather=weather if outcome.weather else None)
    estimate = did.fit(design)
    return summarise(design, estimate, "post_year1")


def summarise(design: did.Design, estimate: did.Estimate, name: str) -> dict[str, Any]:
    """Estimate, CI, p-value (bootstrap when clusters are few)."""
    low, high = did.normal_interval(estimate, name)
    p_value = did.wald_p_value(estimate, name)
    method = f"cluster-robust t({estimate.n_clusters - 1})"
    if estimate.n_clusters < FEW_CLUSTERS:
        boot = did.wild_cluster_bootstrap(design, estimate, name, BOOTSTRAP_DRAWS, RANDOM_SEED)
        p_value, method = boot.p_value, "wild cluster bootstrap (Webb)"
    return {
        "estimate": estimate.value(name),
        "ci_low": low,
        "ci_high": high,
        "p_value": p_value,
        "p_method": method,
        "n_clusters": estimate.n_clusters,
    }


def placebo_passes(result: dict[str, Any], primary: float) -> bool:
    """Deviation 18(a)."""
    if result["n_clusters"] < FEW_CLUSTERS:
        includes_zero = result["p_value"] >= 0.05
    else:
        includes_zero = result["ci_low"] <= 0 <= result["ci_high"]
    return bool(includes_zero or abs(result["estimate"]) < 0.5 * abs(primary))


def row(
    key: str,
    check: str,
    kind: str,
    result: dict[str, Any],
    primary: float,
    passes: bool | None,
    note: str = "",
) -> dict[str, Any]:
    """One results row."""
    return {
        "key": key,
        "check": check,
        "kind": kind,
        "primary_estimate": primary,
        "estimate": result.get("estimate"),
        "ci_low": result.get("ci_low"),
        "ci_high": result.get("ci_high"),
        "p_value": result.get("p_value"),
        "p_method": result.get("p_method"),
        "passes": passes,
        "note": note,
    }


def same_sign(value: float, primary: float) -> bool:
    """Deviation 18(b)."""
    return bool(np.sign(value) == np.sign(primary))


def placebo_date_effect(rows: pl.DataFrame, frequency: str) -> dict[str, Any]:
    """Fake treatment at 2024-01-07 using only data before the anticipation window."""
    frame = specs.label_rows(rows, frequency).filter(
        (pl.col("window") == "pre") & pl.col("value").is_not_nan()
    )
    start = PLACEBO_DATE if frequency == "day" else PLACEBO_DATE.replace(day=1)
    treated = (frame["group"] == "treated").to_numpy()
    after = (frame["period"] >= start).to_numpy()
    design = did.Design(
        y=frame["value"].to_numpy().astype(np.float64),
        x=(treated & after).astype(np.float64)[:, None],
        names=("placebo",),
        fixed_effects=(
            encode((frame["unit"] + "_" + frame["season"].cast(pl.Utf8)).to_numpy()),
            encode(frame["period"].cast(pl.Utf8).to_numpy()),
        ),
        clusters=encode(frame["cluster"].to_numpy()),
    )
    return summarise(design, did.fit(design), "placebo")


def did2s_effect(rows: pl.DataFrame, outcome: DidOutcome) -> dict[str, Any]:
    """Imputation (two-stage) DiD with pyfixest (ADR 0005 heterogeneity-robust check)."""
    import pyfixest as pf

    frame = (
        specs.sample(specs.label_rows(rows, outcome.frequency), "year1")
        .with_columns(
            (pl.col("unit") + "_" + pl.col("season").cast(pl.Utf8)).alias("unit_season"),
            pl.col("period").cast(pl.Utf8).alias("period_label"),
            ((pl.col("group") == "treated") & (pl.col("window") == "post_year1"))
            .cast(pl.Int8)
            .alias("post_year1"),
            ((pl.col("group") == "treated") & (pl.col("window") == "anticipation"))
            .cast(pl.Int8)
            .alias("anticipation"),
        )
        .with_columns(((pl.col("post_year1") + pl.col("anticipation")) > 0).alias("treat_any"))
    )
    # Imputation needs every unit x season level in the untreated (first-stage) sample;
    # treated rows whose level never appears untreated cannot be imputed.
    observed = frame.filter(~pl.col("treat_any"))["unit_season"].unique()
    before = frame.height
    frame = frame.filter(pl.col("unit_season").is_in(observed.implode()))
    dropped = before - frame.height
    fit = pf.did2s(
        frame.select(
            "value",
            "unit_season",
            "period_label",
            "post_year1",
            "anticipation",
            "treat_any",
            "cluster",
        ).to_pandas(),
        yname="value",
        first_stage="~ 0 | unit_season + period_label",
        second_stage="~ post_year1 + anticipation",
        treatment="treat_any",
        cluster="cluster",
    )
    value, se = float(fit.coef()["post_year1"]), float(fit.se()["post_year1"])
    return {
        "estimate": value,
        "ci_low": value - 1.96 * se,
        "ci_high": value + 1.96 * se,
        "p_value": float(fit.pvalue()["post_year1"]),
        "p_method": f"pyfixest did2s ({dropped} non-imputable treated rows dropped)",
    }


# --------------------------------------------------------------------------- HonestDiD


def honest_rows(
    key: str, rows: pl.DataFrame, outcome: DidOutcome, weather: pl.DataFrame
) -> list[dict[str, Any]]:
    """Relative-magnitudes (and, for flagged outcomes, smoothness) bounds."""
    spec = specs.DidSpec(
        "event_study",
        outcome.frequency,
        weather=outcome.weather,
        weather_columns=outcome.weather_columns,
    )
    estimate = specs.relative_to_reference(
        did.fit(specs.build_design(rows, spec, weather=weather if outcome.weather else None))
    )
    if estimate.n_clusters < FEW_CLUSTERS:
        return [
            {
                "key": key,
                "restriction": "relative_magnitudes",
                "parameter": None,
                "lb": None,
                "ub": None,
                "note": f"not computed: {estimate.n_clusters} clusters "
                "give a singular covariance (deviation 18d)",
            }
        ]
    pre = sorted(specs.pre_bins(estimate.names), key=lambda n: int(n.removeprefix("bin_")))
    post = sorted(
        (n for n in estimate.names if n.startswith("bin_") and n not in pre),
        key=lambda n: int(n.removeprefix("bin_")),
    )
    order = [estimate.index(n) for n in [*pre, *post]]
    beta = estimate.coef[order]
    sigma = estimate.vcov[np.ix_(order, order)]
    l_vec = np.full(len(post), 1 / len(post))
    pre_values = beta[: len(pre)]
    scale = float(np.abs(np.diff(np.concatenate([pre_values, [0.0]]), 2)).max())
    m_grid = [round(c * scale, 6) for c in SD_MULTIPLES] if key in SMOOTHNESS_KEYS else []
    result = honest.bounds(
        beta, sigma, len(pre), len(post), l_vec, MBAR_GRID, m_grid, tag=f"phase5_{key}"
    )
    out = [
        {
            "key": key,
            "restriction": "original",
            "parameter": None,
            "lb": result["original"]["lb"],
            "ub": result["original"]["ub"],
            "note": "",
        }
    ]
    for restriction, param in (("relative_magnitudes", "Mbar"), ("smoothness", "M")):
        for item in result[restriction]:
            out.append(
                {
                    "key": key,
                    "restriction": restriction,
                    "parameter": item[param],
                    "lb": item["lb"],
                    "ub": item["ub"],
                    "note": "",
                }
            )
    LOG.info("HonestDiD %s done", key)
    return out


def breakdown(bounds: pl.DataFrame, key: str) -> tuple[str, bool | None]:
    """Breakdown M-bar on the grid, and whether the M-bar = 1 interval excludes zero."""
    rm = bounds.filter((pl.col("key") == key) & (pl.col("restriction") == "relative_magnitudes"))
    if rm.height == 0 or rm["lb"].null_count() == rm.height:
        return "not computed", None
    rm = rm.sort("parameter")
    grid = rm["parameter"].cast(pl.Float64).to_list()
    includes = [lb <= 0 <= ub for lb, ub in zip(rm["lb"], rm["ub"], strict=True)]
    if not any(includes):
        label = f"> {grid[-1]:g}"
    elif includes[0]:
        label = f"<= {grid[0]:g}"  # already includes zero at the smallest grid value
    else:
        first = includes.index(True)
        label = f"{grid[first - 1]:g}-{grid[first]:g}"
    at_one = rm.filter(pl.col("parameter") == 1.0).row(0, named=True)
    return label, not (at_one["lb"] <= 0 <= at_one["ub"])


# --------------------------------------------------------------------------- DoWhy


def dowhy_rows(
    key: str, rows: pl.DataFrame, outcome: DidOutcome, weather: pl.DataFrame
) -> list[dict[str, Any]]:
    """DoWhy refuters on fixed-effect-residualised data (deviations 20 and 24).

    Residualising by the DiD fixed effects (Frisch-Waugh) means a linear-regression
    estimand reproduces the pooled coefficient. DoWhy itself runs in an isolated
    environment (``scripts/dowhy_refuters.py``).
    """
    import json
    import subprocess

    spec = specs.DidSpec(
        "pooled",
        outcome.frequency,
        weather=outcome.weather,
        weather_columns=outcome.weather_columns,
    )
    design = specs.build_design(rows, spec, weather=weather if outcome.weather else None)
    prepared = did.prepare(design)
    y = demean(
        did.adjusted_outcome(design, design.y, prepared.projection), list(design.fixed_effects)
    )
    x = prepared.x_tilde
    work = honest.WORK_DIR.parent / "dowhy"
    work.mkdir(parents=True, exist_ok=True)
    data_path, output = work / f"{key}_residualised.parquet", work / f"{key}_refuters.json"
    pl.DataFrame(
        {
            "y": y,
            "d": x[:, design.names.index("post_year1")],
            "a": x[:, design.names.index("anticipation")],
        }
    ).write_parquet(data_path)
    script = REPO_ROOT / "scripts" / "dowhy_refuters.py"
    subprocess.run(
        [
            "uv",
            "run",
            "--quiet",
            "--script",
            str(script),
            str(data_path),
            str(output),
            str(RANDOM_SEED),
        ],
        check=True,
    )
    LOG.info("DoWhy %s done", key)
    return [{"key": key, **item} for item in json.loads(output.read_text())]


# --------------------------------------------------------------------------- per outcome


def placebo_outcome_rows(key: str) -> pl.DataFrame | None:
    """Placebo outcomes from the plan: Staten Island trips (T2/S1), Verrazzano (T1)."""
    if key in ("T2", "S1"):
        zones = pl.read_csv(FINAL_DIR / "zone_groups.csv").select(
            pl.col("location_id").cast(pl.Utf8).alias("unit"), "borough"
        )
        control = panels.tlc_count_panel("crz").filter(pl.col("group") == "control")
        return (
            control.join(zones, on="unit", how="left")
            .with_columns(
                pl.when(pl.col("borough") == "Staten Island")
                .then(pl.lit("treated"))
                .otherwise(pl.lit("control"))
                .alias("group")
            )
            .drop("borough")
        )
    if key == "T1":
        control = panels.bt_builder("control", "treated")().filter(pl.col("group") == "control")
        return control.with_columns(
            pl.when(pl.col("unit").str.starts_with("Verrazzano"))
            .then(pl.lit("treated"))
            .otherwise(pl.lit("control"))
            .alias("group")
        )
    return None


CONTROL_SWAPS: dict[str, dict[str, Callable[[], pl.DataFrame]]] = {
    "T2": {
        "control: Brooklyn far zones only": lambda: panels.tlc_count_panel(
            "crz", control_boroughs=("Brooklyn",)
        ),
        "control: Queens far zones only": lambda: panels.tlc_count_panel(
            "crz", control_boroughs=("Queens",)
        ),
        "control: intermediate band": lambda: panels.tlc_count_panel(
            "crz", control_group="intermediate"
        ),
    },
    "S1": {
        "control: Brooklyn far zones only": lambda: panels.tlc_count_panel(
            "border_ring", control_boroughs=("Brooklyn",)
        ),
        "control: Queens far zones only": lambda: panels.tlc_count_panel(
            "border_ring", control_boroughs=("Queens",)
        ),
        "control: intermediate band": lambda: panels.tlc_count_panel(
            "border_ring", control_group="intermediate"
        ),
    },
    "T3": {
        "control: Brooklyn far zones only": panels.tlc_speed_builder(
            "crz", control_boroughs=("Brooklyn",)
        ),
        "control: Queens far zones only": panels.tlc_speed_builder(
            "crz", control_boroughs=("Queens",)
        ),
        "control: intermediate band": panels.tlc_speed_builder("crz", control_group="intermediate"),
        "no 20-trip minimum (unweighted)": panels.tlc_speed_builder("crz", min_trips=1),
    },
    "A3": {
        "smoke days included": panels.air_builder(
            "pm25", ["crz_core"], ["far_core"], include_smoke=True
        ),
        "Queens College Near Road added": panels.air_builder(
            "pm25", ["crz_core"], ["far_core", "far_check"]
        ),
    },
}

DOSE_RESPONSE = {"T1", "T3", "S2"}  # deviation 18(c)


def did_checks(outcome: DidOutcome, weather: pl.DataFrame, tables: dict[str, list[Any]]) -> None:
    """All checks for one DiD outcome."""
    key = outcome.key
    rows = outcome.builder()
    primary = pooled_effect(rows, outcome, weather)["estimate"]
    out = tables["checks"]
    out.append(
        row(
            key,
            "placebo date 2024-01-07",
            "placebo",
            result := placebo_date_effect(rows, outcome.frequency),
            primary,
            placebo_passes(result, primary),
        )
    )
    placebo_rows = placebo_outcome_rows(key)
    if placebo_rows is not None:
        name = (
            "placebo outcome: Staten Island trips"
            if key != "T1"
            else "placebo outcome: Verrazzano-Narrows"
        )
        result = pooled_effect(placebo_rows, outcome, weather)
        out.append(row(key, name, "placebo", result, primary, placebo_passes(result, primary)))
    pause = rows.filter(~pl.col("period").is_between(*PAUSE_WINDOW))
    result = pooled_effect(pause, outcome, weather)
    out.append(
        row(
            key,
            "June 2024 pause dropped",
            "re-estimation",
            result,
            primary,
            same_sign(result["estimate"], primary),
        )
    )
    if outcome.frequency == "day":
        calendar = pl.read_parquet(PROCESSED_DIR / "calendar.parquet").select(
            pl.col("date").alias("period"), "is_holiday_week"
        )
        no_holidays = (
            rows.join(calendar, on="period", how="left")
            .filter(~pl.col("is_holiday_week").fill_null(False))
            .drop("is_holiday_week")
        )
        result = pooled_effect(no_holidays, outcome, weather)
        out.append(
            row(
                key,
                "holiday weeks dropped",
                "re-estimation",
                result,
                primary,
                same_sign(result["estimate"], primary),
            )
        )
    if not outcome.weather:
        try:
            result = did2s_effect(rows, outcome)
            out.append(
                row(
                    key,
                    "did2s imputation estimator",
                    "re-estimation",
                    result,
                    primary,
                    same_sign(result["estimate"], primary),
                )
            )
        except Exception as error:
            out.append(
                row(
                    key,
                    "did2s imputation estimator",
                    "re-estimation",
                    {},
                    primary,
                    None,
                    f"failed: {error}",
                )
            )
    for name, build in CONTROL_SWAPS.get(key, {}).items():
        result = pooled_effect(build(), outcome, weather)
        out.append(
            row(key, name, "re-estimation", result, primary, same_sign(result["estimate"], primary))
        )
    if key in DOSE_RESPONSE:
        het = pl.read_csv(RESULTS / "heterogeneity.csv").filter(
            (pl.col("cut") == "peak_vs_overnight")
            & (pl.col("key") == key)
            & (pl.col("kind") == "level effect")
        )
        if het.height == 2:
            peak = het.filter(pl.col("level") == "peak")["estimate"].item()
            night = het.filter(pl.col("level") == "overnight")["estimate"].item()
            out.append(
                row(
                    key,
                    "dose-response: |overnight| <= |peak|",
                    "dose-response",
                    {"estimate": night},
                    peak,
                    abs(night) <= abs(peak),
                )
            )
    tables["honest"].extend(honest_rows(key, rows, outcome, weather))
    if key in DOWHY_KEYS:
        tables["dowhy"].extend(dowhy_rows(key, rows, outcome, weather))
    LOG.info("checks %s done", key)


def sc_checks(outcome: SyntheticOutcome, tables: dict[str, list[Any]]) -> None:
    """Leave-one-out donors, in-time placebo, and data variants for one SC outcome."""
    key = outcome.key
    panel = outcome.builder()
    base = synth.fit_one(panel.target, panel.donors, panel.windows, detrend=False)
    primary = base.effect_year1
    out = tables["checks"]
    loo = []
    for j in np.flatnonzero(base.weights > 1e-4):
        others = np.delete(panel.donors, j, axis=1)
        loo.append(synth.fit_one(panel.target, others, panel.windows, detrend=False).effect_year1)
    out.append(
        row(
            key,
            f"leave-one-out donors ({len(loo)} with weight > 0)",
            "re-estimation",
            {"estimate": float(np.min(loo)), "ci_high": float(np.max(loo))},
            primary,
            all(same_sign(v, primary) for v in loo),
            "estimate = smallest LOO effect; ci_high = largest",
        )
    )
    placebo = fitted_sc_estimate(panel, PLACEBO_DATE)
    out.append(
        row(
            key,
            "placebo date 2024-01-07 (pre-period only)",
            "placebo",
            {"estimate": placebo},
            primary,
            abs(placebo) < 0.5 * abs(primary),
            "no interval for SC; magnitude rule only",
        )
    )
    if key == "A1":
        variants: dict[str, Callable[[], panels.SyntheticPanel]] = {
            "all five CRZ sites (>= 2 valid per week)": lambda: panels.air_synthetic(
                "pm25", ["crz_core", "crz_other"], min_treated_sites=2
            ),
            "smoke days included": lambda: panels.air_synthetic(
                "pm25", ["crz_core"], include_smoke=True
            ),
            "donors >= 98% complete": lambda: panels.air_synthetic(
                "pm25", ["crz_core"], min_donor_completeness=0.98
            ),
        }
        for name, build in variants.items():
            variant = build()
            effect = synth.fit_one(
                variant.target, variant.donors, variant.windows, detrend=False
            ).effect_year1
            out.append(
                row(
                    key,
                    name,
                    "re-estimation",
                    {"estimate": effect},
                    primary,
                    same_sign(effect, primary),
                )
            )
    LOG.info("checks %s done", key)


def main() -> None:
    """Run every check and write the results tables."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    weather = pl.read_parquet(PROCESSED_DIR / "weather_daily.parquet")
    tables: dict[str, list[Any]] = {"checks": [], "honest": [], "dowhy": []}
    for outcome in DID_OUTCOMES:
        if outcome.family != "check":
            did_checks(outcome, weather, tables)
    for synthetic in SYNTHETIC_OUTCOMES:
        sc_checks(synthetic, tables)
    pl.DataFrame(tables["checks"], infer_schema_length=None).write_csv(
        RESULTS / "robustness_checks.csv"
    )
    pl.DataFrame(tables["honest"], infer_schema_length=None).write_csv(
        RESULTS / "honestdid_bounds.csv"
    )
    pl.DataFrame(tables["dowhy"], infer_schema_length=None).write_csv(
        RESULTS / "dowhy_refuters.csv"
    )


if __name__ == "__main__":
    main()
