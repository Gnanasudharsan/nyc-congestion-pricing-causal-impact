"""Minimum detectable effects (MDEs) from placebo dates inside the pre-period.

The analysis plan (section 8) commits to computing MDEs in Phase 2 using
**pre-period data only** (2023-01-01 to 2024-11-13). No post-period data is
read here, so these are not treatment-effect estimates.

Method:
1. Pick placebo "treatment" dates every 28 days from 2023-07-02 to 2024-06-30,
   so each placebo has at least 6 months of data before and 4.5 months after.
2. For each placebo date, estimate the pre-registered specification on
   pre-period data, with "post" meaning on or after the placebo date.
   - DiD outcomes (T1, T2, T3, S1): log outcome on treated x post, with
     unit x week-of-year and date fixed effects (pyfixest).
   - Synthetic-control outcomes (R1, A1): a proxy. We use the change in the gap
     between the treated series and an equal-weight donor average. Fitted
     synthetic-control weights should track the treated unit at least as well,
     so this proxy MDE is expected to be conservative (too large).
3. With no true effect, the placebo estimates show how much an estimate moves
   by chance. MDE at 80% power and 5% two-sided significance is
   2.8 x SD(placebo estimates).

Caveats: about 13 placebo windows, overlapping and serially correlated, so the
SD is itself imprecise. The MDEs are a planning guide, not a test.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta

import numpy as np
import polars as pl

from cordon.config import FINAL_DIR
from cordon.designs import panels
from cordon.features.calendar import PRE_START
from cordon.viz import descriptive

LOG = logging.getLogger(__name__)
PRE_END = date(2024, 11, 13)
FIRST_PLACEBO = date(2023, 7, 2)
LAST_PLACEBO = date(2024, 6, 30)
POWER_MULTIPLIER = 2.8  # z(0.975) + z(0.80) = 1.96 + 0.84
OUTPUT = FINAL_DIR / "mde_pre_period.csv"

DID_KEYS = ("T1", "T2", "T3", "S1")
SC_KEYS = ("R1", "A1")


def placebo_dates() -> list[date]:
    """Placebo treatment dates every 28 days."""
    dates = []
    day = FIRST_PLACEBO
    while day <= LAST_PLACEBO:
        dates.append(day)
        day += timedelta(days=28)
    return dates


def pre_period(rows: pl.DataFrame) -> pl.DataFrame:
    """Keep only the pre-period."""
    return rows.filter(pl.col("period").is_between(PRE_START, PRE_END))


def did_placebo_estimate(rows: pl.DataFrame, placebo: date) -> float:
    """Pooled DiD coefficient with unit x week-of-year and date fixed effects."""
    import pyfixest as pf  # heavy dependency, imported only when needed

    frame = rows.with_columns(
        ((pl.col("group") == "treated") & (pl.col("period") >= placebo))
        .cast(pl.Int8)
        .alias("treated_post"),
        (pl.col("unit") + "_" + pl.col("period").dt.week().cast(pl.Utf8)).alias("unit_week"),
        pl.col("period").cast(pl.Utf8).alias("day"),
    ).to_pandas()
    fit = pf.feols("value ~ treated_post | unit_week + day", data=frame, vcov="iid")
    return float(fit.coef()["treated_post"])


def sc_proxy_estimate(rows: pl.DataFrame, placebo: date) -> float:
    """Change in (treated - equal-weight donor mean) gap after the placebo date."""
    centred = rows.with_columns(
        (pl.col("value") - pl.col("value").mean().over("unit")).alias("centred")
    )
    series = (
        centred.group_by("period", "group")
        .agg(pl.col("centred").mean())
        .pivot(on="group", index="period", values="centred")
        .drop_nulls()
        .with_columns((pl.col("treated") - pl.col("control")).alias("gap"))
    )
    after = series.filter(pl.col("period") >= placebo)["gap"].mean()
    before = series.filter(pl.col("period") < placebo)["gap"].mean()
    if not isinstance(after, float) or not isinstance(before, float):
        raise ValueError("placebo window has no data")
    return after - before


def compute() -> pl.DataFrame:
    """MDE for each primary outcome whose processed panel exists."""
    comparisons = {c.key: c for c in descriptive.COMPARISONS}
    results = []
    for key in (*DID_KEYS, *SC_KEYS):
        comparison = comparisons[key]
        try:
            rows = comparison.builder()
        except FileNotFoundError as error:
            LOG.warning("skipped %s: %s", key, error)
            continue
        if key == "A1":
            rows = panels.to_weekly(rows)  # the plan's A1 outcome is weekly
        rows = pre_period(rows)
        estimator = did_placebo_estimate if key in DID_KEYS else sc_proxy_estimate
        estimates = np.array([estimator(rows, d) for d in placebo_dates()])
        sd = float(estimates.std(ddof=1))
        scale = 100.0 if comparison.log_scale else 1.0
        results.append(
            {
                "key": key,
                "method": "did_placebo" if key in DID_KEYS else "sc_proxy_equal_weights",
                "unit": "log points x 100 (approx. %)"
                if comparison.log_scale
                else comparison.unit_label.split(",")[0],
                "placebos": len(estimates),
                "placebo_mean": round(float(estimates.mean()) * scale, 3),
                "placebo_sd": round(sd * scale, 3),
                "mde_80pct_power": round(POWER_MULTIPLIER * sd * scale, 3),
            }
        )
        LOG.info("%s: MDE %.2f", key, POWER_MULTIPLIER * sd * scale)
    return pl.DataFrame(results)


def main() -> None:
    """Write data/final/mde_pre_period.csv."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    table = compute()
    table.write_csv(OUTPUT)
    print(table)


if __name__ == "__main__":
    main()
