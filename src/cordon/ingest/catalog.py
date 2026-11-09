"""Render the generated coverage table in docs/data-catalog.md from profiles.json.

The table sits between two marker comments, so the hand-written commentary
around it is preserved and the numbers inside it are never typed by hand.
Run with ``python -m cordon.ingest.catalog``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cordon.config import REPO_ROOT
from cordon.ingest.audit import PROFILES_PATH

CATALOG_PATH = REPO_ROOT / "docs" / "data-catalog.md"
BEGIN = "<!-- BEGIN GENERATED COVERAGE TABLE -->"
END = "<!-- END GENERATED COVERAGE TABLE -->"


def _date(value: Any) -> str:
    return "—" if value in (None, "") else str(value)[:10]


def _yes_no(value: Any) -> str:
    if value is None:
        return "?"
    return "yes" if value else "**no**"


def socrata_rows(profiles: dict[str, Any]) -> list[str]:
    """One markdown row per Socrata table."""
    rows = []
    for key, profile in profiles.items():
        if key.startswith("_") or profile.get("kind") != "socrata":
            continue
        if "error" in profile:
            rows.append(f"| `{key}` | {profile['id']} | error: {profile['error'][:60]} | | | | |")
            continue
        dataset_id = profile["dataset_id"]
        count = profile["row_count"]
        count_text = "probe only" if count is None else f"{count:,}"
        rows.append(
            f"| `{key}` | [{dataset_id}]({profile['url']}) | {count_text} | "
            f"{_date(profile['coverage_start'])} | {_date(profile['coverage_end'])} | "
            f"{_yes_no(profile['usable_pre_period']) if profile['coverage_start'] else 'n/a'} | "
            f"{profile['role']} |"
        )
    return rows


def other_rows(profiles: dict[str, Any]) -> list[str]:
    """Rows for TLC, EPA, Citi Bike, and weather sources."""
    rows = []
    tlc = profiles.get("tlc", {})
    for service, info in tlc.get("services", {}).items():
        probe_rows = sum(p["rows"] for p in info["probes"])
        rows.append(
            f"| `tlc_{service}` | TLC parquet | {len(info['months_available'])} monthly files "
            f"({probe_rows:,} rows in {len(info['probes'])} probe months) | "
            f"{info['coverage_start']} | {info['coverage_end']} | "
            f"{_yes_no(info['usable_pre_period'])} | {tlc.get('role')} |"
        )
    for name, info in profiles.get("epa_aqs", {}).get("files", {}).items():
        rows.append(
            f"| `epa_{name}` | EPA AQS hourly | {info['rows']:,} "
            f"({len(info['nyc_sites'])} NYC sites) | {_date(info['coverage_start'])} | "
            f"{_date(info['coverage_end'])} | yes (multi-year files) | outcome |"
        )
    bike = profiles.get("citibike")
    if bike:
        rows.append(
            f"| `citibike` | S3 archives | {len(bike['files'])} files | {bike['coverage_start']} | "
            f"{bike['coverage_end']} | {_yes_no(bike['usable_pre_period'])} | outcome |"
        )
    weather = profiles.get("open_meteo")
    if weather and "rows" in weather:
        rows.append(
            f"| `open_meteo` | Open-Meteo archive | {weather['rows']:,} hours | "
            f"{weather['coverage_start']} | {weather['coverage_end']} | yes | covariate |"
        )
    return rows


def render_table(profiles: dict[str, Any]) -> str:
    """Build the full generated block, including the markers."""
    header = [
        BEGIN,
        f"_Generated from `data/catalog/profiles.json` (audited {profiles.get('_audited_at')})._",
        "",
        "| Key | Source | Rows | Coverage start | Coverage end | ≥1 yr pre-period | Role |",
        "|---|---|---|---|---|---|---|",
    ]
    return "\n".join([*header, *socrata_rows(profiles), *other_rows(profiles), END])


def update_catalog(catalog_path: Path = CATALOG_PATH) -> None:
    """Replace the generated block in the catalog, keeping everything else."""
    profiles = json.loads(PROFILES_PATH.read_text())
    text = catalog_path.read_text()
    start, end = text.index(BEGIN), text.index(END) + len(END)
    catalog_path.write_text(text[:start] + render_table(profiles) + text[end:])


if __name__ == "__main__":
    update_catalog()
