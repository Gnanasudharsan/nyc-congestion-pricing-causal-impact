"""Estimation panels: one function per outcome, returning long rows.

Every builder returns columns ``period``, ``group`` ("treated"/"control"),
``unit``, ``value`` (and sometimes ``cluster``). The group definitions are the
pre-registered ones (analysis plan sections 2-5; ADR 0010). Phase 2 descriptive
figures use the same builders, so the figures and the estimates rest on the
same data.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np
import polars as pl

from cordon.config import FINAL_DIR, PROCESSED_DIR
from cordon.designs import synth, windows
from cordon.features.calendar import ANTICIPATION_START


def daily_rows(frame: pl.DataFrame, value: str, unit: str, group: str) -> pl.DataFrame:
    """Standardise a daily unit panel to columns period, group, unit, value."""
    return frame.select(
        pl.col("date").alias("period"),
        pl.col(group).alias("group"),
        pl.col(unit).cast(pl.Utf8).alias("unit"),
        pl.col(value).alias("value"),
    )


def to_weekly(rows: pl.DataFrame) -> pl.DataFrame:
    """Aggregate daily unit rows to weeks (mean of daily values; weeks with >= 5 days)."""
    return (
        rows.with_columns(pl.col("period").dt.truncate("1w"))
        .group_by("period", "group", "unit")
        .agg(pl.col("value").mean(), pl.len().alias("days"))
        .filter(pl.col("days") >= 5)
        .drop("days")
    )


# --------------------------------------------------------------------------- builders


def bt_builder(control_group: str, treated_group: str) -> Callable[[], pl.DataFrame]:
    """B&T: log daily crossings per facility, weekly, excluding flagged closures."""

    def build() -> pl.DataFrame:
        panel = pl.read_parquet(PROCESSED_DIR / "bt_facility_day.parquet").filter(
            ~pl.col("is_closure") & pl.col("facility_group").is_in([control_group, treated_group])
        )
        panel = panel.with_columns(
            pl.col("crossings").log().alias("log_crossings"),
            pl.when(pl.col("facility_group") == treated_group)
            .then(pl.lit("treated"))
            .otherwise(pl.lit("control"))
            .alias("role"),
        )
        return daily_rows(panel, "log_crossings", "facility", "role")

    return build


def tlc_trips_builder(treated_group: str) -> Callable[[], pl.DataFrame]:
    """TLC: log(1 + daily trips) by pickup zone, using the plan's counting rules."""

    def build() -> pl.DataFrame:
        groups = pl.read_csv(FINAL_DIR / "zone_groups.csv").select(
            pl.col("location_id").alias("pu_location_id"), pl.col("group").alias("pu_group")
        )
        panel = pl.read_parquet(PROCESSED_DIR / "tlc_zone_day.parquet").join(
            groups, on="pu_location_id", how="inner"
        )
        if treated_group == "crz":
            treated = panel.filter(pl.col("pu_group") == "crz")  # all trips from CRZ zones
        else:
            treated = panel.filter(
                (pl.col("pu_group") == treated_group) & (pl.col("do_group") != "crz")
            )
        control = panel.filter(
            (pl.col("pu_group") == "far_control") & (pl.col("do_group") != "crz")
        )
        daily = (
            pl.concat(
                [
                    treated.with_columns(pl.lit("treated").alias("role")),
                    control.with_columns(pl.lit("control").alias("role")),
                ]
            )
            .group_by("date", "pu_location_id", "role")
            .agg(pl.col("trips").sum())
        )
        daily = daily.with_columns((pl.col("trips") + 1).log().alias("log_trips"))
        return daily_rows(daily, "log_trips", "pu_location_id", "role")

    return build


def tlc_speed_builder(treated_group: str) -> Callable[[], pl.DataFrame]:
    """TLC: log distance-weighted speed of same-group trips, peak hours, by pickup zone."""

    def build() -> pl.DataFrame:
        groups = pl.read_csv(FINAL_DIR / "zone_groups.csv").select(
            pl.col("location_id").alias("pu_location_id"), pl.col("group").alias("pu_group")
        )
        panel = (
            pl.read_parquet(PROCESSED_DIR / "tlc_zone_day.parquet")
            .join(groups, on="pu_location_id", how="inner")
            .filter(pl.col("is_peak") & (pl.col("pu_group") == pl.col("do_group")))
            .filter(pl.col("pu_group").is_in([treated_group, "far_control"]))
        )
        daily = (
            panel.group_by("date", "pu_location_id", "pu_group")
            .agg(
                pl.col("speed_miles").sum(),
                pl.col("speed_seconds").sum(),
                pl.col("speed_trips").sum(),
            )
            .filter(pl.col("speed_trips") >= 20)  # avoid noisy zone-days
            .with_columns(
                (pl.col("speed_miles") / (pl.col("speed_seconds") / 3600)).log().alias("log_mph"),
                pl.when(pl.col("pu_group") == treated_group)
                .then(pl.lit("treated"))
                .otherwise(pl.lit("control"))
                .alias("role"),
            )
        )
        return daily_rows(daily, "log_mph", "pu_location_id", "role")

    return build


def ntd_builder(treated_role: str, donor_role: str) -> Callable[[], pl.DataFrame]:
    """NTD: log monthly unlinked passenger trips; donors averaged with equal weight."""

    def build() -> pl.DataFrame:
        panel = pl.read_parquet(PROCESSED_DIR / "ntd_unit_month.parquet").filter(
            pl.col("role").is_in([treated_role, donor_role]) & (pl.col("upt") > 0)
        )
        return panel.select(
            pl.col("month").alias("period"),
            pl.when(pl.col("role") == treated_role)
            .then(pl.lit("treated"))
            .otherwise(pl.lit("control"))
            .alias("group"),
            pl.col("unit"),
            pl.col("upt").log().alias("value"),
        )

    return build


def subway_builder() -> pl.DataFrame:
    """Subway: log daily entries per station complex, CRZ vs non-CRZ."""
    panel = pl.read_parquet(PROCESSED_DIR / "subway_station_day.parquet").filter(
        pl.col("entries") > 0
    )
    panel = panel.with_columns(
        pl.col("entries").log().alias("log_entries"),
        pl.when(pl.col("is_crz"))
        .then(pl.lit("treated"))
        .otherwise(pl.lit("control"))
        .alias("role"),
    )
    return daily_rows(panel, "log_entries", "station_complex_id", "role")


def bus_builder() -> pl.DataFrame:
    """CBD bus speeds: log monthly speed per route segment type (CBD vs non-CBD), peak."""
    panel = pl.read_parquet(PROCESSED_DIR / "bus_route_month.parquet").filter(
        (pl.col("time_period") == "Peak") & (pl.col("hours") > 0)
    )
    return panel.select(
        pl.col("month").alias("period"),
        pl.when(pl.col("cbd_relation") == "CBD")
        .then(pl.lit("treated"))
        .otherwise(pl.lit("control"))
        .alias("group"),
        (pl.col("route_id") + "_" + pl.col("cbd_relation")).alias("unit"),
        pl.col("speed_mph").log().alias("value"),
    )


def air_builder(
    pollutant: str,
    treated_roles: list[str],
    control_roles: list[str],
    control_source: str | None = None,
) -> Callable[[], pl.DataFrame]:
    """Air: daily-mean concentration per site on valid, non-smoke days (levels, not logs)."""

    def build() -> pl.DataFrame:
        smoke = pl.read_parquet(PROCESSED_DIR / "smoke_days.parquet").select("date", "is_smoke_day")
        panel = (
            pl.read_parquet(PROCESSED_DIR / "air_site_day.parquet")
            .filter((pl.col("pollutant") == pollutant) & pl.col("valid_day"))
            .join(smoke, on="date", how="left")
            .filter(~pl.col("is_smoke_day").fill_null(False))
        )
        treated = panel.filter(pl.col("role").is_in(treated_roles))
        control = panel.filter(pl.col("role").is_in(control_roles))
        if control_source:
            control = control.filter(pl.col("source") == control_source)
        both = pl.concat(
            [
                treated.with_columns(pl.lit("treated").alias("role_label")),
                control.with_columns(pl.lit("control").alias("role_label")),
            ],
            how="diagonal_relaxed",
        ).with_columns((pl.col("source") + ":" + pl.col("site_id")).alias("site_key"))
        return daily_rows(both, "daily_mean", "site_key", "role_label")

    return build


# --------------------------------------------------------------------------- estimation panels
#
# Phase 3 additions. The rules below were fixed and logged in docs/deviations.md
# (entries 6-10) before any treatment-effect estimate was computed.

G_LINE_SHUTDOWN = (date(2024, 6, 28), date(2024, 9, 3))  # docs/confounders.md
MIN_DONOR_COVERAGE = 0.75  # share of donors that must report in a week (deviation 8)
PANDEY_WEEKS = range(1, 15)  # weeks 1-14
PANDEY_EXCLUDED_ZONES = (103, 104, 105)  # Governor's, Ellis, Liberty islands: not "north of 60th"


def fill_missing_days(daily: pl.DataFrame, unit: str, count: str) -> pl.DataFrame:
    """Add a zero-count row for every unit-day missing between the first and last date.

    TLC zone-days with no trips have no row in the aggregated panel. The
    pre-registered outcome is log(1 + trips), which is defined for zero, so
    missing days are zeros, not missing data.
    """
    first, last = daily["date"].min(), daily["date"].max()
    if not isinstance(first, date) or not isinstance(last, date):
        raise ValueError("panel has no dates")
    days = pl.DataFrame({"date": pl.date_range(first, last, interval="1d", eager=True)})
    keys = daily.select(unit, "role").unique()
    grid = keys.join(days, how="cross")
    return grid.join(daily, on=[unit, "role", "date"], how="left").with_columns(
        pl.col(count).fill_null(0)
    )


def tlc_count_panel(
    treated_group: str, measure: str = "trips", services: tuple[str, ...] | None = None
) -> pl.DataFrame:
    """log(1 + daily count) by pickup zone with the plan's counting rules (T2, S1, S3, T5).

    CRZ zones count every pickup. Every other zone counts only trips whose
    drop-off is also outside the CRZ. ``measure`` is ``trips`` or
    ``shared_requests``; ``services`` restricts to yellow, green, or fhvhv.
    """
    groups = pl.read_csv(FINAL_DIR / "zone_groups.csv").select(
        pl.col("location_id").alias("pu_location_id"), pl.col("group").alias("pu_group")
    )
    panel = pl.read_parquet(PROCESSED_DIR / "tlc_zone_day.parquet").join(
        groups, on="pu_location_id", how="inner"
    )
    if services is not None:
        panel = panel.filter(pl.col("service").is_in(list(services)))
    if treated_group == "crz":
        treated = panel.filter(pl.col("pu_group") == "crz")
    else:
        treated = panel.filter(
            (pl.col("pu_group") == treated_group) & (pl.col("do_group") != "crz")
        )
    control = panel.filter((pl.col("pu_group") == "far_control") & (pl.col("do_group") != "crz"))
    daily = (
        pl.concat(
            [
                treated.with_columns(pl.lit("treated").alias("role")),
                control.with_columns(pl.lit("control").alias("role")),
            ]
        )
        .group_by("date", "pu_location_id", "role")
        .agg(pl.col(measure).sum())
    )
    daily = fill_missing_days(daily, "pu_location_id", measure)
    daily = daily.with_columns((pl.col(measure) + 1).log().alias("log_count"))
    return daily_rows(daily, "log_count", "pu_location_id", "role")


def g_line_complexes() -> set[str]:
    """Station complexes with at least one station served by the G train."""
    stations = pl.read_csv(
        PROCESSED_DIR.parent / "raw" / "socrata" / "subway_stations.csv", infer_schema_length=0
    )
    served = stations.filter(pl.col("Daytime Routes").str.split(" ").list.contains(pl.lit("G")))
    return set(served["Complex ID"].to_list())


def subway_panel() -> pl.DataFrame:
    """R2: log daily entries per complex, with the G shutdown excluded from controls.

    The pre-registered handling in docs/confounders.md: control complexes served by
    the G train are dropped from 2024-06-28 to 2024-09-03.
    """
    rows = subway_builder()
    affected = g_line_complexes()
    start, end = G_LINE_SHUTDOWN
    drop = (
        (pl.col("group") == "control")
        & pl.col("unit").is_in(list(affected))
        & pl.col("period").is_between(start, end)
    )
    return rows.filter(~drop)


def bus_panel() -> pl.DataFrame:
    """R3: log peak bus speed per route segment type and month, clustered by route."""
    rows = bus_builder()
    return rows.with_columns(pl.col("unit").str.split("_").list.first().alias("cluster"))


def pandey_panel(control: str, week_convention: str) -> pl.DataFrame:
    """Replication sample for Pandey, Guler & Gayah (2026), analysis plan section 4.2.

    FHVHV pickups on weekdays in weeks 1-14 of 2024 and 2025. Treated: CRZ zones
    (all pickups). Control: Manhattan zones north of 60th St (``upper_manhattan``)
    or our far-control group (``far_control``), counting only trips that do not
    end in the CRZ. The paper does not state its week convention, so both ISO
    weeks (``iso``) and 7-day blocks from January 1 (``calendar``) are offered.
    """
    groups = pl.read_csv(FINAL_DIR / "zone_groups.csv")
    if control == "upper_manhattan":
        control_zones = groups.filter(
            (pl.col("borough") == "Manhattan")
            & (pl.col("group") != "crz")
            & ~pl.col("location_id").is_in(list(PANDEY_EXCLUDED_ZONES))
        )
    elif control == "far_control":
        control_zones = groups.filter(pl.col("group") == "far_control")
    else:
        raise ValueError(f"unknown control {control}")
    crz_zones = groups.filter(pl.col("group") == "crz")
    panel = pl.read_parquet(PROCESSED_DIR / "tlc_zone_day.parquet").filter(
        pl.col("service") == "fhvhv"
    )
    treated = panel.filter(pl.col("pu_location_id").is_in(crz_zones["location_id"].to_list()))
    controls = panel.filter(
        pl.col("pu_location_id").is_in(control_zones["location_id"].to_list())
        & (pl.col("do_group") != "crz")
    )
    daily = (
        pl.concat(
            [
                treated.with_columns(pl.lit("treated").alias("role")),
                controls.with_columns(pl.lit("control").alias("role")),
            ]
        )
        .group_by("date", "pu_location_id", "role")
        .agg(pl.col("trips").sum())
    )
    daily = fill_missing_days(daily, "pu_location_id", "trips")
    if week_convention == "iso":
        week, year = pl.col("date").dt.week(), pl.col("date").dt.iso_year()
    elif week_convention == "calendar":
        week, year = (pl.col("date").dt.ordinal_day() - 1) // 7 + 1, pl.col("date").dt.year()
    else:
        raise ValueError(f"unknown week convention {week_convention}")
    daily = daily.with_columns(week.alias("week"), year.alias("year")).filter(
        pl.col("week").is_in(list(PANDEY_WEEKS))
        & pl.col("year").is_in([2024, 2025])
        & (pl.col("date").dt.weekday() <= 5)
    )
    return daily.select(
        pl.col("date").alias("period"),
        pl.col("role").alias("group"),
        pl.col("pu_location_id").cast(pl.Utf8).alias("unit"),
        (pl.col("trips") + 1).log().alias("value"),
        (pl.col("year") == 2025).alias("post"),
    )


# --------------------------------------------------------------------------- synthetic control


@dataclass(frozen=True)
class SyntheticPanel:
    """A treated series and a balanced donor matrix over the same periods."""

    periods: list[date]
    target: np.ndarray
    donors: np.ndarray
    donor_names: list[str]
    windows: synth.Windows
    imputed_share: float = 0.0  # share of donor-periods filled by imputation


def study_windows(periods: list[date], frequency: str) -> synth.Windows:
    """Window masks for a list of periods."""
    labels = np.array([windows.window_of(p, frequency) for p in periods])
    return synth.Windows(
        pre=labels == "pre",
        anticipation=labels == "anticipation",
        post_year1=labels == "post_year1",
        post_extended=labels == "post_extended",
        years=np.array([windows.years_since_start(p) for p in periods]),
    )


def ntd_synthetic(treated_role: str, donor_role: str) -> SyntheticPanel:
    """R1/R4: log monthly unlinked passenger trips, NYC treated unit vs donors."""
    rows = ntd_builder(treated_role, donor_role)().filter(pl.col("period") >= date(2023, 1, 1))
    wide = rows.pivot(on="unit", index="period", values="value").sort("period").drop_nulls()
    treated_unit = rows.filter(pl.col("group") == "treated")["unit"].unique().item()
    donor_names = sorted(c for c in wide.columns if c not in ("period", treated_unit))
    periods = wide["period"].to_list()
    return SyntheticPanel(
        periods=periods,
        target=wide[treated_unit].to_numpy(),
        donors=wide.select(donor_names).to_numpy(),
        donor_names=donor_names,
        windows=study_windows(periods, "month"),
    )


def impute_two_way(values: np.ndarray, iterations: int = 500) -> np.ndarray:
    """Fill missing cells of a (periods x units) matrix with unit + period effects.

    Fits value = a_unit + b_period on the observed cells by alternating means,
    then uses a + b for the missing ones. Observed cells are unchanged.
    """
    observed = ~np.isnan(values)
    unit_effect = np.nanmean(values, axis=0)
    period_effect = np.zeros(values.shape[0])
    for _ in range(iterations):
        period_effect = np.nanmean(values - unit_effect[None, :], axis=1)
        unit_effect = np.nanmean(values - period_effect[:, None], axis=0)
    fitted = period_effect[:, None] + unit_effect[None, :]
    return np.where(observed, values, fitted)


def air_synthetic(
    pollutant: str, treated_roles: list[str], statistic: str = "daily_mean"
) -> SyntheticPanel:
    """A1/A4 (and Phase 4's A2/S5): weekly mean of daily values, treated vs donors.

    Analysis plan section 5.2:
    - The treated series is the mean of the treated sites' site-demeaned weekly
      values. A week counts only if every treated site is valid that week.
    - A valid week has at least 5 valid, non-smoke days.
    - Donor-weeks that are missing are imputed with donor + week effects
      (deviation 8). The treated series is never imputed.
    - Weeks where fewer than 75% of donors report are dropped (deviation 8).
    """
    smoke = pl.read_parquet(PROCESSED_DIR / "smoke_days.parquet").select("date", "is_smoke_day")
    air = (
        pl.read_parquet(PROCESSED_DIR / "air_site_day.parquet")
        .filter((pl.col("pollutant") == pollutant) & pl.col("valid_day"))
        .filter(pl.col("role").is_in([*treated_roles, "donor"]))
        .join(smoke, on="date", how="left")
        .filter(~pl.col("is_smoke_day").fill_null(False))
        .with_columns(
            pl.col("date").dt.truncate("1w").alias("week"),
            (pl.col("source") + ":" + pl.col("site_id")).alias("site_key"),
        )
    )
    weekly = (
        air.group_by("role", "site_key", "week")
        .agg(pl.col(statistic).mean().alias("value"), pl.len().alias("days"))
        .filter((pl.col("days") >= 5) & (pl.col("week") >= date(2023, 1, 2)))
    )
    treated = weekly.filter(pl.col("role").is_in(treated_roles))
    n_treated_sites = treated["site_key"].n_unique()
    pre_end = ANTICIPATION_START
    treated = treated.with_columns(
        (
            pl.col("value")
            - pl.col("value")
            .filter(pl.col("week") + timedelta(days=6) < pre_end)
            .mean()
            .over("site_key")
        ).alias("centred")
    )
    treated_series = (
        treated.group_by("week")
        .agg(pl.col("centred").mean(), pl.len().alias("sites"))
        .filter(pl.col("sites") == n_treated_sites)
        .sort("week")
    )
    donors_long = weekly.filter(pl.col("role") == "donor").join(
        treated_series.select("week"), on="week", how="semi"
    )
    donor_wide = (
        donors_long.pivot(on="site_key", index="week", values="value")
        .join(treated_series.select("week"), on="week", how="right")
        .sort("week")
    )
    donor_names = sorted(c for c in donor_wide.columns if c != "week")
    raw = donor_wide.select(donor_names).to_numpy().astype(np.float64)
    # Keep weeks where most donors report; this also ends the panel where the AQS
    # donor files end, so whole stretches of donor data are never invented.
    covered = (~np.isnan(raw)).mean(axis=1) >= MIN_DONOR_COVERAGE
    raw = raw[covered]
    periods = [
        week for week, keep in zip(treated_series["week"].to_list(), covered, strict=True) if keep
    ]
    return SyntheticPanel(
        periods=periods,
        target=treated_series["centred"].to_numpy()[covered],
        donors=impute_two_way(raw),
        donor_names=donor_names,
        windows=study_windows(periods, "week"),
        imputed_share=float(np.isnan(raw).mean()),
    )
