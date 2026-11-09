"""Pre-specified heterogeneity cuts (analysis plan section 9; deviation 16).

Each cut splits an outcome into levels:
- peak vs overnight;
- weekday vs weekend;
- vehicle class;
- borough.

Rows from all levels are stacked into one regression. Each level gets its own
unit x season and period fixed effects, so the coefficients equal separate
per-level regressions. Standard errors are clustered by the original unit, so
the covariance between levels is estimated, and the *difference* between levels
gets a valid SE.

Two parametrisations of the same model:
- **per level:** treated x post x 1[level = l] for every level, which gives each
  level's effect;
- **difference:** a common treated x post term plus treated x post x 1[level = l]
  for every non-reference level, which gives level minus reference.

The borough cut is different: borough splits the *treated* zones, and they share
one control group. It is estimated in a single regression with one treated x
post indicator per borough.

Few-cluster outcomes (T1: 7 facilities) also get a wild cluster bootstrap p-value.
BH q-values are computed within each cut, across outcomes (ADR 0008).

Run: ``python -m cordon.designs.heterogeneity``.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import numpy as np
import polars as pl

from cordon.config import FINAL_DIR, RANDOM_SEED, REPO_ROOT
from cordon.designs import did, multiple, panels, specs
from cordon.designs.fixed_effects import encode

LOG = logging.getLogger(__name__)
OUTPUT = REPO_ROOT / "results" / "heterogeneity.csv"
FEW_CLUSTERS = did.MIN_CLUSTERS_FOR_WALD
BOOTSTRAP_DRAWS = 9_999


@dataclass(frozen=True)
class Cut:
    """One outcome split into levels; the first level is the reference."""

    cut: str
    key: str
    levels: dict[str, Callable[[], pl.DataFrame]]
    frequency: str = "day"


def weekday_split(builder: Callable[[], pl.DataFrame]) -> dict[str, Callable[[], pl.DataFrame]]:
    """Split one panel into weekday and weekend rows."""

    def part(weekend: bool) -> Callable[[], pl.DataFrame]:
        return lambda: builder().filter((pl.col("period").dt.weekday() >= 6) == weekend)

    return {"weekday": part(False), "weekend": part(True)}


CUTS = [
    Cut(
        "peak_vs_overnight",
        "T1",
        {
            "peak": panels.bt_builder("control", "treated", "crossings_peak"),
            "overnight": panels.bt_builder("control", "treated", "crossings_offpeak"),
        },
    ),
    Cut(
        "peak_vs_overnight",
        "T2",
        {
            "peak": lambda: panels.tlc_count_panel("crz", peak=True),
            "overnight": lambda: panels.tlc_count_panel("crz", peak=False),
        },
    ),
    Cut(
        "peak_vs_overnight",
        "T3",
        {
            "peak": panels.tlc_speed_builder("crz", peak=True),
            "overnight": panels.tlc_speed_builder("crz", peak=False),
        },
    ),
    Cut(
        "peak_vs_overnight",
        "S1",
        {
            "peak": lambda: panels.tlc_count_panel("border_ring", peak=True),
            "overnight": lambda: panels.tlc_count_panel("border_ring", peak=False),
        },
    ),
    Cut(
        "peak_vs_overnight",
        "S3",
        {
            "peak": lambda: panels.tlc_count_panel("upper_manhattan_bronx", peak=True),
            "overnight": lambda: panels.tlc_count_panel("upper_manhattan_bronx", peak=False),
        },
    ),
    Cut("weekday_vs_weekend", "T1", weekday_split(panels.bt_builder("control", "treated"))),
    Cut("weekday_vs_weekend", "T2", weekday_split(lambda: panels.tlc_count_panel("crz"))),
    Cut("weekday_vs_weekend", "T3", weekday_split(panels.tlc_speed_builder("crz"))),
    Cut("weekday_vs_weekend", "S1", weekday_split(lambda: panels.tlc_count_panel("border_ring"))),
    Cut(
        "weekday_vs_weekend",
        "S3",
        weekday_split(lambda: panels.tlc_count_panel("upper_manhattan_bronx")),
    ),
    Cut(
        "vehicle_class",
        "T1",
        {
            "car": panels.bt_builder("control", "treated", "crossings_car"),
            "truck": panels.bt_builder("control", "treated", "crossings_truck"),
        },
    ),
    Cut(
        "vehicle_class",
        "T2",
        {
            "fhvhv": lambda: panels.tlc_count_panel("crz", services=("fhvhv",)),
            "yellow": lambda: panels.tlc_count_panel("crz", services=("yellow",)),
        },
    ),
]

BOROUGH_CUTS = {"S1": "border_ring", "S3": "upper_manhattan_bronx"}


def stack(levels: dict[str, pl.DataFrame]) -> pl.DataFrame:
    """Stack level panels with level-specific unit and period labels."""
    frames = []
    for level, rows in levels.items():
        if "cluster" not in rows.columns:
            rows = rows.with_columns(pl.col("unit").alias("cluster"))
        frames.append(
            rows.with_columns(
                pl.lit(level).alias("level"),
                (pl.col("unit") + "|" + level).alias("unit"),
                (pl.col("period").cast(pl.Utf8) + "|" + level).alias("period_key"),
            )
        )
    return pl.concat(frames, how="diagonal_relaxed")


def stacked_design(
    rows: pl.DataFrame, levels: list[str], frequency: str, parametrisation: str
) -> did.Design:
    """Design for a stacked cut: 'per_level' or 'difference' parametrisation."""
    frame = specs.sample(specs.label_rows(rows, frequency), "year1")
    treated = (frame["group"] == "treated").to_numpy()
    window = frame["window"].to_numpy()
    level = frame["level"].to_numpy()
    columns, names = [], []
    for term in ("anticipation", "post_year1"):
        in_term = treated & (window == term)
        if parametrisation == "per_level":
            for name in levels:
                columns.append(in_term & (level == name))
                names.append(f"{term}:{name}")
        else:
            columns.append(in_term)
            names.append(term)
            for name in levels[1:]:
                columns.append(in_term & (level == name))
                names.append(f"{term}:{name}-{levels[0]}")
    unit_season = encode((frame["unit"] + "_" + frame["season"].cast(pl.Utf8)).to_numpy())
    return did.Design(
        y=frame["value"].to_numpy().astype(np.float64),
        x=np.column_stack(columns).astype(np.float64),
        names=tuple(names),
        fixed_effects=(unit_season, encode(specs.period_keys(frame))),
        clusters=encode(frame["cluster"].to_numpy()),
    )


def result_row(
    cut: str,
    key: str,
    level: str,
    kind: str,
    design: did.Design,
    estimate: did.Estimate,
    name: str,
) -> dict[str, Any]:
    """One output row, with a bootstrap p-value when clusters are few."""
    low, high = did.normal_interval(estimate, name)
    p_value = did.wald_p_value(estimate, name)
    method = f"cluster-robust t({estimate.n_clusters - 1})"
    if estimate.n_clusters < FEW_CLUSTERS:
        boot = did.wild_cluster_bootstrap(design, estimate, name, BOOTSTRAP_DRAWS, RANDOM_SEED)
        p_value, method = boot.p_value, f"wild cluster bootstrap, Webb ({boot.draws} draws)"
    return {
        "cut": cut,
        "key": key,
        "level": level,
        "kind": kind,  # "level effect" or "difference"
        "estimate": estimate.value(name),
        "se": estimate.se(name),
        "ci_low": low,
        "ci_high": high,
        "percent": did.percent(estimate.value(name)),
        "percent_ci_low": did.percent(low),
        "percent_ci_high": did.percent(high),
        "p_value": p_value,
        "p_method": method,
        "n_obs": estimate.n_obs,
        "n_clusters": estimate.n_clusters,
    }


def run_cut(cut: Cut) -> list[dict[str, Any]]:
    """Level effects and level-minus-reference differences for one cut."""
    levels = list(cut.levels)
    rows = stack({name: build() for name, build in cut.levels.items()})
    out = []
    per_level = stacked_design(rows, levels, cut.frequency, "per_level")
    estimate = did.fit(per_level)
    for name in levels:
        out.append(
            result_row(
                cut.cut, cut.key, name, "level effect", per_level, estimate, f"post_year1:{name}"
            )
        )
    difference = stacked_design(rows, levels, cut.frequency, "difference")
    estimate = did.fit(difference)
    for name in levels[1:]:
        out.append(
            result_row(
                cut.cut,
                cut.key,
                f"{name} - {levels[0]}",
                "difference",
                difference,
                estimate,
                f"post_year1:{name}-{levels[0]}",
            )
        )
    LOG.info("%s %s done", cut.cut, cut.key)
    return out


def run_borough_cut(key: str, treated_group: str) -> list[dict[str, Any]]:
    """One treated x post indicator per borough of the treated zones; shared controls."""
    zones = pl.read_csv(FINAL_DIR / "zone_groups.csv").select(
        pl.col("location_id").cast(pl.Utf8).alias("unit"), "borough"
    )
    rows = panels.tlc_count_panel(treated_group).join(zones, on="unit", how="left")
    frame = specs.sample(specs.label_rows(rows, "day"), "year1")
    treated = (frame["group"] == "treated").to_numpy()
    window = frame["window"].to_numpy()
    borough = frame["borough"].to_numpy()
    boroughs = sorted(set(borough[treated].tolist()))
    columns, names = [], []
    for term in ("anticipation", "post_year1"):
        for b in boroughs:
            columns.append(treated & (window == term) & (borough == b))
            names.append(f"{term}:{b}")
    design = did.Design(
        y=frame["value"].to_numpy().astype(np.float64),
        x=np.column_stack(columns).astype(np.float64),
        names=tuple(names),
        fixed_effects=(
            encode((frame["unit"] + "_" + frame["season"].cast(pl.Utf8)).to_numpy()),
            encode(specs.period_keys(frame)),
        ),
        clusters=encode(frame["cluster"].to_numpy()),
    )
    estimate = did.fit(design)
    out = []
    for b in boroughs:
        row = result_row("borough", key, b, "level effect", design, estimate, f"post_year1:{b}")
        row["n_treated_zones"] = len(
            set(
                frame.filter((pl.col("group") == "treated") & (pl.col("borough") == b))[
                    "unit"
                ].to_list()
            )
        )
        out.append(row)
    LOG.info("borough %s done", key)
    return out


def add_bh(table: pl.DataFrame) -> pl.DataFrame:
    """BH q-values within each cut: differences, or borough effects for the borough cut."""
    tested = (pl.col("kind") == "difference") | (pl.col("cut") == "borough")
    frames = []
    for _, group in table.group_by(["cut"], maintain_order=True):
        mask = group.select(tested).to_series()
        q = np.full(group.height, np.nan)
        if mask.any():
            q[mask.to_numpy()] = multiple.benjamini_hochberg(
                group.filter(mask)["p_value"].to_list()
            )
        frames.append(group.with_columns(pl.Series("q_bh_within_cut", q)))
    return pl.concat(frames)


def main() -> None:
    """Write results/heterogeneity.csv."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    rows: list[dict[str, Any]] = []
    for cut in CUTS:
        rows.extend(run_cut(cut))
    for key, group in BOROUGH_CUTS.items():
        rows.extend(run_borough_cut(key, group))
    table = add_bh(pl.DataFrame(rows, infer_schema_length=None))
    OUTPUT.parent.mkdir(exist_ok=True)
    table.write_csv(OUTPUT)


if __name__ == "__main__":
    main()
