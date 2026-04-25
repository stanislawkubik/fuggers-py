from __future__ import annotations

from decimal import Decimal

import pytest

from fuggers_py._core import Date
from fuggers_py._core import YearMonth
from fuggers_py._runtime.snapshot import InflationFixing, MarketDataSnapshot
from fuggers_py._runtime.sources import InMemoryInflationFixingSource, MarketDataProvider
from fuggers_py.inflation import (
    MissingInflationFixing,
    USD_CPI_U_NSA,
    reference_cpi,
    reference_index_ratio,
)


def _fixing(month: str, value: str) -> InflationFixing:
    return InflationFixing(
        index_name="CPURNSA",
        observation_month=YearMonth.parse(month),
        value=Decimal(value),
    )


def test_reference_cpi_returns_exact_first_of_month_value() -> None:
    source = InMemoryInflationFixingSource(
        [
            _fixing("2024-04", "300"),
            _fixing("2024-05", "331"),
        ]
    )
    provider = MarketDataProvider(inflation_fixing_source=source)

    reference_value = reference_cpi(Date.from_ymd(2024, 7, 1), USD_CPI_U_NSA, provider)
    ratio = reference_index_ratio(
        Date.from_ymd(2024, 7, 1),
        Date.from_ymd(2024, 7, 1),
        USD_CPI_U_NSA,
        provider,
    )

    assert reference_value == Decimal("300")
    assert ratio == Decimal("1")


def test_reference_cpi_returns_exact_last_of_month_value() -> None:
    source = InMemoryInflationFixingSource(
        [
            _fixing("2024-04", "300"),
            _fixing("2024-05", "331"),
        ]
    )

    reference_value = reference_cpi(Date.from_ymd(2024, 7, 31), USD_CPI_U_NSA, source)

    assert reference_value == Decimal("330")


def test_reference_cpi_interpolates_mid_month() -> None:
    snapshot = MarketDataSnapshot(
        inflation_fixings=(
            _fixing("2024-04", "300"),
            _fixing("2024-05", "331"),
        )
    )

    reference_value = reference_cpi(Date.from_ymd(2024, 7, 16), USD_CPI_U_NSA, snapshot)

    assert reference_value == Decimal("315")


def test_reference_cpi_uses_leap_year_february_length() -> None:
    source = InMemoryInflationFixingSource(
        [
            _fixing("2023-11", "280"),
            _fixing("2023-12", "309"),
        ]
    )

    reference_value = reference_cpi(Date.from_ymd(2024, 2, 29), USD_CPI_U_NSA, source)

    assert reference_value == Decimal("308")


def test_reference_cpi_raises_meaningful_error_when_fixing_is_missing() -> None:
    source = InMemoryInflationFixingSource([_fixing("2024-04", "300")])

    with pytest.raises(MissingInflationFixing, match="CPURNSA"):
        reference_cpi(Date.from_ymd(2024, 7, 16), USD_CPI_U_NSA, source)
