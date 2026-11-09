"""Project-wide constants: treatment timing, time zone, and paths.

Every module imports these values from here so the treatment date and
time zone are defined in exactly one place (see docs/adr/0003).
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

TIMEZONE = ZoneInfo("America/New_York")

# Tolling in the Congestion Relief Zone began at 12:00 a.m. on Sunday, January 5, 2025.
TREATMENT_DATE = date(2025, 1, 5)
TREATMENT_START = datetime(2025, 1, 5, 0, 0, tzinfo=TIMEZONE)

# Placebo date used in robustness checks: same weekday one year earlier.
PLACEBO_DATE = date(2024, 1, 7)

# Main pre-period starts in 2023 (after the steepest COVID recovery). See analysis plan.
PRE_PERIOD_START = date(2023, 1, 1)

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
INTERIM_DIR = DATA_DIR / "interim"
PROCESSED_DIR = DATA_DIR / "processed"
FINAL_DIR = DATA_DIR / "final"
MANIFEST_PATH = DATA_DIR / "MANIFEST.json"
RESULTS_DIR = REPO_ROOT / "results"

RANDOM_SEED = 20250105


def is_post_treatment(moment: datetime) -> bool:
    """Return True if a time zone-aware timestamp falls on or after tolling began.

    Naive timestamps are rejected because silently assuming a time zone is a
    common source of off-by-hours errors around DST transitions.
    """
    if moment.tzinfo is None:
        raise ValueError("timestamp must be time zone-aware")
    return moment >= TREATMENT_START
