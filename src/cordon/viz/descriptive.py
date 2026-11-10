"""Phase 2 descriptive figures: raw trends, seasonality, and pre-trend plots.

Pre-registration discipline (ADR 0002):

- **Pre-trend plots** for every planned comparison use **pre-period data only**
  (2023-01-01 to 2024-11-13). They never show a treated-vs-control contrast after
  the program was announced.
- **Before/after raw-trend plots** show **citywide or system-wide aggregates
  only**, never a treated group set against a control.

Every figure title is generated from statistics computed on the plotted data:
the pre-period correlation of the two weekly series, and the slope of the gap
between them. No number is typed by hand. Each figure's data is also written to
``data/final/figures/<name>.csv`` for the website.

Method for the comparison series: each unit's outcome (log, or level for
pollution) is centred on its own pre-period mean. The group's weekly value is
the mean of its units' centred values. Centring removes level differences
between units, so the plot shows whether the groups' *changes* moved together.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

import matplotlib.dates as mdates
import numpy as np
import polars as pl

from cordon.config import FINAL_DIR, PROCESSED_DIR
from cordon.designs.panels import (
    air_builder,
    bt_builder,
    bus_builder,
    ntd_builder,
    subway_builder,
    tlc_speed_builder,
    tlc_trips_builder,
    to_weekly,
)
from cordon.features.calendar import ANTICIPATION_START, PRE_START, TREATMENT
from cordon.viz import style

LOG = logging.getLogger(__name__)
FIGURE_DATA_DIR = FINAL_DIR / "figures"
PRE_END = date(2024, 11, 13)


@dataclass(frozen=True)
class Comparison:
    """One planned comparison from the analysis plan."""

    key: str  # outcome ID from the plan, e.g. "T1"
    name: str  # file name
    treated_label: str
    control_label: str
    unit_label: str  # what the y-axis measures
    treated_color: str
    builder: Callable[[], pl.DataFrame]  # returns period, group (treated/control), unit, value
    frequency: str = "week"  # plotted frequency: "week" (built from daily rows) or "month"
    log_scale: bool = True


def centre_on_pre_period(frame: pl.DataFrame) -> pl.DataFrame:
    """Subtract each unit's pre-period mean, keeping pre-period rows only."""
    pre = frame.filter(pl.col("period").is_between(PRE_START, PRE_END))
    return pre.with_columns(
        (pl.col("value") - pl.col("value").mean().over("unit")).alias("centred")
    )


def group_series(frame: pl.DataFrame) -> pl.DataFrame:
    """Mean of centred unit values per group and period."""
    return (
        centre_on_pre_period(frame)
        .group_by("period", "group")
        .agg(pl.col("centred").mean().alias("value"), pl.col("unit").n_unique().alias("units"))
        .sort("period", "group")
    )


COMPARISONS = [
    Comparison(
        "T1",
        "pretrend_t1_bt_tunnels",
        "CRZ-feeding tunnels",
        "Control bridges",
        "log crossings, vs own pre-period mean",
        style.TREATED,
        bt_builder("control", "treated"),
    ),
    Comparison(
        "S2",
        "pretrend_s2_bt_spillover",
        "Spillover bridges",
        "Control bridges",
        "log crossings, vs own pre-period mean",
        style.SPILLOVER,
        bt_builder("control", "spillover"),
    ),
    Comparison(
        "T2",
        "pretrend_t2_tlc_trips_crz",
        "CRZ taxi zones",
        "Far-control zones",
        "log(1 + trips), vs own pre-period mean",
        style.TREATED,
        tlc_trips_builder("crz"),
    ),
    Comparison(
        "S1",
        "pretrend_s1_tlc_trips_ring",
        "Border-ring zones",
        "Far-control zones",
        "log(1 + trips), vs own pre-period mean",
        style.SPILLOVER,
        tlc_trips_builder("border_ring"),
    ),
    Comparison(
        "S3",
        "pretrend_s3_tlc_trips_upper",
        "Upper Manhattan + Bronx",
        "Far-control zones",
        "log(1 + trips), vs own pre-period mean",
        style.SPILLOVER,
        tlc_trips_builder("upper_manhattan_bronx"),
    ),
    Comparison(
        "T3",
        "pretrend_t3_tlc_speed_crz",
        "Trips within the CRZ",
        "Trips within far-control zones",
        "log mph, vs own pre-period mean",
        style.TREATED,
        tlc_speed_builder("crz"),
    ),
    Comparison(
        "S4",
        "pretrend_s4_tlc_speed_ring",
        "Trips within the border ring",
        "Trips within far-control zones",
        "log mph, vs own pre-period mean",
        style.SPILLOVER,
        tlc_speed_builder("border_ring"),
    ),
    Comparison(
        "R1",
        "pretrend_r1_ntd_subway",
        "NYC subway",
        "Other US rail systems (mean)",
        "log monthly trips, vs own pre-period mean",
        style.TREATED,
        ntd_builder("treated_r1", "donor_r1"),
        frequency="month",
    ),
    Comparison(
        "R4",
        "pretrend_r4_ntd_bus",
        "NYC buses",
        "Other US bus systems (mean)",
        "log monthly trips, vs own pre-period mean",
        style.TREATED,
        ntd_builder("treated_r4", "donor_r4"),
        frequency="month",
    ),
    Comparison(
        "R2",
        "pretrend_r2_subway_stations",
        "CRZ stations",
        "Stations elsewhere",
        "log entries, vs own pre-period mean",
        style.TREATED,
        subway_builder,
    ),
    Comparison(
        "R3",
        "pretrend_r3_bus_speeds",
        "Bus service in the CBD",
        "Bus service elsewhere",
        "log mph, vs own pre-period mean",
        style.TREATED,
        bus_builder,
        frequency="month",
    ),
    Comparison(
        "A1",
        "pretrend_a1_pm25_donors",
        "CRZ monitors (2)",
        "Out-of-region monitors",
        "PM2.5 µg/m³, vs own pre-period mean",
        style.TREATED,
        air_builder("pm25", ["crz_core"], ["donor"]),
        log_scale=False,
    ),
    Comparison(
        "A3",
        "pretrend_a3_pm25_nyc",
        "CRZ monitors (2)",
        "Queens College monitors",
        "PM2.5 µg/m³, vs own pre-period mean",
        style.TREATED,
        air_builder("pm25", ["crz_core"], ["far_core"]),
        log_scale=False,
    ),
    Comparison(
        "A2",
        "pretrend_a2_no2_bronx",
        "South Bronx (IS 52)",
        "Out-of-region monitors",
        "NO2 ppb, vs own pre-period mean",
        style.SPILLOVER,
        air_builder("no2", ["spillover_no2"], ["donor"]),
        log_scale=False,
    ),
    Comparison(
        "S5",
        "pretrend_s5_pm25_cross_bronx",
        "Cross Bronx Expwy",
        "Out-of-region monitors",
        "PM2.5 µg/m³, vs own pre-period mean",
        style.SPILLOVER,
        air_builder("pm25", ["spillover_core"], ["donor"]),
        log_scale=False,
    ),
]


# --------------------------------------------------------------------------- statistics


def pre_period_stats(series: pl.DataFrame, frequency: str) -> dict[str, float]:
    """Correlation of the two groups' series and the yearly trend in their gap."""
    wide = series.pivot(on="group", index="period", values="value").drop_nulls().sort("period")
    treated = wide["treated"].to_numpy()
    control = wide["control"].to_numpy()
    gap = treated - control
    years = np.array([(p - wide["period"][0]).days / 365.25 for p in wide["period"]], dtype=float)
    slope, intercept = np.polyfit(years, gap, 1)
    residuals = gap - (slope * years + intercept)
    # Plain OLS standard error of the slope; serial correlation makes this optimistic.
    se = float(np.sqrt(residuals.var(ddof=2) / ((years - years.mean()) ** 2).sum()))
    return {
        "periods": float(len(wide)),
        "correlation": float(np.corrcoef(treated, control)[0, 1]),
        "gap_slope_per_year": float(slope),
        "gap_slope_se": se,
        "frequency_is_month": float(frequency == "month"),
    }


def describe(comparison: Comparison, stats: dict[str, float]) -> tuple[str, str]:
    """Generate the takeaway title and subtitle from the computed statistics."""
    r = stats["correlation"]
    if r >= 0.8:
        verb = "moved closely together"
    elif r >= 0.5:
        verb = "moved broadly together"
    else:
        verb = "did not move together"
    title = (
        f"{comparison.key}: before tolling, {style.sentence_case(comparison.treated_label)} "
        f"and {style.sentence_case(comparison.control_label)} {verb}"
    )
    scale = 100 if comparison.log_scale else 1
    unit = "log points" if comparison.log_scale else comparison.unit_label.split(",")[0]
    slope = stats["gap_slope_per_year"] * scale
    se = stats["gap_slope_se"] * scale
    subtitle = (
        f"Pre-period only (Jan 2023 to Nov 13, 2024), {int(stats['periods'])} "
        f"{'months' if stats['frequency_is_month'] else 'weeks'}. Correlation {r:.2f}; "
        f"gap trend {slope:+.1f} {unit}/yr (naive SE {se:.1f}). {comparison.unit_label}."
    )
    return title, subtitle


def with_gaps(part: pl.DataFrame, frequency: str) -> pl.DataFrame:
    """Insert empty periods so plotted lines break at missing data instead of bridging it."""
    interval = "1mo" if frequency == "month" else "1w"
    first, last = part["period"].min(), part["period"].max()
    if not isinstance(first, date) or not isinstance(last, date):
        raise TypeError("period column must hold dates")
    periods = pl.date_range(first, last, interval, eager=True)
    full = pl.DataFrame({"period": periods})
    return full.join(part.select("period", "value"), on="period", how="left").sort("period")


# --------------------------------------------------------------------------- plots


def plot_comparison(comparison: Comparison) -> dict[str, float]:
    """Draw and save one pre-trend figure; return its statistics."""
    rows = comparison.builder()
    if comparison.frequency == "week":
        rows = to_weekly(rows)
    series = group_series(rows)
    stats = pre_period_stats(series, comparison.frequency)
    FIGURE_DATA_DIR.mkdir(parents=True, exist_ok=True)
    series.write_csv(FIGURE_DATA_DIR / f"{comparison.name}.csv")

    figure, axis = style.new_figure()
    scale = 100 if comparison.log_scale else 1
    for group, color, label in (
        ("control", style.CONTROL, comparison.control_label),
        ("treated", comparison.treated_color, comparison.treated_label),
    ):
        part = with_gaps(series.filter(pl.col("group") == group), comparison.frequency)
        values = part["value"].to_numpy() * scale
        axis.plot(part["period"].to_list(), values, color=color, label=label)
        last = part.drop_nulls("value")
        axis.annotate(
            label,
            (last["period"][-1], last["value"][-1] * scale),
            xytext=(6, 0),
            textcoords="offset points",
            color=style.INK,
            fontsize=8,
            va="center",
        )
    axis.axhline(0, color=style.SLATE, linewidth=0.8)
    axis.set_ylabel(
        comparison.unit_label.replace("log", "100 x log")
        if comparison.log_scale
        else comparison.unit_label
    )
    axis.legend(loc="lower left", fontsize=8, ncols=2)
    axis.margins(x=0.02)
    title, subtitle = describe(comparison, stats)
    style.date_axis(axis)
    style.titles(axis, title, subtitle)
    style.save(figure, comparison.name)
    return {**stats, **plot_aligned_gap(comparison, series)}


def aligned_gap(series: pl.DataFrame, frequency: str) -> pl.DataFrame:
    """Seasonally aligned gap: (treated - control) in 2024 minus the same week/month in 2023.

    The pre-registered DiD includes unit x week-of-year fixed effects, so what
    parallel trends requires is that this aligned gap is flat around zero, not
    that the raw series move together week to week.
    """
    slot = pl.col("period").dt.month() if frequency == "month" else pl.col("period").dt.week()
    gaps = (
        series.pivot(on="group", index="period", values="value")
        .drop_nulls()
        .with_columns(
            (pl.col("treated") - pl.col("control")).alias("gap"),
            pl.col("period").dt.year().alias("year"),
            slot.alias("slot"),
        )
    )
    first = gaps.filter(pl.col("year") == 2023).select("slot", pl.col("gap").alias("gap_2023"))
    second = gaps.filter(pl.col("year") == 2024).select(
        "period", "slot", pl.col("gap").alias("gap_2024")
    )
    return (
        second.join(first, on="slot", how="inner")
        .with_columns((pl.col("gap_2024") - pl.col("gap_2023")).alias("aligned_gap"))
        .sort("period")
    )


def plot_aligned_gap(comparison: Comparison, series: pl.DataFrame) -> dict[str, float]:
    """Figure of the seasonally aligned gap for one comparison; returns its summary."""
    aligned = aligned_gap(series, comparison.frequency)
    aligned.write_csv(FIGURE_DATA_DIR / f"aligned_{comparison.name}.csv")
    scale = 100 if comparison.log_scale else 1
    values = aligned["aligned_gap"].to_numpy() * scale
    mean, sd = float(values.mean()), float(values.std(ddof=1))
    figure, axis = style.new_figure(height=2.8)
    axis.axhline(0, color=style.SLATE, linewidth=0.8)
    axis.plot(aligned["period"].to_list(), values, color=comparison.treated_color)
    style.date_axis(axis)
    unit = "log points" if comparison.log_scale else comparison.unit_label.split(",")[0]
    axis.set_ylabel(f"2024 gap minus 2023 gap ({unit})")
    within = "stayed near zero" if abs(mean) < 0.5 * sd else "shifted away from zero"
    style.titles(
        axis,
        f"{comparison.key}: comparing each 2024 week with the same week of 2023, the gap {within}",
        f"Seasonally aligned treated-minus-control gap, pre-period only. Mean {mean:+.1f}, "
        f"SD {sd:.1f} {unit} over {len(values)} "
        f"{'months' if comparison.frequency == 'month' else 'weeks'}. This is the comparison the "
        "pre-registered design's week-of-year fixed effects make.",
    )
    style.save(figure, f"aligned_{comparison.name}")
    return {"aligned_mean": mean, "aligned_sd": sd, "aligned_periods": float(len(values))}


def plot_citywide_trends() -> None:
    """Before/after raw trends of citywide aggregates only (no treated vs control)."""
    panels: list[tuple[str, str, pl.DataFrame]] = []
    bt = (
        pl.read_parquet(PROCESSED_DIR / "bt_facility_day.parquet")
        .group_by("date")
        .agg(pl.col("crossings").sum().alias("value"))
    )
    panels.append(("trend_bt_all_facilities", "All MTA bridge and tunnel crossings, per day", bt))
    tlc_path = PROCESSED_DIR / "tlc_zone_day.parquet"
    if tlc_path.exists():
        tlc = pl.read_parquet(tlc_path).group_by("date").agg(pl.col("trips").sum().alias("value"))
        panels.append(("trend_tlc_all_trips", "All taxi and for-hire trips citywide, per day", tlc))
    subway_path = PROCESSED_DIR / "subway_station_day.parquet"
    if subway_path.exists():
        subway = (
            pl.read_parquet(subway_path)
            .group_by("date")
            .agg(pl.col("entries").sum().alias("value"))
        )
        panels.append(
            ("trend_subway_all_entries", "All subway entries systemwide, per day", subway)
        )

    for name, label, frame in panels:
        frame = frame.sort("date").with_columns(
            pl.col("value").rolling_mean(window_size=28).alias("smooth")
        )
        frame.write_csv(FIGURE_DATA_DIR / f"{name}.csv")
        figure, axis = style.new_figure()
        axis.plot(
            frame["date"].to_list(), frame["value"].to_list(), color=style.LINE, linewidth=0.8
        )
        axis.plot(frame["date"].to_list(), frame["smooth"].to_list(), color=style.INK)
        events = ((ANTICIPATION_START, "Revived at $9", -10), (TREATMENT, "Tolling starts", -22))
        for when, text, offset in events:
            x = float(mdates.date2num(when))  # type: ignore[no-untyped-call]
            axis.axvline(x, color=style.SLATE, linewidth=0.8, linestyle=(0, (2, 2)))
            axis.annotate(
                text,
                (x, 1.0),
                xycoords=("data", "axes fraction"),
                xytext=(3, offset),
                textcoords="offset points",
                fontsize=7.5,
                color=style.SLATE,
            )
        axis.yaxis.set_major_formatter(
            lambda v, _: f"{v / 1e6:.1f}M" if v >= 1e6 else f"{v / 1e3:.0f}k"
        )
        style.date_axis(axis)
        last_year = float(frame.filter(pl.col("date").dt.year() == 2025)["value"].sum())
        prior_year = float(frame.filter(pl.col("date").dt.year() == 2024)["value"].sum())
        change = 100 * (last_year / prior_year - 1)
        style.titles(
            axis,
            f"{label.split(',')[0]}: 2025 total {change:+.1f}% vs 2024 (raw, not causal)",
            "Grey: daily values. Ink: 28-day mean. Citywide aggregate; no comparison group, "
            "no controls for weather, calendar, or trends.",
        )
        style.save(figure, name)


def plot_seasonality() -> None:
    """B&T weekly crossings by ISO week, one line per pre-period year."""
    bt = pl.read_parquet(PROCESSED_DIR / "bt_facility_day.parquet").filter(
        pl.col("date").dt.year().is_in([2023, 2024])
    )
    weekly_totals = (
        bt.group_by(pl.col("date").dt.year().alias("year"), pl.col("date").dt.week().alias("week"))
        .agg(pl.col("crossings").sum(), pl.col("date").n_unique().alias("days"))
        .filter(pl.col("days") == 7)
        .sort("year", "week")
    )
    weekly_totals.write_csv(FIGURE_DATA_DIR / "seasonality_bt.csv")
    figure, axis = style.new_figure()
    for year, color in ((2023, style.CONTROL), (2024, style.INK)):
        part = weekly_totals.filter(pl.col("year") == year)
        axis.plot(
            part["week"].to_list(),
            (part["crossings"] / 1e6).to_list(),
            color=color,
            label=str(year),
        )
        axis.annotate(
            str(year),
            (part["week"][-1], part["crossings"][-1] / 1e6),
            xytext=(4, 0),
            textcoords="offset points",
            fontsize=8,
            color=style.INK,
            va="center",
        )
    by_week = (
        weekly_totals.filter(pl.col("year") == 2023)
        .select("week", pl.col("crossings").alias("y2023"))
        .join(
            weekly_totals.filter(pl.col("year") == 2024).select(
                "week", pl.col("crossings").alias("y2024")
            ),
            on="week",
        )
    )
    corr = float(np.corrcoef(by_week["y2023"].to_numpy(), by_week["y2024"].to_numpy())[0, 1])
    axis.set_xlabel("ISO week of year")
    axis.set_ylabel("crossings per week (millions)")
    axis.legend(loc="lower center", ncols=2, fontsize=8)
    style.titles(
        axis,
        f"Crossings follow the same seasonal shape each year (r = {corr:.2f})",
        "MTA bridges and tunnels, all facilities, full weeks only, pre-period years. "
        "This is why every design compares each unit with itself in the same week.",
    )
    style.save(figure, "seasonality_bt")


def main() -> None:
    """Build every figure whose inputs exist; record statistics."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    FIGURE_DATA_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    for comparison in COMPARISONS:
        try:
            stats = plot_comparison(comparison)
        except FileNotFoundError as error:
            LOG.warning("skipped %s: %s", comparison.key, error)
            continue
        rows.append({"key": comparison.key, "figure": comparison.name, **stats})
        LOG.info("%s: r=%.2f", comparison.key, stats["correlation"])
    pl.DataFrame(rows).write_csv(FIGURE_DATA_DIR / "pretrend_stats.csv")
    plot_citywide_trends()
    plot_seasonality()


if __name__ == "__main__":
    main()
