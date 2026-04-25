"""Private curve day-count parsing helpers."""

from __future__ import annotations

from fuggers_py._core.daycounts import DayCount, DayCountConvention

_DAY_COUNT_ALIASES = {
    "ACT/360": "ACT_360",
    "ACT/365F": "ACT_365_FIXED",
    "ACT/365FIXED": "ACT_365_FIXED",
    "ACT/365L": "ACT_365_LEAP",
    "ACT/365LEAP": "ACT_365_LEAP",
    "ACT/ACT": "ACT_ACT_ISDA",
    "ACT/ACTISDA": "ACT_ACT_ISDA",
    "ACT/ACTICMA": "ACT_ACT_ICMA",
    "ACT/ACTAFB": "ACT_ACT_AFB",
    "30/360": "THIRTY_360_US",
    "30/360US": "THIRTY_360_US",
    "30E/360": "THIRTY_360_E",
    "30/360E": "THIRTY_360_E",
    "30E/360ISDA": "THIRTY_360_E_ISDA",
    "30/360GERMAN": "THIRTY_360_GERMAN",
}


def resolve_curve_day_count(label: str) -> DayCount:
    """Return the curve day-count object for a supported label."""

    key = label.strip().upper().replace(" ", "")
    if key in DayCountConvention.__members__:
        return DayCountConvention[key].to_day_count()
    alias = _DAY_COUNT_ALIASES.get(key)
    if alias is not None:
        return DayCountConvention[alias].to_day_count()
    raise ValueError(f"Unsupported curve day-count label: {label}.")
