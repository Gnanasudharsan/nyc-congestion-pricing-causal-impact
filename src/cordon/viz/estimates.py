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


def plot_heterogeneity() -> None:
    """Forest plot of level effects for every heterogeneity cut."""
    import matplotlib.pyplot as plt

    table = pl.read_csv(RESULTS / "heterogeneity.csv", infer_schema_length=None).filter(
        pl.col("kind") == "level effect"
    )
    cuts = table["cut"].unique(maintain_order=True).to_list()
    figure, axes = plt.subplots(1, len(cuts), figsize=(10, 4.6), sharex=False)
    for axis, cut in zip(np.atleast_1d(axes), cuts, strict=True):
        rows = table.filter(pl.col("cut") == cut)
        labels = [f"{k} {lvl}" for k, lvl in zip(rows["key"], rows["level"], strict=True)]
        y = np.arange(len(labels))[::-1]
        axis.axvline(0, color=style.SLATE, linewidth=0.8)
        axis.hlines(
            y,
            rows["percent_ci_low"].to_numpy(),
            rows["percent_ci_high"].to_numpy(),
            color=style.TREATED,
            linewidth=1.6,
        )
        axis.plot(rows["percent"].to_numpy(), y, "o", color=style.TREATED, markersize=4)
        axis.set_yticks(y, labels, fontsize=7)
        axis.set_title(cut.replace("_", " "), fontsize=9)
        axis.tick_params(axis="x", labelsize=7)
    spans = (table["percent_ci_high"] - table["percent_ci_low"]).to_numpy()
    figure.suptitle(
        f"Heterogeneity: 2025 effects by level, {len(table)} estimates; median 95% CI width "
        f"{float(np.median(spans)):.1f} percentage points",
        x=0.01,
        ha="left",
        fontsize=11,
        fontweight="bold",
        color=style.INK,
    )
    figure.text(
        0.01,
        0.92,
        "Percent change vs comparison group, 95% CIs. Differences between "
        "levels, with BH q-values, are in docs/results-phase4.md.",
        fontsize=8,
        color=style.SLATE,
    )
    figure.tight_layout(rect=(0, 0, 1, 0.9), h_pad=0.5)
    style.save(figure, "phase4_heterogeneity")


def plot_zone_equity() -> None:
    """Shrunk zone spillover effects against each equity covariate (exploratory)."""
    import matplotlib.pyplot as plt

    from cordon.designs.zone_effects import COVARIATES

    zones = pl.read_csv(RESULTS / "zone_spillover_effects.csv")
    assoc = pl.read_csv(RESULTS / "equity_associations.csv", infer_schema_length=None).filter(
        pl.col("model") == "bivariate"
    )
    axis_labels = {
        "median_income_popweighted": "Median household income ($000)",
        "share_no_vehicle": "Households without a vehicle (share)",
        "poverty_rate": "Poverty rate",
        "asthma_ed_rate_adults": "Adult asthma ED visits per 10,000",
    }
    figure, axes = plt.subplots(1, len(COVARIATES), figsize=(10.5, 3.6), sharey=True)
    figure.set_layout_engine(None)
    for axis, column in zip(axes, COVARIATES, strict=True):
        for design, color, name in (
            ("S1", style.SPILLOVER, "Border ring (S1)"),
            ("S3", style.CONTROL, "Upper Manhattan + Bronx (S3)"),
        ):
            part = zones.filter((pl.col("design") == design) & pl.col(column).is_not_null())
            x = part[column].to_numpy()
            if column == "median_income_popweighted":
                x = x / 1000  # thousands of dollars keeps tick labels short
            sizes = 6 + 40 * part["population"].to_numpy() / zones["population"].max()
            axis.scatter(
                x,
                part["shrunk_percent"].to_numpy(),
                s=sizes,
                color=color,
                alpha=0.7,
                linewidths=0,
                label=name,
            )
        r = assoc.filter(pl.col("covariate") == column)["weighted_correlation"].item()
        axis.set_title(f"weighted r = {r:+.2f}", fontsize=8, color=style.SLATE)
        axis.set_xlabel(axis_labels[column], fontsize=8)
        axis.axhline(0, color=style.SLATE, linewidth=0.8)
        axis.tick_params(labelsize=7)
    axes[0].set_ylabel("Shrunk 2025 effect (%)", fontsize=8)
    handles, labels = axes[0].get_legend_handles_labels()
    figure.legend(
        handles,
        labels,
        fontsize=8,
        frameon=False,
        loc="upper right",
        ncol=2,
        bbox_to_anchor=(0.99, 0.86),
    )
    correlations = assoc["weighted_correlation"].to_numpy()
    figure.text(
        0.01,
        0.95,
        f"Zone spillover effects and neighbourhood characteristics: weighted correlations "
        f"from {correlations.min():+.2f} to {correlations.max():+.2f} (exploratory, not causal)",
        fontsize=10.5,
        fontweight="bold",
        color=style.INK,
    )
    figure.text(
        0.01,
        0.885,
        "Each dot is a taxi zone, sized by population. Effects: empirical-Bayes 2025 change in "
        "trips with both ends outside the CRZ.",
        fontsize=8,
        color=style.SLATE,
    )
    figure.subplots_adjust(left=0.06, right=0.99, top=0.74, bottom=0.15, wspace=0.12)
    style.save(figure, "phase4_zone_equity")


def plot_honestdid() -> None:
    """Relative-magnitudes robust CIs against M-bar for each DiD outcome."""
    import matplotlib.pyplot as plt

    bounds = pl.read_csv(RESULTS / "honestdid_bounds.csv", infer_schema_length=None).filter(
        pl.col("lb").is_not_null()
    )
    keys = (
        bounds.filter(pl.col("restriction") == "relative_magnitudes")["key"]
        .unique(maintain_order=True)
        .to_list()
    )
    columns = 5
    rows_n = int(np.ceil(len(keys) / columns))
    figure, axes = plt.subplots(rows_n, columns, figsize=(11, 2.3 * rows_n + 0.8), squeeze=False)
    figure.set_layout_engine(None)
    excluded = 0
    for axis, key in zip(axes.ravel(), keys, strict=False):
        part = bounds.filter(pl.col("key") == key)
        original = part.filter(pl.col("restriction") == "original").row(0, named=True)
        rm = part.filter(pl.col("restriction") == "relative_magnitudes").sort("parameter")
        x = [0.0, *rm["parameter"].to_list()]
        low = [original["lb"], *rm["lb"].to_list()]
        high = [original["ub"], *rm["ub"].to_list()]
        scale = 100.0
        axis.vlines(
            x, np.array(low) * scale, np.array(high) * scale, color=style.TREATED, linewidth=2
        )
        axis.axhline(0, color=style.SLATE, linewidth=0.8)
        axis.axvline(1.0, color=style.SLATE, linewidth=0.6, linestyle=":")
        at_one = rm.filter(pl.col("parameter") == 1.0).row(0, named=True)
        holds = not (at_one["lb"] <= 0 <= at_one["ub"])
        excluded += int(holds)
        axis.set_title(f"{key}: {'excludes' if holds else 'includes'} 0 at M̄ = 1", fontsize=8)
        axis.tick_params(labelsize=7)
    for axis in axes.ravel()[len(keys) :]:
        axis.set_visible(False)
    figure.text(
        0.01,
        0.97,
        f"HonestDiD: {excluded} of {len(keys)} DiD estimates keep a "
        "robust 95% CI that excludes zero when post-period violations may be as large as "
        "the largest pre-period one (M̄ = 1)",
        fontsize=10.5,
        fontweight="bold",
        color=style.INK,
        va="top",
    )
    figure.text(
        0.01,
        0.92,
        "Relative-magnitudes robust CIs (x100: log points or levels) for "
        "the 2025 event-study average; M̄ = 0 assumes exact parallel trends.",
        fontsize=8,
        color=style.SLATE,
        va="top",
    )
    figure.subplots_adjust(left=0.05, right=0.99, top=0.82, bottom=0.08, hspace=0.6, wspace=0.3)
    style.save(figure, "phase5_honestdid")


def main() -> None:
    """Draw every Phase 3, 4, and 5 figure."""
    from cordon.designs.run import DID_OUTCOMES, SYNTHETIC_OUTCOMES

    style.apply_style()
    for outcome in DID_OUTCOMES:
        if outcome.family != "check":
            plot_event_study(outcome.key, outcome.description, outcome.frequency == "month")
    for synthetic in SYNTHETIC_OUTCOMES:
        plot_synthetic_gap(synthetic.key, synthetic.description)
    if (RESULTS / "heterogeneity.csv").exists():
        plot_heterogeneity()
    if (RESULTS / "zone_spillover_effects.csv").exists():
        plot_zone_equity()
    if (RESULTS / "honestdid_bounds.csv").exists():
        plot_honestdid()


if __name__ == "__main__":
    main()
