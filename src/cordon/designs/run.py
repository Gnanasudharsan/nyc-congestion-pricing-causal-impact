"""Run every Phase 3 design and write the results tables in ``results/``.

Scope (analysis plan sections 3-5; ADR 0011 amendment):
- **Primary outcomes:** T1, T2, T3, S1 (DiD) and R1, A1 (synthetic control). Their
  pre-registered p-values are Holm-adjusted together.
- **Non-spillover secondary outcomes with Phase 2 panels:** T5 (service-type
  splits), R2, R3 (DiD), A3 (weather-adjusted DiD), R4, A4 (synthetic control).
- **Not here:** the spillover secondaries S2-S5 and A2 (Phase 4), and secondary
  outcomes that need data not yet built: T4, T6, R5, R6. BH q-values are
  computed once each secondary family is complete (Phase 5); Phase 3 reports
  unadjusted secondary p-values.

Every DiD is estimated as:
- the pooled pre-registered specification (headline, post year 1);
- the extended window (2026 onward as its own term);
- the event study (2023 seasonal baseline, relative to the reference window,
  deviation 6);
- the detrended secondary specification (ADR 0011).

Every synthetic control is estimated plain and detrended.

Run: ``python -m cordon.designs.run`` (about 20-30 minutes).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from typing import Any

import numpy as np
import polars as pl

from cordon.config import PROCESSED_DIR, RANDOM_SEED, REPO_ROOT
from cordon.designs import did, multiple, panels, specs, synth
from cordon.designs.windows import EXTENDED_START

LOG = logging.getLogger(__name__)
RESULTS_DIR = REPO_ROOT / "results"
BOOTSTRAP_DRAWS = 9_999


@dataclass(frozen=True)
class DidOutcome:
    """A DiD outcome from the analysis plan."""

    key: str
    family: str  # "primary" or "secondary"
    description: str
    builder: Callable[[], pl.DataFrame]
    frequency: str = "day"
    log_scale: bool = True
    unit_label: str = "log points"
    weather: bool = False
    weather_columns: tuple[str, ...] = specs.WEATHER_COLUMNS
    primary_inference: str = "cluster"  # "cluster" or "randomization"
    bootstrap: bool = True  # wild cluster bootstrap check
    clusters_label: str = "units"


@dataclass(frozen=True)
class SyntheticOutcome:
    """A synthetic-control outcome from the analysis plan."""

    key: str
    family: str
    description: str
    builder: Callable[[], panels.SyntheticPanel]
    log_scale: bool = True
    unit_label: str = "log points"


DID_OUTCOMES = [
    DidOutcome(
        "T1",
        "primary",
        "Crossings at CRZ-feeding MTA tunnels vs control bridges",
        panels.bt_builder("control", "treated"),
        primary_inference="randomization",
        clusters_label="facilities",
    ),
    DidOutcome(
        "T2",
        "primary",
        "Taxi + FHV trips from CRZ zones vs far-control zones",
        lambda: panels.tlc_count_panel("crz"),
        clusters_label="taxi zones",
    ),
    DidOutcome(
        "T3",
        "primary",
        "Peak speed of trips within the CRZ vs within far-control zones",
        panels.tlc_speed_builder("crz"),
        clusters_label="taxi zones",
    ),
    DidOutcome(
        "S1",
        "primary",
        "Taxi + FHV trips in the border ring (both ends outside the CRZ) vs far control",
        lambda: panels.tlc_count_panel("border_ring"),
        clusters_label="taxi zones",
    ),
    DidOutcome(
        "T5a",
        "secondary",
        "Yellow-taxi trips from CRZ zones vs far control",
        lambda: panels.tlc_count_panel("crz", services=("yellow",)),
        bootstrap=False,
        clusters_label="taxi zones",
    ),
    DidOutcome(
        "T5b",
        "secondary",
        "High-volume FHV trips from CRZ zones vs far control",
        lambda: panels.tlc_count_panel("crz", services=("fhvhv",)),
        bootstrap=False,
        clusters_label="taxi zones",
    ),
    DidOutcome(
        "T5c",
        "secondary",
        "Shared-ride requests from CRZ zones vs far control",
        lambda: panels.tlc_count_panel("crz", measure="shared_requests", services=("fhvhv",)),
        bootstrap=False,
        clusters_label="taxi zones",
    ),
    DidOutcome(
        "R2",
        "secondary",
        "Subway entries at CRZ station complexes vs elsewhere",
        panels.subway_panel,
        bootstrap=False,
        clusters_label="station complexes",
    ),
    DidOutcome(
        "R3",
        "secondary",
        "Peak bus speeds on CBD route segments vs non-CBD segments",
        panels.bus_panel,
        frequency="month",
        bootstrap=False,
        clusters_label="routes",
    ),
    DidOutcome(
        "A3",
        "secondary",
        "PM2.5 at the two core CRZ sites vs Queens College sites, weather-adjusted",
        panels.air_builder("pm25", ["crz_core"], ["far_core"]),
        log_scale=False,
        unit_label="µg/m³",
        weather=True,
        primary_inference="randomization",
        clusters_label="sites",
    ),
    DidOutcome(
        "S2",
        "spillover",
        "Crossings at spillover facilities (RFK plazas, Henry Hudson) vs control bridges",
        panels.bt_builder("control", "spillover"),
        primary_inference="randomization",
        clusters_label="facilities",
    ),
    DidOutcome(
        "S3",
        "spillover",
        "Taxi + FHV trips in upper Manhattan + Bronx (both ends outside the CRZ) vs far control",
        lambda: panels.tlc_count_panel("upper_manhattan_bronx"),
        clusters_label="taxi zones",
    ),
    DidOutcome(
        "S4",
        "spillover",
        "Peak speed of trips within the border ring vs within far-control zones",
        panels.tlc_speed_builder("border_ring"),
        clusters_label="taxi zones",
    ),
    DidOutcome(
        "A2b",
        "spillover",
        "NO2 at the Bronx sites (IS 52, Pfizer Lab) vs Queens College sites, weather-adjusted",
        panels.air_builder("no2", ["spillover_no2", "spillover_no2_secondary"], ["far_core"]),
        log_scale=False,
        unit_label="ppb",
        weather=True,
        primary_inference="randomization",
        clusters_label="sites",
    ),
    DidOutcome(
        "A3_pbl",
        "check",
        "A3 with boundary-layer height added, complete-case days only (deviation 11)",
        panels.air_builder("pm25", ["crz_core"], ["far_core"]),
        log_scale=False,
        unit_label="µg/m³",
        weather=True,
        weather_columns=specs.WEATHER_COLUMNS_WITH_PBL,
        primary_inference="randomization",
        clusters_label="sites",
    ),
]

SYNTHETIC_OUTCOMES = [
    SyntheticOutcome(
        "S5",
        "spillover",
        "PM2.5 at the Cross Bronx Expwy monitor vs out-of-region monitors",
        lambda: panels.air_synthetic("pm25", ["spillover_core"]),
        log_scale=False,
        unit_label="µg/m³",
    ),
    SyntheticOutcome(
        "A2",
        "spillover",
        "NO2 at IS 52 (South Bronx) vs out-of-region monitors",
        lambda: panels.air_synthetic("no2", ["spillover_no2"]),
        log_scale=False,
        unit_label="ppb",
    ),
    SyntheticOutcome(
        "R1",
        "primary",
        "NYC subway ridership vs out-of-region rail systems",
        lambda: panels.ntd_synthetic("treated_r1", "donor_r1"),
    ),
    SyntheticOutcome(
        "A1",
        "primary",
        "PM2.5 at the two core CRZ monitors vs out-of-region monitors",
        lambda: panels.air_synthetic("pm25", ["crz_core"]),
        log_scale=False,
        unit_label="µg/m³",
    ),
    SyntheticOutcome(
        "R4",
        "secondary",
        "NYC bus ridership vs out-of-region bus systems",
        lambda: panels.ntd_synthetic("treated_r4", "donor_r4"),
    ),
    SyntheticOutcome(
        "A4",
        "secondary",
        "Daily-maximum PM2.5 at the core CRZ monitors vs out-of-region monitors",
        lambda: panels.air_synthetic("pm25", ["crz_core"], statistic="daily_max"),
        log_scale=False,
        unit_label="µg/m³",
    ),
]


@dataclass
class Tables:
    """Accumulated result rows, written to CSV at the end."""

    estimates: list[dict[str, Any]] = field(default_factory=list)
    event_study: list[dict[str, Any]] = field(default_factory=list)
    pretrends: list[dict[str, Any]] = field(default_factory=list)
    sc_series: list[dict[str, Any]] = field(default_factory=list)
    sc_weights: list[dict[str, Any]] = field(default_factory=list)
    sc_placebos: list[dict[str, Any]] = field(default_factory=list)
    crosschecks: list[dict[str, Any]] = field(default_factory=list)


# --------------------------------------------------------------------------- DiD


def describe_sample(rows: pl.DataFrame) -> dict[str, int]:
    """Count units and treated units for the results table."""
    return {
        "n_units": rows["unit"].n_unique(),
        "n_treated_units": rows.filter(pl.col("group") == "treated")["unit"].n_unique(),
    }


def scaled(outcome: DidOutcome, value: float) -> float:
    """Express a coefficient in reporting units (percent for logs)."""
    return did.percent(value) if outcome.log_scale else value


def did_row(
    outcome: DidOutcome,
    spec: specs.DidSpec,
    estimate: did.Estimate,
    name: str,
    sample: dict[str, int],
    p_value: float,
    p_method: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """One row of results/estimates.csv for a DiD coefficient."""
    low, high = did.normal_interval(estimate, name)
    value = estimate.value(name)
    return {
        "key": outcome.key,
        "family": outcome.family,
        "design": "did",
        "spec": spec.label,
        "term": name,
        "estimate": value,
        "se": estimate.se(name),
        "ci_low": low,
        "ci_high": high,
        "reported": scaled(outcome, value),
        "reported_ci_low": scaled(outcome, low),
        "reported_ci_high": scaled(outcome, high),
        "reported_unit": "percent" if outcome.log_scale else outcome.unit_label,
        "p_value": p_value,
        "p_method": p_method,
        "n_obs": estimate.n_obs,
        "n_clusters": estimate.n_clusters,
        "cluster": outcome.clusters_label,
        **sample,
        **(extra or {}),
    }


def event_study_rows(
    outcome: DidOutcome, spec: specs.DidSpec, estimate: did.Estimate
) -> list[dict[str, Any]]:
    """Event-study coefficients relative to the reference window."""
    rows = []
    for name in estimate.names:
        low, high = did.normal_interval(estimate, name)
        rows.append(
            {
                "key": outcome.key,
                "spec": spec.label,
                "term": name,
                "bin": None if name == "anticipation" else int(name.removeprefix("bin_")),
                "estimate": estimate.value(name),
                "se": estimate.se(name),
                "ci_low": low,
                "ci_high": high,
            }
        )
    return rows


def pretrend_test(
    outcome: DidOutcome,
    rows: pl.DataFrame,
    spec: specs.DidSpec,
    estimate: did.Estimate,
    weather: pl.DataFrame | None,
) -> dict[str, Any]:
    """Joint test of the 2024 pre-period bins (analysis plan section 7, check 1)."""
    pre = specs.pre_bins(estimate.names)
    f_stat, p_value = did.joint_wald_test(estimate, pre)
    method = f"cluster Wald F({len(pre)}, {estimate.n_clusters - 1})"
    if np.isnan(p_value):

        def sum_of_squares(e: did.Estimate) -> float:
            relative = specs.relative_to_reference(e)
            return float(sum(relative.value(n) ** 2 for n in specs.pre_bins(relative.names)))

        permutation = specs.randomization_inference(rows, spec, sum_of_squares, weather)
        f_stat, p_value = permutation.observed, permutation.p_value
        assignments = len(permutation.permuted)
        method = f"randomization inference, sum of squared pre bins ({assignments} assignments)"
    return {
        "key": outcome.key,
        "spec": spec.label,
        "n_pre_bins": len(pre),
        "statistic": f_stat,
        "p_value": p_value,
        "method": method,
        "flag_p_below_0_10": bool(p_value < 0.10),
        "max_abs_pre_bin": float(max(abs(estimate.value(n)) for n in pre)),
    }


def pyfixest_crosscheck(
    outcome: DidOutcome, design: did.Design, estimate: did.Estimate
) -> dict[str, Any]:
    """Re-fit the pooled primary specification with pyfixest (ADR 0005)."""
    import pandas as pd
    import pyfixest as pf

    frame = pd.DataFrame(
        {
            "y": design.y,
            "anticipation": design.x[:, design.names.index("anticipation")],
            "post_year1": design.x[:, design.names.index("post_year1")],
            "unit_season": design.fixed_effects[0],
            "period": design.fixed_effects[1],
            "cluster": design.clusters,
        }
    )
    reference = pf.feols(
        "y ~ anticipation + post_year1 | unit_season + period",
        data=frame,
        vcov={"CRV1": "cluster"},
    )
    return {
        "key": outcome.key,
        "check": "pyfixest pooled DiD",
        "ours": estimate.value("post_year1"),
        "reference": float(reference.coef()["post_year1"]),
        "ours_se": estimate.se("post_year1"),
        "reference_se": float(reference.se()["post_year1"]),
    }


def run_did(outcome: DidOutcome, tables: Tables, weather: pl.DataFrame) -> None:
    """All specifications for one DiD outcome."""
    LOG.info("%s: building panel", outcome.key)
    rows = outcome.builder()
    sample = describe_sample(rows)
    w = weather if outcome.weather else None
    adjustments = [(False, outcome.weather), (True, outcome.weather)]
    for trends, use_weather in adjustments:
        pooled = specs.DidSpec(
            "pooled",
            outcome.frequency,
            trends=trends,
            weather=use_weather,
            weather_columns=outcome.weather_columns,
        )
        design = specs.build_design(rows, pooled, weather=w)
        estimate = did.fit(design)
        LOG.info(
            "%s %s: %.4f (%.4f)",
            outcome.key,
            pooled.label,
            estimate.value("post_year1"),
            estimate.se("post_year1"),
        )
        extra: dict[str, Any] = {}
        p_value = did.wald_p_value(estimate, "post_year1")
        p_method = f"cluster-robust t({estimate.n_clusters - 1})"
        if outcome.bootstrap or outcome.primary_inference == "randomization":
            boot = did.wild_cluster_bootstrap(
                design, estimate, "post_year1", BOOTSTRAP_DRAWS, RANDOM_SEED
            )
            extra["p_wild_bootstrap"] = boot.p_value
            extra["bootstrap_draws"] = boot.draws
        if outcome.primary_inference == "randomization":
            permutation = specs.randomization_inference(
                rows, pooled, lambda e: e.value("post_year1"), w
            )
            extra["p_cluster_t"] = p_value
            p_value = permutation.p_value
            p_method = f"randomization inference ({len(permutation.permuted)} assignments)"
            extra["min_attainable_p"] = 1 / len(permutation.permuted)
        for name in ("post_year1", "anticipation"):
            tables.estimates.append(
                did_row(
                    outcome,
                    pooled,
                    estimate,
                    name,
                    sample,
                    p_value if name == "post_year1" else did.wald_p_value(estimate, name),
                    p_method
                    if name == "post_year1"
                    else f"cluster-robust t({estimate.n_clusters - 1})",
                    extra if name == "post_year1" else None,
                )
            )
        if design.adjust is None:  # pyfixest has no pre-fitted adjustment step
            tables.crosschecks.append(pyfixest_crosscheck(outcome, design, estimate))

        study = specs.DidSpec(
            "event_study",
            outcome.frequency,
            trends=trends,
            weather=use_weather,
            weather_columns=outcome.weather_columns,
        )
        es = specs.relative_to_reference(did.fit(specs.build_design(rows, study, weather=w)))
        tables.event_study.extend(event_study_rows(outcome, study, es))
        tables.pretrends.append(pretrend_test(outcome, rows, study, es, w))

    extended = specs.DidSpec(
        "pooled", outcome.frequency, window="extended", weather=outcome.weather
    )
    last_period = rows["period"].max()
    if isinstance(last_period, date) and last_period >= EXTENDED_START:
        estimate = did.fit(specs.build_design(rows, extended, weather=w))
        tables.estimates.append(
            did_row(
                outcome,
                extended,
                estimate,
                "post_extended",
                sample,
                did.wald_p_value(estimate, "post_extended"),
                f"cluster-robust t({estimate.n_clusters - 1})",
            )
        )


# --------------------------------------------------------------------------- synthetic control


def sc_scaled(outcome: SyntheticOutcome, value: float) -> float:
    """Synthetic-control effects in reporting units."""
    return did.percent(value) if outcome.log_scale else value


def run_synthetic(outcome: SyntheticOutcome, tables: Tables) -> None:
    """Plain and detrended synthetic control for one outcome."""
    LOG.info("%s: building panel", outcome.key)
    panel = outcome.builder()
    for detrend in (False, True):
        label = "synthetic_detrended" if detrend else "synthetic"
        result = synth.placebo_inference(
            panel.target, panel.donors, panel.windows, detrend, panel.donor_names
        )
        fit = result.fit
        low, high = result.placebo_range
        LOG.info("%s %s: %.4f (p = %.3f)", outcome.key, label, fit.effect_year1, result.p_value)
        for term, value in (
            ("post_year1", fit.effect_year1),
            ("anticipation", fit.effect_anticipation),
            ("post_extended", fit.effect_extended),
        ):
            if np.isnan(value):
                continue
            tables.estimates.append(
                {
                    "key": outcome.key,
                    "family": outcome.family,
                    "design": "synthetic_control",
                    "spec": label,
                    "term": term,
                    "estimate": value,
                    "reported": sc_scaled(outcome, value),
                    "reported_unit": "percent" if outcome.log_scale else outcome.unit_label,
                    "p_value": result.p_value if term == "post_year1" else None,
                    "p_method": "placebo RMSPE-ratio rank" if term == "post_year1" else None,
                    "min_attainable_p": result.min_p_value,
                    "placebo_effect_low": low if term == "post_year1" else None,
                    "placebo_effect_high": high if term == "post_year1" else None,
                    "pre_rmspe": fit.pre_rmspe,
                    "median_placebo_pre_rmspe": float(np.median(result.placebo_pre_rmspe)),
                    "fit_ok": result.fit_ok,
                    "n_donors": panel.donors.shape[1],
                    "n_pre_periods": int(panel.windows.pre.sum()),
                    "donor_cells_imputed": panel.imputed_share,
                }
            )
        for period, treated, synthetic, gap in zip(
            panel.periods, fit.treated, fit.synthetic, fit.gap, strict=True
        ):
            tables.sc_series.append(
                {
                    "key": outcome.key,
                    "spec": label,
                    "period": period,
                    "treated": treated,
                    "synthetic": synthetic,
                    "gap": gap,
                }
            )
        for name, weight in zip(panel.donor_names, fit.weights, strict=True):
            if weight > 1e-4:
                tables.sc_weights.append(
                    {"key": outcome.key, "spec": label, "donor": name, "weight": weight}
                )
        for name, ratio, effect, pre in zip(
            panel.donor_names,
            result.placebo_ratios,
            result.placebo_effects,
            result.placebo_pre_rmspe,
            strict=True,
        ):
            tables.sc_placebos.append(
                {
                    "key": outcome.key,
                    "spec": label,
                    "donor": name,
                    "rmspe_ratio": ratio,
                    "effect_year1": effect,
                    "pre_rmspe": pre,
                }
            )


# --------------------------------------------------------------------------- multiple testing


def holm_table(estimates: pl.DataFrame) -> pl.DataFrame:
    """Holm adjustment across the six primary outcomes (pre-registered p-values)."""
    primary = estimates.filter(
        (pl.col("family") == "primary")
        & (pl.col("term") == "post_year1")
        & pl.col("spec").is_in(["pooled_year1", "synthetic"])
    ).sort("key")
    adjusted = multiple.holm(primary["p_value"].to_list())
    return primary.select(
        "key", "design", "reported", "reported_unit", "p_value", "p_method", "min_attainable_p"
    ).with_columns(
        pl.Series("p_holm", adjusted),
        (pl.Series("p_holm", adjusted) <= 0.05).alias("reject_at_5pct"),
    )


SPILLOVER_FAMILY = {
    "S2": "pooled_year1",
    "S3": "pooled_year1",
    "S4": "pooled_year1",
    "S5": "synthetic",
    "A2": "synthetic",
}


def spillover_bh_table(estimates: pl.DataFrame) -> pl.DataFrame:
    """BH q-values across the spillover family S2-S5 + A2 (analysis plan section 5.3)."""
    rows = [
        estimates.filter(
            (pl.col("key") == key) & (pl.col("spec") == spec) & (pl.col("term") == "post_year1")
        )
        for key, spec in SPILLOVER_FAMILY.items()
    ]
    family = pl.concat(rows, how="diagonal_relaxed").select(
        "key", "design", "spec", "reported", "reported_unit", "p_value", "p_method"
    )
    return family.with_columns(
        pl.Series("q_bh", multiple.benjamini_hochberg(family["p_value"].to_list()))
    )


def write(tables: Tables) -> None:
    """Write every table to results/."""
    RESULTS_DIR.mkdir(exist_ok=True)
    estimates = pl.DataFrame(tables.estimates, infer_schema_length=None)
    estimates.write_csv(RESULTS_DIR / "estimates.csv")
    holm_table(estimates).write_csv(RESULTS_DIR / "primary_holm.csv")
    spillover_bh_table(estimates).write_csv(RESULTS_DIR / "spillover_bh.csv")
    for name, rows in (
        ("event_study", tables.event_study),
        ("pretrend_tests", tables.pretrends),
        ("synthetic_control_series", tables.sc_series),
        ("synthetic_control_weights", tables.sc_weights),
        ("synthetic_control_placebos", tables.sc_placebos),
        ("crosschecks", tables.crosschecks),
    ):
        pl.DataFrame(rows, infer_schema_length=None).write_csv(RESULTS_DIR / f"{name}.csv")


def main() -> None:
    """Estimate everything in scope and write results/."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    weather = pl.read_parquet(PROCESSED_DIR / "weather_daily.parquet")
    tables = Tables()
    for outcome in DID_OUTCOMES:
        run_did(outcome, tables, weather)
    for synthetic in SYNTHETIC_OUTCOMES:
        run_synthetic(synthetic, tables)
    write(tables)
    LOG.info("wrote %s", RESULTS_DIR)


if __name__ == "__main__":
    main()
