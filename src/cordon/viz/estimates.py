"""Phase 3 figures: event studies and synthetic-control gaps, drawn from results/.

Every title is generated from the numbers in ``results/estimates.csv``; none is
typed by hand. Figures go to ``report/figures/phase3_*.png``.
"""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import polars as pl

from cordon.config import REPO_ROOT
from cordon.features.calendar import ANTICIPATION_START, TREATMENT
from cordon.viz import style

RESULTS = REPO_ROOT / "results"
ANTICIPATION_MIDPOINT = date(2024, 12, 10)


def bin_start(bin_number: int | None, monthly: bool) -> date:
    """Calendar date at which an event-study bin starts (anticipation: its midpoint)."""
    if bin_number is None:
        return ANTICIPATION_MIDPOINT
    if monthly:
        anchor = TREATMENT.replace(day=1) if bin_number >= 0 else ANTICIPATION_START.replace(day=1)
        month_index = anchor.year * 12 + anchor.month - 1 + bin_number
        return date(month_index // 12, month_index % 12 + 1, 1)
    anchor = TREATMENT if bin_number >= 0 else ANTICIPATION_START
    return anchor + timedelta(days=28 * bin_number)


def headline(estimates: pl.DataFrame, key: str, spec: str) -> dict[str, float | str]:
    """Return the year-1 estimate row for one outcome and specification."""
    row = estimates.filter(
        (pl.col("key") == key) & (pl.col("spec") == spec) & (pl.col("term") == "post_year1")
    )
    return row.row(0, named=True)


def describe_effect(row: dict[str, float | str]) -> str:
    """Plain-language effect with its interval, e.g. '-5.2% (95% CI -7.0 to -3.4)'."""
    unit = "%" if row["reported_unit"] == "percent" else f" {row['reported_unit']}"
    return (
        f"{float(row['reported']):+.1f}{unit} "
        f"(95% CI {float(row['reported_ci_low']):+.1f} to {float(row['reported_ci_high']):+.1f})"
    )


def interval_excludes_zero(row: dict[str, float | str]) -> bool:
    """Check whether the 95% interval lies entirely on one side of zero."""
    return float(row["ci_low"]) > 0 or float(row["ci_high"]) < 0


def plot_event_study(key: str, description: str, monthly: bool) -> None:
    """Primary and detrended event studies for one DiD outcome."""
    event = pl.read_csv(RESULTS / "event_study.csv").filter(pl.col("key") == key)
    estimates = pl.read_csv(RESULTS / "estimates.csv", infer_schema_length=None)
    specs_present = event["spec"].unique().to_list()
    primary_spec = next(s for s in specs_present if "detrended" not in s)
    detrended_spec = next(s for s in specs_present if "detrended" in s)
    pooled = headline(estimates, key, primary_spec.replace("event_study", "pooled"))
    detrended_pooled = headline(estimates, key, detrended_spec.replace("event_study", "pooled"))
    log_scale = pooled["reported_unit"] == "percent"
    scale = 100 if log_scale else 1

    figure, axis = style.new_figure(height=3.6)
    axis.axhline(0, color=style.SLATE, linewidth=0.8)
    axis.axvline(TREATMENT, color=style.SLATE, linewidth=0.8, linestyle=":")  # type: ignore[arg-type]
    for spec, color, dashed, label in (
        (primary_spec, style.TREATED, False, "Pre-registered"),
        (detrended_spec, style.CONTROL, True, "Detrended (ADR 0011)"),
    ):
        rows = event.filter(pl.col("spec") == spec).with_columns(
            pl.col("bin").cast(pl.Int64, strict=False)
        )
        bins = rows["bin"].to_list()
        starts = [bin_start(b, monthly) for b in bins]
        order = np.argsort([d.toordinal() for d in starts])
        x = np.array([starts[i] for i in order], dtype="datetime64[D]")
        y = rows["estimate"].to_numpy()[order] * scale
        low = rows["ci_low"].to_numpy()[order] * scale
        high = rows["ci_high"].to_numpy()[order] * scale
        axis.fill_between(x, low, high, color=color, alpha=style.BAND_ALPHA, linewidth=0)
        axis.plot(x, y, color=color, linestyle="--" if dashed else "-", marker="o", markersize=3)
        axis.annotate(
            label,
            (x[-1], y[-1]),
            xytext=(6, 0),
            textcoords="offset points",
            color=color,
            fontsize=8,
            va="center",
        )
    style.date_axis(axis)
    unit = "log points x 100" if log_scale else str(pooled["reported_unit"])
    axis.set_ylabel(f"Treated minus comparison ({unit})")
    agree = interval_excludes_zero(pooled) == interval_excludes_zero(detrended_pooled) and (
        np.sign(float(pooled["estimate"])) == np.sign(float(detrended_pooled["estimate"]))
    )
    style.titles(
        axis,
        f"{key}: 2025 change {describe_effect(pooled)} as pre-registered; "
        f"{describe_effect(detrended_pooled)} detrended"
        + ("" if agree else " (the specifications disagree)"),
        f"{description}. Event study relative to Sep 19-Nov 13, 2024; seasonal baseline 2023 "
        "(ADR 0012). Bands: 95% CIs. The headline number is the pooled pre-registered estimate.",
    )
    style.save(figure, f"phase3_event_study_{key.lower()}")


def plot_synthetic_gap(key: str, description: str) -> None:
    """Treated-minus-synthetic gap over time, with the placebo effect range."""
    series = pl.read_csv(RESULTS / "synthetic_control_series.csv", try_parse_dates=True).filter(
        pl.col("key") == key
    )
    estimates = pl.read_csv(RESULTS / "estimates.csv", infer_schema_length=None)
    row = headline(estimates, key, "synthetic")
    log_scale = row["reported_unit"] == "percent"
    scale = 100 if log_scale else 1
    figure, axis = style.new_figure(height=3.4)
    axis.axhline(0, color=style.SLATE, linewidth=0.8)
    axis.axvline(TREATMENT, color=style.SLATE, linewidth=0.8, linestyle=":")  # type: ignore[arg-type]
    for spec, color, dashed, label in (
        ("synthetic", style.TREATED, False, "Pre-registered"),
        ("synthetic_detrended", style.CONTROL, True, "Detrended"),
    ):
        rows = series.filter(pl.col("spec") == spec).sort("period")
        x = rows["period"].to_list()
        y = rows["gap"].to_numpy() * scale
        axis.plot(x, y, color=color, linestyle="--" if dashed else "-", linewidth=1.4)
        axis.annotate(
            label,
            (x[-1], y[-1]),
            xytext=(6, 0),
            textcoords="offset points",
            color=color,
            fontsize=8,
            va="center",
        )
    low, high = float(row["placebo_effect_low"]) * scale, float(row["placebo_effect_high"]) * scale
    post = series.filter((pl.col("spec") == "synthetic") & (pl.col("period") >= TREATMENT))
    axis.fill_between(
        post["period"].to_list(),
        low,
        high,
        color=style.CONTROL,
        alpha=style.BAND_ALPHA,
        linewidth=0,
    )
    style.date_axis(axis)
    unit = "log points x 100" if log_scale else str(row["reported_unit"])
    axis.set_ylabel(f"Treated minus synthetic ({unit})")
    value = float(row["reported"])
    suffix = "%" if log_scale else f" {row['reported_unit']}"
    p_value, min_p = float(row["p_value"]), float(row["min_attainable_p"])
    style.titles(
        axis,
        f"{key}: year-1 gap {value:+.1f}{suffix}; placebo rank p = {p_value:.2f} "
        f"(smallest possible {min_p:.2f})",
        f"{description}. Grey band after tolling: 2.5th-97.5th percentile of placebo (untreated "
        f"donor) year-1 effects. Pre-period fit "
        f"{'passes' if row['fit_ok'] in (True, 'true') else 'fails'} the pre-registered "
        "RMSPE check.",
    )
    style.save(figure, f"phase3_synthetic_{key.lower()}")


def main() -> None:
    """Draw every Phase 3 figure."""
    from cordon.designs.run import DID_OUTCOMES, SYNTHETIC_OUTCOMES

    style.apply_style()
    for outcome in DID_OUTCOMES:
        if outcome.family != "check":
            plot_event_study(outcome.key, outcome.description, outcome.frequency == "month")
    for synthetic in SYNTHETIC_OUTCOMES:
        plot_synthetic_gap(synthetic.key, synthetic.description)


if __name__ == "__main__":
    main()
