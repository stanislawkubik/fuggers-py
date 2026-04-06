from __future__ import annotations

from decimal import Decimal

from fuggers_py.core import Currency, Date
from fuggers_py.calc import AnalyticsCurves
from fuggers_py.pricers.rates.options import BachelierPricer, bachelier_formula
from fuggers_py.products.rates.futures import GovernmentBondFuture
from fuggers_py.products.rates.options import FuturesOption

from tests.helpers._rates_helpers import flat_curve


def test_bachelier_formula_supports_negative_forwards_and_parity() -> None:
    call = bachelier_formula(
        forward=Decimal("-0.0020"),
        strike=Decimal("0.0000"),
        volatility=Decimal("0.0100"),
        expiry_years=Decimal("1.0"),
        option_type="CALL",
        discount_factor=Decimal("0.99"),
    )
    put = bachelier_formula(
        forward=Decimal("-0.0020"),
        strike=Decimal("0.0000"),
        volatility=Decimal("0.0100"),
        expiry_years=Decimal("1.0"),
        option_type="PUT",
        discount_factor=Decimal("0.99"),
    )

    assert call.present_value > Decimal(0)
    assert round(call.present_value - put.present_value, 12) == round(Decimal("0.99") * Decimal("-0.0020"), 12)


def test_bachelier_futures_option_prices_in_cash_terms() -> None:
    as_of = Date.from_ymd(2026, 1, 15)
    curves = AnalyticsCurves(discount_curve=flat_curve(as_of, "0.03"))
    option = FuturesOption(
        expiry_date=Date.from_ymd(2026, 2, 15),
        underlying_future=GovernmentBondFuture(delivery_date=Date.from_ymd(2026, 3, 15), currency=Currency.USD),
        strike=Decimal("110"),
        option_type="CALL",
    )

    result = BachelierPricer().futures_option(
        option,
        curves=curves,
        futures_price=Decimal("112.5"),
        volatility=Decimal("1.25"),
        valuation_date=as_of,
    )

    assert result.present_value > Decimal(0)
    assert result.contract_multiplier == Decimal("1000")
    assert result.greeks.delta > Decimal(0)
