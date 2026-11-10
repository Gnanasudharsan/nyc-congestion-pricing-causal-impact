"""Inputs for the Quarto paper and site: every number comes from results/.

Writes:
- ``report/_variables.yml``: values cited in the text, used as
  ``{{< var t2.est >}}`` in .qmd files (Quarto variables);
- ``report/_generated/*.md``: tables included with ``{{< include >}}``.

No number in the paper or on the site is typed by hand (CLAUDE.md). Re-run after
``make analysis``: ``python -m cordon.viz.report_inputs``.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import polars as pl
import yaml

from cordon.config import FINAL_DIR, REPO_ROOT
from cordon.designs import results_page as page
from cordon.robustness.labels import detrended_spec, headline_spec

RESULTS = REPO_ROOT / "results"
REPORT = REPO_ROOT / "report"
GENERATED = REPORT / "_generated"
MINUS = "\u2212"  # typographic minus sign


def signed(value: float, digits: int = 1) -> str:
    """'+1.2' or '-1.2' with a true minus sign for typography."""
    text = f"{value:+.{digits}f}"
    return text.replace("-", MINUS)


def with_unit(value: float, unit: str, digits: int = 1) -> str:
    """Format an effect with its reporting unit."""
    return f"{signed(value, digits)}%" if unit == "percent" else f"{signed(value, digits)} {unit}"


def p_text(value: float) -> str:
    """Format a p-value for prose."""
    return "< 0.001" if value < 0.001 else f"{value:.3f}"


def estimate_row(estimates: pl.DataFrame, key: str, spec: str, term: str) -> dict[str, Any] | None:
    """One estimates row, or None."""
    rows = estimates.filter(
        (pl.col("key") == key) & (pl.col("spec") == spec) & (pl.col("term") == term)
    )
    return rows.row(0, named=True) if rows.height else None


def interval(row: dict[str, Any]) -> str:
    """Format a DiD interval as 'a to b' in reporting units."""
    unit = row["reported_unit"]
    return (
        f"{with_unit(float(row['reported_ci_low']), unit)} to "
        f"{with_unit(float(row['reported_ci_high']), unit)}"
    )


def outcome_variables(estimates: pl.DataFrame, claims: pl.DataFrame) -> dict[str, Any]:
    """Headline, detrended, anticipation, 2026, label, and p for every labelled outcome."""
    out: dict[str, Any] = {}
    for claim in claims.iter_rows(named=True):
        key = claim["key"]
        head = estimate_row(estimates, key, headline_spec(key), "post_year1")
        if head is None:
            continue
        unit = head["reported_unit"]
        entry: dict[str, Any] = {
            "est": with_unit(float(head["reported"]), unit),
            "label": claim["label"],
            "padj": p_text(float(claim["adjusted_p"])),
            "p": p_text(float(head["p_value"])),
            "breakdown": str(claim["breakdown_mbar"] or "not applicable").replace("<=", "≤"),
        }
        if head.get("reported_ci_low") is not None:
            entry["ci"] = interval(head)
        det = estimate_row(estimates, key, detrended_spec(key), "post_year1")
        if det is not None:
            entry["det"] = with_unit(float(det["reported"]), unit)
            if det.get("reported_ci_low") is not None:
                entry["det_ci"] = interval(det)
        spec = headline_spec(key)
        ant = estimate_row(estimates, key, spec, "anticipation")
        if ant is not None:
            entry["ant"] = with_unit(float(ant["reported"]), unit)
        ext_spec = spec.replace("pooled_year1", "pooled_extended")
        ext = estimate_row(estimates, key, ext_spec, "post_extended") or estimate_row(
            estimates, key, spec, "post_extended"
        )
        if ext is not None:
            entry["ext"] = with_unit(float(ext["reported"]), unit)
        out[key.lower()] = entry
    return out


def check_value(checks: pl.DataFrame, key: str, check: str) -> float:
    """Estimate from one robustness check (model scale)."""
    return float(
        checks.filter((pl.col("key") == key) & (pl.col("check") == check))["estimate"].item()
    )


def extra_variables(claims: pl.DataFrame) -> dict[str, Any]:
    """Numbers cited in the discussion: placebo, replication, power, equity, heterogeneity."""
    checks = pl.read_csv(RESULTS / "robustness_checks.csv", infer_schema_length=None)
    bounds = pl.read_csv(RESULTS / "honestdid_bounds.csv", infer_schema_length=None)
    replication = pl.read_csv(RESULTS / "replication_pandey.csv")
    mde = pl.read_csv(RESULTS / "mde_fitted_sc.csv")
    assoc = pl.read_csv(RESULTS / "equity_associations.csv", infer_schema_length=None)
    zones = pl.read_csv(RESULTS / "zone_spillover_effects.csv")
    het = pl.read_csv(RESULTS / "heterogeneity.csv", infer_schema_length=None)
    groups = pl.read_csv(FINAL_DIR / "zone_groups.csv")

    def pct(log_points: float) -> str:
        return f"{signed(100 * float(np.expm1(log_points)))}%"

    original = bounds.filter((pl.col("key") == "T2") & (pl.col("restriction") == "original"))
    t2_es = original.row(0, named=True)
    rep = {(r["control_group"], r["week_convention"]): r for r in replication.iter_rows(named=True)}
    iso, far = rep[("upper_manhattan", "iso")], rep[("far_control", "iso")]

    def corr(column: str) -> str:
        value = assoc.filter((pl.col("model") == "bivariate") & (pl.col("covariate") == column))
        return signed(float(value["weighted_correlation"].item()), 2)

    def level(cut: str, key: str, name: str) -> str:
        row = het.filter(
            (pl.col("cut") == cut) & (pl.col("key") == key) & (pl.col("level") == name)
        )
        return f"{signed(float(row['percent'].item()))}%"

    counts = claims["label"].value_counts()
    tally = {r["label"]: int(r["count"]) for r in counts.iter_rows(named=True)}
    primary = claims.filter(pl.col("family") == "primary")
    return {
        "labels": {
            "robust": tally.get("robust", 0),
            "fragile": tally.get("fragile", 0),
            "not_supported": tally.get("not supported", 0),
            "total": claims.height,
            "primary_fragile": int((primary["label"] == "fragile").sum()),
            "primary_not_supported": int((primary["label"] == "not supported").sum()),
        },
        "placebo": {
            "t2": pct(check_value(checks, "T2", "placebo date 2024-01-07")),
            "t3": pct(check_value(checks, "T3", "placebo date 2024-01-07")),
            "s1": pct(check_value(checks, "S1", "placebo date 2024-01-07")),
            "t2_intermediate": pct(check_value(checks, "T2", "control: intermediate band")),
            "s1_intermediate": pct(check_value(checks, "S1", "control: intermediate band")),
        },
        "t2_event_study_ci": (
            f"{signed(100 * t2_es['lb'])} to {signed(100 * t2_es['ub'])} log points"
        ),
        "pandey": {
            "beta": signed(float(iso["beta"]), 4),
            "se": f"{float(iso['se']):.4f}",
            "published": signed(float(iso["published_beta"]), 4),
            "published_se": f"{float(iso['published_se']):.4f}",
            "far_beta": signed(float(far["beta"]), 4),
            "far_se": f"{float(far['se']):.4f}",
        },
        "mde": {
            r["key"].lower(): f"{float(r['mde_80pct_power']):.1f}"
            for r in mde.iter_rows(named=True)
        },
        "equity": {
            "income": corr("median_income_popweighted"),
            "no_vehicle": corr("share_no_vehicle"),
            "poverty": corr("poverty_rate"),
            "asthma": corr("asthma_ed_rate_adults"),
            "zones": int(zones.height),
            "tau": f"{100 * float(zones['eb_tau2'][0]) ** 0.5:.1f}",
        },
        "het": {
            "t3_weekday": level("weekday_vs_weekend", "T3", "weekday"),
            "t3_weekend": level("weekday_vs_weekend", "T3", "weekend"),
            "t2_peak": level("peak_vs_overnight", "T2", "peak"),
            "t2_overnight": level("peak_vs_overnight", "T2", "overnight"),
            "s1_manhattan": level("borough", "S1", "Manhattan"),
            "s1_brooklyn": level("borough", "S1", "Brooklyn"),
            "s1_queens": level("borough", "S1", "Queens"),
        },
        "zones": {g: int(n) for g, n in groups.group_by("group").len().iter_rows()},
    }


def coverage_table() -> str:
    """Dataset coverage table, generated from data/catalog/profiles.json (as in docs/)."""
    import json

    from cordon.ingest.catalog import BEGIN, END, render_table

    profiles = json.loads((REPO_ROOT / "data" / "catalog" / "profiles.json").read_text())
    return render_table(profiles).replace(BEGIN, "").replace(END, "").strip()


def write_tables() -> None:
    """Markdown tables for the paper and site, from the same functions as docs/."""
    GENERATED.mkdir(parents=True, exist_ok=True)
    estimates = pl.read_csv(RESULTS / "estimates.csv", infer_schema_length=None)
    pretrends = pl.read_csv(RESULTS / "pretrend_tests.csv")
    tables = {
        "claims.md": page.claims_section(),
        "holm.md": page.holm_section(),
        "primary_did.md": page.did_table(estimates, pretrends, "primary"),
        "primary_sc.md": page.synthetic_table(estimates, "primary"),
        "secondary_did.md": page.did_table(estimates, pretrends, "secondary"),
        "secondary_sc.md": page.synthetic_table(estimates, "secondary"),
        "spillover_bh.md": page.spillover_bh_section(),
        "spillover_did.md": page.did_table(estimates, pretrends, "spillover"),
        "spillover_sc.md": page.synthetic_table(estimates, "spillover"),
        "heterogeneity.md": page.heterogeneity_section(),
        "zones.md": page.zone_section(),
        "honestdid.md": page.honest_section(),
        "checks.md": page.checks_section(),
        "dowhy.md": page.dowhy_section(),
        "replication.md": page.replication_section(),
        "crosschecks.md": page.crosscheck_section(),
    }
    tables["coverage.md"] = coverage_table()
    for name, text in tables.items():
        (GENERATED / name).write_text(
            "<!-- Generated by cordon.viz.report_inputs from results/. Do not edit. -->\n\n"
            + text.rstrip()
            + "\n"
        )


def main() -> None:
    """Write report/_variables.yml and report/_generated/."""
    estimates = pl.read_csv(RESULTS / "estimates.csv", infer_schema_length=None)
    claims = pl.read_csv(RESULTS / "claims.csv", infer_schema_length=None)
    variables = {**outcome_variables(estimates, claims), **extra_variables(claims)}
    (REPORT / "_variables.yml").write_text(
        "# Generated by cordon.viz.report_inputs from results/. Do not edit.\n"
        + yaml.safe_dump(variables, sort_keys=True, allow_unicode=True)
    )
    write_tables()


if __name__ == "__main__":
    main()
