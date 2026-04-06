from __future__ import annotations

from decimal import Decimal

from fuggers_py.core import Currency, Date
from fuggers_py.calc import AnalyticsCurves
from fuggers_py.core import VolSurfaceId, YearMonth
from fuggers_py.market.vol_surfaces import VolPoint, VolQuoteType, VolSurfaceType, VolatilitySurface
from fuggers_py.pricers.rates.options import (
    BachelierPricer,
    HullWhiteOptionPricer,
    HullWhiteRateOptionModel,
)
from fuggers_py.products.rates import FloatingLegSpec, PayReceive
from fuggers_py.products.rates.options import CapFloor, CapFloorType

from tests.helpers._rates_helpers import flat_curve, multicurve_analytics_curves, rate_index


def _cap_floor_curves() -> AnalyticsCurves:
    as_of = Date.from_ymd(2026, 1, 15)
    discount_curve = flat_curve(as_of, "0.03")
    projection_curve = flat_curve(as_of, "0.04")
    curves = multicurve_analytics_curves(
        discount_curve=discount_curve,
        discount_currency=Currency.USD,
        forward_curve=projection_curve,
        projection_curves={rate_index("SOFR", "3M"): projection_curve},
    )
    return AnalyticsCurves(
        discount_curve=curves.discount_curve,
        forward_curve=curves.forward_curve,
        multicurve_environment=curves.multicurve_environment,
        projection_curves=curves.projection_curves,
        vol_surface=VolatilitySurface(
            surface_id=VolSurfaceId("usd.capfloor"),
            surface_type=VolSurfaceType.CAP_FLOOR,
            as_of=as_of,
            points=(
                VolPoint(
                    expiry=YearMonth(2026, 4),
                    tenor=YearMonth(2026, 7),
                    strike=Decimal("0.03"),
                    volatility=Decimal("0.01"),
                    quote_type=VolQuoteType.NORMAL,
                ),
                VolPoint(
                    expiry=YearMonth(2026, 7),
                    tenor=YearMonth(2026, 10),
                    strike=Decimal("0.03"),
                    volatility=Decimal("0.01"),
                    quote_type=VolQuoteType.NORMAL,
                ),
            ),
        ),
    )


def test_cap_floor_pricer_sums_optionlets_and_cap_exceeds_floor_when_forward_is_above_strike() -> None:
    curves = _cap_floor_curves()
    floating_leg = FloatingLegSpec(
        pay_receive=PayReceive.RECEIVE,
        notional=Decimal("1000000"),
        index_name="SOFR",
        index_tenor="3M",
        currency=Currency.USD,
    )
    cap = CapFloor(
        effective_date=Date.from_ymd(2026, 1, 15),
        maturity_date=Date.from_ymd(2026, 10, 15),
        floating_leg=floating_leg,
        strike=Decimal("0.03"),
        cap_floor_type=CapFloorType.CAP,
    )
    floor = CapFloor(
        effective_date=cap.effective_date,
        maturity_date=cap.maturity_date,
        floating_leg=floating_leg,
        strike=cap.strike,
        cap_floor_type=CapFloorType.FLOOR,
    )

    pricer = BachelierPricer()
    cap_result = pricer.cap_floor(cap, curves, valuation_date=Date.from_ymd(2026, 1, 15))
    floor_result = pricer.cap_floor(floor, curves, valuation_date=Date.from_ymd(2026, 1, 15))

    assert len(cap_result.optionlets) == 3
    assert cap_result.present_value == sum((item.present_value for item in cap_result.optionlets), start=Decimal(0))
    assert cap_result.present_value > floor_result.present_value


def test_hull_white_cap_floor_pricer_uses_parameterized_normal_volatility() -> None:
    curves = _cap_floor_curves()
    cap = CapFloor(
        effective_date=Date.from_ymd(2026, 1, 15),
        maturity_date=Date.from_ymd(2026, 10, 15),
        floating_leg=FloatingLegSpec(
            pay_receive=PayReceive.RECEIVE,
            notional=Decimal("1000000"),
            index_name="SOFR",
            index_tenor="3M",
            currency=Currency.USD,
        ),
        strike=Decimal("0.03"),
        cap_floor_type=CapFloorType.CAP,
    )

    result = HullWhiteOptionPricer(
        HullWhiteRateOptionModel(mean_reversion=Decimal("0.05"), volatility=Decimal("0.01"))
    ).cap_floor(
        cap,
        curves,
        valuation_date=Date.from_ymd(2026, 1, 15),
    )

    assert result.present_value > Decimal(0)
