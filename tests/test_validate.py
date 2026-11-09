from datetime import date

import polars as pl
import pytest

from cordon.clean import validate
from cordon.clean.bt import build_panel, flag_closures


def test_duplicate_keys_detects_repeats() -> None:
    frame = pl.DataFrame({"a": [1, 1, 2], "b": ["x", "x", "y"]})
    assert validate.duplicate_keys(frame, ["a", "b"]) == ["1 duplicated keys on ['a', 'b']"]
    assert validate.duplicate_keys(frame.unique(), ["a", "b"]) == []


def test_missing_days_flags_gaps() -> None:
    frame = pl.DataFrame(
        {"unit": ["u", "u", "v"], "date": [date(2024, 1, 1), date(2024, 1, 2), date(2024, 1, 1)]}
    )
    failures = validate.missing_days(frame, "unit", date(2024, 1, 1), date(2024, 1, 2))
    assert failures == ["1 unit values lack 2 days in 2024-01-01..2024-01-02"]


def test_run_all_reports_missing_inputs_instead_of_crashing() -> None:
    def missing() -> list[str]:
        raise FileNotFoundError("nope.parquet")

    results = validate.run_all({"x": missing, "y": lambda: []})
    assert results["y"] == []
    assert results["x"] and "input missing" in results["x"][0]


def test_bt_closure_rule_uses_same_weekday_median() -> None:
    days = pl.date_range(date(2024, 1, 1), date(2024, 2, 25), eager=True)  # 8 weeks
    crossings = [1000] * len(days)
    crossings[7] = 150  # a Monday at 15% of the Monday median -> closure
    crossings[8] = 250  # a Tuesday at 25% -> not a closure
    frame = pl.DataFrame({"facility": ["F"] * len(days), "date": days, "crossings": crossings})
    flagged = flag_closures(frame).filter(pl.col("is_closure"))["date"].to_list()
    assert flagged == [days[7]]


def test_bt_panel_rejects_unregistered_facility() -> None:
    by_class = pl.DataFrame(
        {
            "facility": ["New Bridge"],
            "date": [date(2024, 1, 1)],
            "vehicle_class_category": ["Car"],
            "crossings": [10],
        }
    )
    by_hour = pl.DataFrame(
        {"facility": ["New Bridge"], "date": [date(2024, 1, 1)], "hour": [8], "crossings": [10]}
    )
    with pytest.raises(ValueError, match="pre-registered"):
        build_panel(by_class, by_hour)
