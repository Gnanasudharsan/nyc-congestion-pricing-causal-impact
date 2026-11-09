from datetime import UTC, datetime

import pytest

from cordon.config import TIMEZONE, TREATMENT_START, is_post_treatment


def test_treatment_starts_at_local_midnight_jan_5_2025() -> None:
    assert TREATMENT_START.isoformat() == "2025-01-05T00:00:00-05:00"


def test_post_treatment_boundary_is_inclusive() -> None:
    assert is_post_treatment(TREATMENT_START)
    assert not is_post_treatment(datetime(2025, 1, 4, 23, 59, tzinfo=TIMEZONE))


def test_utc_timestamps_are_compared_correctly() -> None:
    # 04:59 UTC on Jan 5 is 23:59 on Jan 4 in New York.
    assert not is_post_treatment(datetime(2025, 1, 5, 4, 59, tzinfo=UTC))
    assert is_post_treatment(datetime(2025, 1, 5, 5, 0, tzinfo=UTC))


def test_naive_timestamp_is_rejected() -> None:
    with pytest.raises(ValueError, match="time zone-aware"):
        is_post_treatment(datetime(2025, 1, 5))
