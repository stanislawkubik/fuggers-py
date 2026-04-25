from __future__ import annotations

import pytest

from fuggers_py.curves._day_count import resolve_curve_day_count


@pytest.mark.parametrize(
    ("label", "expected_name"),
    [
        ("ACT_365_FIXED", "ACT/365F"),
        ("ACT/365F", "ACT/365F"),
        ("ACT / 365F", "ACT/365F"),
        ("ACT/365FIXED", "ACT/365F"),
        ("ACT/ACT", "ACT/ACT ISDA"),
        ("30/360", "30/360 US"),
        ("30E/360", "30E/360"),
        ("30E/360ISDA", "30E/360 ISDA"),
    ],
)
def test_resolve_curve_day_count_accepts_curve_aliases(label: str, expected_name: str) -> None:
    assert resolve_curve_day_count(label).name() == expected_name


def test_resolve_curve_day_count_rejects_invalid_label() -> None:
    with pytest.raises(ValueError, match="Unsupported curve day-count label: NOPE."):
        resolve_curve_day_count("NOPE")
