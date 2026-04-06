from __future__ import annotations

import pytest

from fuggers_py.core import Currency
from fuggers_py.core import CurrencyPair, VolSurfaceId, YearMonth


def test_currency_pair_normalization_and_roundtrip() -> None:
    pair = CurrencyPair.parse("usd eur")

    assert pair == CurrencyPair.from_string("USDEUR")
    assert pair.base is Currency.USD
    assert pair.quote is Currency.EUR
    assert pair.as_str() == "USD/EUR"
    assert {pair: "fx"}[CurrencyPair.parse("usd/eur")] == "fx"


def test_year_month_roundtrip_and_validation() -> None:
    year_month = YearMonth.parse("2026-03")

    assert year_month == YearMonth.from_string("2026-03")
    assert year_month.year == 2026
    assert year_month.month == 3
    assert year_month.as_str() == "2026-03"
    assert VolSurfaceId.from_string("usd.swaption").as_str() == "usd.swaption"

    with pytest.raises(ValueError):
        YearMonth.parse("2026-13")

