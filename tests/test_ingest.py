from datetime import date
from typing import Any

import pytest

from cordon.ingest import socrata
from cordon.ingest.coverage import has_usable_pre_period, parse_coverage_date, pre_period_days
from cordon.ingest.misc_sources import citibike_coverage
from cordon.ingest.tlc import file_url, month_range


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("2019-01-01T00:00:00.000", date(2019, 1, 1)),
        ("2023-07-15", date(2023, 7, 15)),
        ("2023-01", date(2023, 1, 1)),
        (2016, date(2016, 1, 1)),
        ("2016", date(2016, 1, 1)),
        (None, None),
        ("", None),
    ],
)
def test_parse_coverage_date_handles_source_formats(raw: Any, expected: date | None) -> None:
    assert parse_coverage_date(raw) == expected


def test_dataset_starting_in_2025_has_no_pre_period() -> None:
    # e.g. MTA CRZ Vehicle Entries (t6yz-b64h) begins on the treatment date.
    assert pre_period_days("2025-01-05T00:00:00.000") == 0
    assert not has_usable_pre_period("2025-01-05")


def test_pre_period_threshold_is_one_year() -> None:
    # 2024 is a leap year: 2024-01-06 to 2025-01-05 is exactly 365 days.
    assert pre_period_days("2024-01-06") == 365
    assert has_usable_pre_period("2024-01-06")
    assert not has_usable_pre_period("2024-01-07")


def test_coverage_query_selects_min_max_count() -> None:
    params = socrata.coverage_query("date")
    assert params == {"$select": "min(date) as start, max(date) as end, count(*) as n"}


def test_levels_query_groups_and_orders() -> None:
    params = socrata.levels_query("facility", limit=10)
    assert params["$group"] == "facility"
    assert params["$order"] == "n DESC"
    assert params["$limit"] == "10"


def test_profile_dataset_parses_socrata_responses(monkeypatch: pytest.MonkeyPatch) -> None:
    responses: dict[str, Any] = {
        "views": {
            "name": "Fake",
            "rowsUpdatedAt": 1,
            "columns": [{"fieldName": "date"}, {"fieldName": ":id"}, {"fieldName": "count"}],
        },
        "coverage": [{"start": "2019-01-01T00:00:00.000", "end": "2026-10-31", "n": "1234"}],
        "levels": [{"level": "A", "n": "1000"}, {"level": "B", "n": "234"}],
    }

    def fake_get_json(url: str, params: dict[str, str] | None = None) -> Any:
        if "/api/views/" in url:
            return responses["views"]
        if params and "$group" in params:
            return responses["levels"]
        return responses["coverage"]

    monkeypatch.setattr(socrata, "_get_json", fake_get_json)
    profile = socrata.profile_dataset("example.org", "abcd-1234", "date", ["kind"])
    assert profile.columns == ["date", "count"]
    assert profile.row_count == 1234
    assert profile.coverage_start == "2019-01-01T00:00:00.000"
    assert profile.levels == {"kind": {"A": 1000, "B": 234}}


def test_month_range_crosses_year_boundary() -> None:
    assert month_range("2024-11", "2025-02") == ["2024-11", "2024-12", "2025-01", "2025-02"]


def test_tlc_file_url() -> None:
    assert file_url("https://x", "yellow", "2025-01") == "https://x/yellow_tripdata_2025-01.parquet"


def test_citibike_coverage_mixes_yearly_and_monthly_archives() -> None:
    keys = [
        "2023-citibike-tripdata.zip",
        "202401-citibike-tripdata.zip",
        "202610-citibike-tripdata.zip",
    ]
    assert citibike_coverage(keys) == ("2023", "202610")
