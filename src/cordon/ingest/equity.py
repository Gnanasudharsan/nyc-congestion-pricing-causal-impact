"""Download the Phase 4 equity inputs (analysis plan section 9; deviations 12-13).

- **ACS 2019-2023 5-year estimates**, census-tract level, from the Census Bureau's
  table-based summary files. They are keyless public downloads. The Census API
  now requires a key (deviation 12).
  - B01003: total population;
  - B19013: median household income;
  - B08201: households, and households with no vehicle;
  - B17001: poverty status (universe, and population below poverty).
- **TIGER/Line 2023 census tracts** for New York State.
- **Asthma ED visits, adults, by NTA 2010** (age-adjusted average annual rate per
  10,000; 2017-2019 is the latest period). From the NYC Environment & Health Data
  Portal's public repository, pinned to a commit, with the NTA 2010 boundaries
  from the same commit (deviation 13).

The raw files go to ``data/raw/equity/`` (gitignored), and each is recorded in
``data/MANIFEST.json``. Run: ``python -m cordon.ingest.equity``.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

import requests

from cordon.config import DATA_DIR, RAW_DIR, REPO_ROOT
from cordon.ingest.download import download_with_resume
from cordon.manifest import ManifestEntry, sha256_file, upsert_entry

LOG = logging.getLogger(__name__)
EQUITY_DIR = RAW_DIR / "equity"
ACS_BASE = (
    "https://www2.census.gov/programs-surveys/acs/summary_file/2023/table-based-SF/data/5YRData"
)
ACS_TABLES = ("b01003", "b19013", "b08201", "b17001")
TIGER_TRACTS = "https://www2.census.gov/geo/tiger/TIGER2023/TRACT/tl_2023_36_tract.zip"
EHDP_COMMIT = "547482b9df589006543e13e8cdf6546e00ed9998"
EHDP_BASE = f"https://raw.githubusercontent.com/nychealth/EHDP-data/{EHDP_COMMIT}"
ASTHMA_INDICATOR = 2384  # Asthma emergency department visits (adults), by NTA
ASTHMA_MEASURE = 1209  # average annual age-adjusted rate per 10,000
ASTHMA_PERIOD = 282  # 2017-2019, the latest period published


def files() -> dict[str, tuple[str, Path]]:
    """Dataset name -> (URL, local path)."""
    targets = {
        f"acs5_2023_{table}": (
            f"{ACS_BASE}/acsdt5y2023-{table}.dat",
            EQUITY_DIR / f"acsdt5y2023-{table}.dat",
        )
        for table in ACS_TABLES
    }
    targets["tiger_2023_tracts_ny"] = (TIGER_TRACTS, EQUITY_DIR / "tl_2023_36_tract.zip")
    targets["ehdp_asthma_ed_adults_nta"] = (
        f"{EHDP_BASE}/indicators/data/{ASTHMA_INDICATOR}.json",
        EQUITY_DIR / f"ehdp_indicator_{ASTHMA_INDICATOR}.json",
    )
    targets["ehdp_nta2010_boundaries"] = (
        f"{EHDP_BASE}/geography/NTA2010.topo.json",
        EQUITY_DIR / "NTA2010.topo.json",
    )
    return targets


def download_small(url: str, path: Path) -> None:
    """Plain download for small files.

    GitHub serves raw files gzip-compressed and reports the compressed size, so
    the resumable downloader's size check does not apply.
    """
    reply = requests.get(url, timeout=120)
    reply.raise_for_status()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(reply.content)


def main() -> None:
    """Download every equity input once and record it in the manifest."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    for dataset, (url, path) in files().items():
        fresh = not path.exists()
        if fresh and "githubusercontent" in url:
            download_small(url, path)
        else:
            download_with_resume(url, path)
        if fresh:
            upsert_entry(
                DATA_DIR / "MANIFEST.json",
                ManifestEntry(
                    dataset=dataset,
                    source_url=url,
                    local_path=str(path.relative_to(REPO_ROOT)),
                    downloaded_at=datetime.now(UTC).isoformat(timespec="seconds"),
                    sha256=sha256_file(path),
                    rows=None,
                    coverage_start=None,
                    coverage_end=None,
                    notes="Phase 4 equity input (cross-sectional; not an outcome).",
                ),
            )
        LOG.info("%s: %s", dataset, path)


if __name__ == "__main__":
    main()
