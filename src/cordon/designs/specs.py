"""Turn a long panel into regression arrays for a pre-registered DiD specification.

Input rows have columns ``period`` (date), ``group`` ("treated"/"control"),
``unit`` (str), ``value`` (float), and optionally ``cluster`` (str; defaults to
the unit).

Specifications:
- **pooled:** indicators for treated x anticipation and treated x post year 1
  (and treated x post extended for the extended window);
- **event_study:** treated x event-bin indicators plus treated x anticipation.
  The calendar year 2023 is the seasonal baseline and gets no indicators. Bins
  in 2024, including the reference bins, get indicators. Coefficients are then
  re-expressed relative to the reference window (bins -2 and -1). Each
  coefficient therefore compares the treated-minus-control gap in a 4-week bin
  with the gap in the same weeks of 2023, net of the same comparison for the
  reference window.
  Why not indicators for every pre-period bin, as first written in the plan:
  13 bins of 28 days line up with the same calendar weeks every year. The treated
  group's seasonal profile is then almost collinear with the bin indicators, and
  the bins pick up seasonal noise that looks like pre-trends. This was found on
  simulated data before any estimate was computed; see deviation 6 and ADR 0012.

Fixed effects: unit x season (ISO week-of-year for daily data, month-of-year
for monthly data) and period.

Adjustments fitted on the pre-period only:
- ``trends``: unit-specific linear trends (ADR 0011);
- ``weather``: treated-group weather slopes (A3, analysis plan section 5.2).
"""

from __future__ import annotations

import itertools
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
import polars as pl

from cordon.designs import windows
from cordon.designs.did import Design, Estimate, fit
from cordon.designs.fixed_effects import encode

# Boundary-layer height is missing at the source (Open-Meteo) for 2023-12-31 to
# 2024-06-30, so the primary weather adjustment omits it; a check adds it back on
# complete-case days (deviation 11).
WEATHER_COLUMNS = ("temp_mean_c", "rh_mean_pct", "wind_mean_kmh", "precip_mm")
WEATHER_COLUMNS_WITH_PBL = (*WEATHER_COLUMNS, "pbl_mean_m")


@dataclass(frozen=True)
class DidSpec:
    """One pre-registered DiD specification."""

    kind: str  # "pooled" or "event_study"
    frequency: str  # "day" or "month"
    window: str = "year1"  # "year1" or "extended"
    trends: bool = False
    weather: bool = False
    weather_columns: tuple[str, ...] = WEATHER_COLUMNS

    @property
    def label(self) -> str:
        """Short name used in results files."""
        parts = [self.kind, self.window]
        if self.trends:
            parts.append("detrended")
        if self.weather:
            parts.append("weather" if self.weather_columns == WEATHER_COLUMNS else "weather_pbl")
        return "_".join(parts)


def label_rows(rows: pl.DataFrame, frequency: str) -> pl.DataFrame:
    """Add window, event bin, season, and time-in-years columns."""
    periods = rows["period"].unique().sort().to_list()
    lookup = pl.DataFrame(
        {
            "period": periods,
            "window": [windows.window_of(p, frequency) for p in periods],
            "bin": [
                None
                if windows.window_of(p, frequency) == "before_study"
                else windows.event_bin(p, frequency)
                for p in periods
            ],
            "years": [windows.years_since_start(p) for p in periods],
        },
        schema_overrides={"bin": pl.Int64},
    )
    season = pl.col("period").dt.week() if frequency == "day" else pl.col("period").dt.month()
    frame = rows.join(lookup, on="period", how="left").with_columns(season.alias("season"))
    if "cluster" not in frame.columns:
        frame = frame.with_columns(pl.col("unit").alias("cluster"))
    return frame


def sample(frame: pl.DataFrame, window: str) -> pl.DataFrame:
    """Rows used by a window: pre, anticipation, year 1 (+ extended)."""
    keep = ["pre", "anticipation", "post_year1"]
    if window == "extended":
        keep.append("post_extended")
    return frame.filter(pl.col("window").is_in(keep) & pl.col("value").is_not_nan())


def regressors(
    frame: pl.DataFrame, spec: DidSpec, treated: np.ndarray
) -> tuple[np.ndarray, list[str]]:
    """Treatment indicator columns and their names."""
    window = frame["window"].to_numpy()
    columns: list[np.ndarray] = []
    names: list[str] = []
    if spec.kind == "pooled":
        for name in ["anticipation", "post_year1"] + (
            ["post_extended"] if spec.window == "extended" else []
        ):
            columns.append(treated & (window == name))
            names.append(name)
    elif spec.kind == "event_study":
        bins = frame["bin"].to_numpy()
        in_2024 = (frame["period"].dt.year() == 2024).to_numpy()
        is_event_period = ((window == "pre") & in_2024) | (window == "post_year1")
        present = sorted({int(b) for b, keep in zip(bins, is_event_period, strict=True) if keep})
        for b in present:
            columns.append(treated & is_event_period & (bins == b))
            names.append(f"bin_{b}")
        columns.append(treated & (window == "anticipation"))
        names.append("anticipation")
    else:
        raise ValueError(f"unknown specification {spec.kind}")
    return np.column_stack(columns).astype(np.float64), names


def adjustment(
    frame: pl.DataFrame, spec: DidSpec, treated: np.ndarray, weather: pl.DataFrame | None
) -> np.ndarray | None:
    """Columns fitted on the pre-period only (unit trends and/or weather slopes)."""
    blocks: list[np.ndarray] = []
    if spec.trends:
        units = encode(frame["unit"].to_numpy())
        years = frame["years"].to_numpy()
        trend = np.zeros((len(frame), int(units.max()) + 1))
        trend[np.arange(len(frame)), units] = years
        blocks.append(trend)
    if spec.weather:
        if weather is None:
            raise ValueError("weather adjustment requested without weather data")
        joined = frame.select("period").join(
            weather.rename({"date": "period"}), on="period", how="left"
        )
        numeric = joined.select(spec.weather_columns).to_numpy()
        sectors = joined["wind_sector"].to_numpy()
        levels = sorted(set(sectors.tolist()))[1:]  # first sector is the baseline
        dummies = np.column_stack([sectors == level for level in levels]).astype(np.float64)
        blocks.append(np.column_stack([numeric, dummies]) * treated[:, None])
    if not blocks:
        return None
    return np.column_stack(blocks)


def build_design(
    rows: pl.DataFrame,
    spec: DidSpec,
    treated_units: set[str] | None = None,
    weather: pl.DataFrame | None = None,
) -> Design:
    """Regression arrays for one specification.

    ``treated_units`` overrides which units count as treated, for randomization
    inference. By default the ``group`` column decides.
    """
    frame = sample(label_rows(rows, spec.frequency), spec.window)
    if spec.weather and weather is not None:
        complete = weather.filter(
            pl.all_horizontal(pl.col(c).is_not_nan() for c in spec.weather_columns)
        )
        frame = frame.join(
            complete.select("date").rename({"date": "period"}), on="period", how="semi"
        )
    if treated_units is None:
        treated = (frame["group"] == "treated").to_numpy()
    else:
        treated = frame["unit"].is_in(list(treated_units)).to_numpy()
    x, names = regressors(frame, spec, treated)
    unit_season = encode((frame["unit"] + "_" + frame["season"].cast(pl.Utf8)).to_numpy())
    period = encode(frame["period"].cast(pl.Utf8).to_numpy())
    z = adjustment(frame, spec, treated, weather)
    return Design(
        y=frame["value"].to_numpy().astype(np.float64),
        x=x,
        names=tuple(names),
        fixed_effects=(unit_season, period),
        clusters=encode(frame["cluster"].to_numpy()),
        adjust=z,
        adjust_rows=(frame["window"] == "pre").to_numpy() if z is not None else None,
    )


def pre_bins(names: tuple[str, ...]) -> list[str]:
    """Names of pre-period event-bin coefficients."""
    return [n for n in names if n.startswith("bin_-")]


def relative_to_reference(estimate: Estimate) -> Estimate:
    """Subtract the mean of the reference bins (-2, -1) from every other coefficient.

    This is a linear map A applied to the coefficients, so the covariance becomes
    A V A' and the linear weights become W A'. The reference bins are dropped.
    """
    reference = [f"bin_{b}" for b in windows.REFERENCE_BINS]
    if not all(name in estimate.names for name in reference):
        raise ValueError("event study has no reference bins")
    keep = [i for i, name in enumerate(estimate.names) if name not in reference]
    ref_idx = [estimate.index(name) for name in reference]
    transform = np.zeros((len(keep), len(estimate.names)))
    for row, i in enumerate(keep):
        transform[row, i] = 1.0
        transform[row, ref_idx] -= 1.0 / len(ref_idx)  # anticipation too
    return Estimate(
        names=tuple(estimate.names[i] for i in keep),
        coef=transform @ estimate.coef,
        vcov=transform @ estimate.vcov @ transform.T,
        weights=estimate.weights @ transform.T,
        residuals=estimate.residuals,
        clusters=estimate.clusters,
        n_obs=estimate.n_obs,
        n_clusters=estimate.n_clusters,
        n_params=estimate.n_params,
    )


@dataclass(frozen=True)
class Permutation:
    """Randomization inference over assignments of treated status."""

    p_value: float
    observed: float
    permuted: list[float]


def randomization_inference(
    rows: pl.DataFrame,
    spec: DidSpec,
    statistic: Callable[[Estimate], float],
    weather: pl.DataFrame | None = None,
) -> Permutation:
    """Re-estimate under every assignment of the same number of treated units.

    The p-value is the share of assignments (the actual one included) whose
    statistic is at least as large in absolute value as the observed one, so its
    smallest possible value is 1 / (number of assignments).
    """
    units = sorted(rows["unit"].unique().to_list())
    actual = set(rows.filter(pl.col("group") == "treated")["unit"].unique().to_list())
    observed = statistic(fit(build_design(rows, spec, actual, weather)))
    permuted = []
    for combo in itertools.combinations(units, len(actual)):
        permuted.append(statistic(fit(build_design(rows, spec, set(combo), weather))))
    values = np.abs(np.array(permuted))
    p_value = float(np.mean(values >= abs(observed) - 1e-12))
    return Permutation(p_value=p_value, observed=observed, permuted=permuted)
