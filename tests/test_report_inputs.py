"""Formatting helpers that put numbers into the paper."""

from cordon.viz import report_inputs

M = report_inputs.MINUS


def test_signed_uses_a_true_minus_sign() -> None:
    assert report_inputs.signed(-10.335) == f"{M}10.3"
    assert report_inputs.signed(2.36) == "+2.4"
    assert report_inputs.signed(-0.0613, 4) == f"{M}0.0613"


def test_with_unit_formats_percent_and_levels() -> None:
    assert report_inputs.with_unit(-4.36, "percent") == f"{M}4.4%"
    assert report_inputs.with_unit(-2.0125, "µg/m³") == f"{M}2.0 µg/m³"


def test_p_text() -> None:
    assert report_inputs.p_text(0.0004) == "< 0.001"
    assert report_inputs.p_text(0.0476) == "0.048"
