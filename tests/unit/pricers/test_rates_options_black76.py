from __future__ import annotations

from decimal import Decimal

from fuggers_py._core import Currency, Date, PayReceive
from fuggers_py._market.state import AnalyticsCurves
from fuggers_py._core import VolSurfaceId, YearMonth
from fuggers_py._pricers.rates.options import Black76Pricer, black76_formula
from fuggers_py._products.rates import FixedFloatSwap, FixedLegSpec, FloatingLegSpec
from fuggers_py._products.rates.options import Swaption
from fuggers_py.vol_surfaces import VolPoint, VolQuoteType, VolSurfaceType, VolatilitySurface

from tests.helpers._rates_helpers import flat_curve, multicurve_analytics_curves, rate_index


def _swaption_curves():
    as_of = Date.from_ymd(2026, 1, 15)
    discount_curve = flat_curve(as_of, "0.03")
    projection_curve = flat_curve(as_of, "0.035")
    curves = multicurve_analytics_curves(
        discount_curve=discount_curve,
        discount_currency=Currency.USD,
        forward_curve=projection_curve,
        projection_curves={rate_index("SOFR", "3M"): projection_curve},
    )
    return as_of, AnalyticsCurves(
        discount_curve=curves.discount_curve,
        forward_curve=curves.forward_curve,
        multicurve_environment=curves.multicurve_environment,
        projection_curves=curves.projection_curves,
        vol_surface=VolatilitySurface(
            surface_id=VolSurfaceId("usd.swaption"),
            surface_type=VolSurfaceType.SWAPTION,
            as_of=as_of,
            points=(
                VolPoint(
                    expiry=YearMonth(2026, 7),
                    tenor=YearMonth(2031, 7),
                    strike=Decimal("0.035"),
                    volatility=Decimal("0.20"),
                    quote_type=VolQuoteType.LOGNORMAL,
                ),
            ),
        ),
    )


def test_black76_formula_satisfies_call_put_parity() -> None:
    call = black76_formula(
        forward=Decimal("100"),
        strike=Decimal("98"),
        volatility=Decimal("0.25"),
        expiry_years=Decimal("1.5"),
        option_type="CALL",
        discount_factor=Decimal("0.97"),
    )
    put = black76_formula(
        forward=Decimal("100"),
        strike=Decimal("98"),
        volatility=Decimal("0.25"),
        expiry_years=Decimal("1.5"),
        option_type="PUT",
        discount_factor=Decimal("0.97"),
    )

    assert round(call.present_value - put.present_value, 12) == round(Decimal("0.97") * Decimal("2"), 12)


def test_black76_swaption_uses_surface_lookup_and_returns_positive_pv() -> None:
    _, curves = _swaption_curves()
    swap = FixedFloatSwap(
        effective_date=Date.from_ymd(2026, 7, 15),
        maturity_date=Date.from_ymd(2031, 7, 15),
        fixed_leg=FixedLegSpec(
            pay_receive=PayReceive.PAY,
            notional=Decimal("1000000"),
            fixed_rate=Decimal("0.035"),
            currency=Currency.USD,
        ),
        floating_leg=FloatingLegSpec(
            pay_receive=PayReceive.RECEIVE,
            notional=Decimal("1000000"),
            index_name="SOFR",
            index_tenor="3M",
            currency=Currency.USD,
        ),
    )
    swaption = Swaption(
        expiry_date=Date.from_ymd(2026, 7, 15),
        underlying_swap=swap,
        strike=Decimal("0.035"),
        exercise_into=PayReceive.PAY,
    )

    pricer = Black76Pricer()
    from_surface = pricer.swaption(swaption, curves)
    explicit = pricer.swaption(swaption, curves, volatility=Decimal("0.20"))

    assert from_surface.present_value == explicit.present_value
    assert from_surface.present_value > Decimal(0)
    assert from_surface.greeks.delta > Decimal(0)
