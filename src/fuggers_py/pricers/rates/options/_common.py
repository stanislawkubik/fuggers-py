"""Shared helpers for rates option pricing.

The helpers in this module glue option products to the curve and volatility
containers used by the pricing engines. Input rates and volatilities are raw
decimals unless a return type explicitly represents a currency amount.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from math import erf, exp, pi, sqrt
from typing import Iterable

from fuggers_py.core.ids import YearMonth
from fuggers_py.core.types import Date
from fuggers_py.market.state import AnalyticsCurves
from fuggers_py.market.vol_surfaces import VolPoint, VolQuoteType, VolatilitySurface
from fuggers_py.pricers.rates.futures import DeliveryOptionModel, fair_futures_price
from fuggers_py.pricers.rates.swap_pricer import SwapPricer
from fuggers_py.pricers.rates._curve_resolver import (
    forward_rate_from_curve,
    resolve_discount_curve,
    resolve_projection_curve,
)
from fuggers_py.products.rates.futures import DeliverableBasket
from fuggers_py.products.rates.options._common import _to_decimal
from fuggers_py.products.rates.options import CapFloor, FuturesOption, OptionType, Swaption
from fuggers_py.products.rates import PayReceive


def _year_fraction(start: Date, end: Date) -> Decimal:
    """Return ACT/365 year fraction between two dates."""
    if end <= start:
        return Decimal(0)
    return Decimal(start.days_between(end)) / Decimal(365)


def _normal_cdf(value: float) -> float:
    """Return the standard normal CDF."""
    return 0.5 * (1.0 + erf(value / sqrt(2.0)))


def _normal_pdf(value: float) -> float:
    """Return the standard normal PDF."""
    return exp(-0.5 * value * value) / sqrt(2.0 * pi)


def _surface_from_inputs(
    curves: AnalyticsCurves | None,
    vol_surface: VolatilitySurface | None,
) -> VolatilitySurface | None:
    """Return the explicit surface or the one attached to the curves object."""
    if vol_surface is not None:
        return vol_surface
    if curves is None:
        return None
    candidate = curves.vol_surface
    if isinstance(candidate, VolatilitySurface):
        return candidate
    return None


def _month_distance(lhs: object, rhs: object) -> int:
    """Return the absolute month distance between two year-month values."""
    return abs((lhs.year * 12 + lhs.month) - (rhs.year * 12 + rhs.month))


def _strike_distance(lhs: Decimal | None, rhs: Decimal | None) -> Decimal:
    """Return a distance metric that prefers exact strike matches."""
    if lhs is None and rhs is None:
        return Decimal(0)
    if lhs is None or rhs is None:
        return Decimal("1000000")
    return abs(lhs - rhs)


def _resolve_surface_volatility(
    curves: AnalyticsCurves | None,
    *,
    expiry_date: Date,
    tenor_date: Date | None,
    strike: Decimal,
    quote_type: VolQuoteType,
    vol_surface: VolatilitySurface | None = None,
    explicit_volatility: object | None = None,
) -> Decimal:
    """Resolve a volatility quote from an explicit value or a surface lookup."""
    if explicit_volatility is not None:
        return _to_decimal(explicit_volatility)

    surface = _surface_from_inputs(curves, vol_surface)
    if surface is None:
        raise ValueError("A volatility or VolatilitySurface is required to price the option.")

    expiry_month = YearMonth(expiry_date.year(), expiry_date.month())
    tenor_month = None
    if tenor_date is not None:
        tenor_month = YearMonth(tenor_date.year(), tenor_date.month())

    points = tuple(point for point in surface.points if point.quote_type is quote_type)
    if not points:
        points = surface.points
    if not points:
        raise ValueError("VolatilitySurface contains no points.")

    def sort_key(point: VolPoint) -> tuple[int, int, Decimal]:
        tenor_distance = 0 if tenor_month is None or point.tenor is None else _month_distance(point.tenor, tenor_month)
        if tenor_month is not None and point.tenor is None:
            tenor_distance = 10_000
        return (
            _month_distance(point.expiry, expiry_month),
            tenor_distance,
            _strike_distance(point.strike, strike),
        )

    return min(points, key=sort_key).volatility


def _time_to_expiry(expiry_date: Date, valuation_date: Date) -> Decimal:
    """Return the option time to expiry in ACT/365 years."""
    return _year_fraction(valuation_date, expiry_date)


def _scale_greeks(greeks: "OptionGreeks", factor: object) -> "OptionGreeks":
    """Scale greeks by a currency or notional factor."""
    scalar = _to_decimal(factor)
    return OptionGreeks(
        delta=greeks.delta * scalar,
        gamma=greeks.gamma * scalar,
        vega=greeks.vega * scalar,
        theta=greeks.theta * scalar,
        rho=greeks.rho * scalar,
    )


def _sum_greeks(greeks: Iterable["OptionGreeks"]) -> "OptionGreeks":
    """Add greeks component-wise."""
    delta = gamma = vega = theta = rho = Decimal(0)
    for item in greeks:
        delta += item.delta
        gamma += item.gamma
        vega += item.vega
        theta += item.theta
        rho += item.rho
    return OptionGreeks(delta=delta, gamma=gamma, vega=vega, theta=theta, rho=rho)


@dataclass(frozen=True, slots=True)
class OptionGreeks:
    """Greeks for a rates option.

    The sensitivities are signed in the usual market direction: delta and rho
    reflect the value change for higher forwards or rates, respectively.
    """

    delta: Decimal = Decimal(0)
    gamma: Decimal = Decimal(0)
    vega: Decimal = Decimal(0)
    theta: Decimal = Decimal(0)
    rho: Decimal = Decimal(0)


@dataclass(frozen=True, slots=True)
class OptionFormulaResult:
    """Result of a closed-form option valuation.

    Attributes
    ----------
    option_type
        Call or put classification.
    forward
        Forward rate or futures price, depending on the instrument.
    strike
        Strike in the same units as `forward`.
    volatility
        Raw-decimal volatility quote used in the formula.
    expiry_years
        Time to expiry in ACT/365 years.
    discount_factor
        Discount factor to the valuation date.
    present_value
        Option value before any external contract-multiplier or annuity
        scaling is applied by a pricer.
    intrinsic_value
        Intrinsic value component at valuation.
    time_value
        Time value component of the result.
    greeks
        Model greeks in the same scaling as the present value.
    """

    option_type: OptionType
    forward: Decimal
    strike: Decimal
    volatility: Decimal
    expiry_years: Decimal
    discount_factor: Decimal
    present_value: Decimal
    intrinsic_value: Decimal
    time_value: Decimal
    greeks: OptionGreeks


@dataclass(frozen=True, slots=True)
class SwaptionPricingResult:
    """Swaption valuation result expressed as a currency present value.

    ``present_value`` is the annuity-scaled option value in swap currency and
    the greeks are scaled to the same convention.
    """

    forward_rate: Decimal
    strike: Decimal
    annuity: Decimal
    volatility: Decimal
    expiry_years: Decimal
    present_value: Decimal
    greeks: OptionGreeks


@dataclass(frozen=True, slots=True)
class CapFloorletPricingResult:
    """Single cap/floor optionlet result.

    The optionlet result reports the per-period forward, strike, volatility,
    accrual factor, discount factor, PV, and greeks.
    """

    start_date: Date
    end_date: Date
    payment_date: Date
    forward_rate: Decimal
    strike: Decimal
    volatility: Decimal
    expiry_years: Decimal
    accrual_factor: Decimal
    discount_factor: Decimal
    present_value: Decimal
    greeks: OptionGreeks


@dataclass(frozen=True, slots=True)
class CapFloorPricingResult:
    """Aggregate cap/floor valuation result.

    The aggregate value is the sum of the optionlet present values, and the
    greeks are the sum of the optionlet greeks.
    """

    present_value: Decimal
    optionlets: tuple[CapFloorletPricingResult, ...]
    greeks: OptionGreeks


@dataclass(frozen=True, slots=True)
class FuturesOptionPricingResult:
    """Futures option valuation result expressed in currency units.

    The `futures_price` and `strike` are quoted in futures points; the
    `present_value` and `greeks` are scaled to the contract multiplier.
    """

    futures_price: Decimal
    strike: Decimal
    volatility: Decimal
    expiry_years: Decimal
    contract_multiplier: Decimal
    discount_factor: Decimal
    delivery_option_adjustment: Decimal
    present_value: Decimal
    greeks: OptionGreeks


@dataclass(frozen=True, slots=True)
class _CapFloorletInputs:
    """Internal cap/floor optionlet inputs."""

    start_date: Date
    end_date: Date
    payment_date: Date
    forward_rate: Decimal
    accrual_factor: Decimal
    discount_factor: Decimal
    expiry_years: Decimal


def swaption_context(
    swaption: Swaption,
    curves: AnalyticsCurves,
    *,
    valuation_date: Date | None = None,
    swap_pricer: SwapPricer | None = None,
) -> tuple[Decimal, Decimal, Date]:
    """Return the swaption forward rate, annuity, and valuation date."""
    pricer = swap_pricer or SwapPricer()
    discount_curve = resolve_discount_curve(curves, swaption.currency())
    resolved_valuation_date = valuation_date or discount_curve.reference_date()
    return (
        pricer.par_rate(swaption.underlying_swap, curves),
        pricer.annuity(swaption.underlying_swap, curves),
        resolved_valuation_date,
    )


def cap_floor_context(
    cap_floor: CapFloor,
    curves: AnalyticsCurves,
    *,
    valuation_date: Date | None = None,
) -> tuple[tuple[_CapFloorletInputs, ...], Date]:
    """Return cap/floor optionlet inputs and the valuation date."""
    discount_curve = resolve_discount_curve(curves, cap_floor.currency())
    projection_curve = resolve_projection_curve(
        curves,
        currency=cap_floor.floating_leg.currency,
        index_name=cap_floor.floating_leg.index_name,
        index_tenor=cap_floor.floating_leg.index_tenor,
    )
    resolved_valuation_date = valuation_date or discount_curve.reference_date()
    optionlets: list[_CapFloorletInputs] = []
    for period in cap_floor.optionlet_periods():
        optionlets.append(
            _CapFloorletInputs(
                start_date=period.start_date,
                end_date=period.end_date,
                payment_date=period.payment_date,
                forward_rate=forward_rate_from_curve(
                    projection_curve,
                    period.start_date,
                    period.end_date,
                    day_count_convention=cap_floor.floating_leg.day_count_convention,
                ),
                accrual_factor=period.year_fraction,
                discount_factor=discount_curve.discount_factor(period.payment_date),
                expiry_years=_time_to_expiry(period.start_date, resolved_valuation_date),
            )
        )
    return tuple(optionlets), resolved_valuation_date


def futures_option_context(
    option: FuturesOption,
    *,
    curves: AnalyticsCurves | None = None,
    valuation_date: Date | None = None,
    futures_price: object | None = None,
    basket: DeliverableBasket | None = None,
    delivery_option_model: DeliveryOptionModel | None = None,
) -> tuple[Decimal, Decimal, Decimal, Date]:
    """Return futures price, delivery-option adjustment, discount factor, and valuation date."""
    if futures_price is not None:
        resolved_price = _to_decimal(futures_price)
        delivery_adjustment = Decimal(0)
    elif basket is not None:
        fair_value = fair_futures_price(
            option.underlying_future,
            basket,
            delivery_option_model=delivery_option_model,
        )
        resolved_price = fair_value.fair_futures_price
        delivery_adjustment = fair_value.delivery_option_adjustment
    else:
        raise ValueError("Futures option pricing requires futures_price or a deliverable basket.")

    if curves is not None:
        discount_curve = resolve_discount_curve(curves, option.currency())
        resolved_valuation_date = valuation_date or discount_curve.reference_date()
        discount_factor = discount_curve.discount_factor(option.expiry_date)
    else:
        resolved_valuation_date = valuation_date or option.expiry_date
        discount_factor = Decimal(1)
    return resolved_price, delivery_adjustment, discount_factor, resolved_valuation_date


def swaption_option_type(swaption: Swaption) -> OptionType:
    """Return the call/put type implied by the swaption exercise direction."""
    return OptionType.CALL if swaption.exercise_into is PayReceive.PAY else OptionType.PUT


__all__ = [
    "CapFloorPricingResult",
    "CapFloorletPricingResult",
    "FuturesOptionPricingResult",
    "OptionFormulaResult",
    "OptionGreeks",
    "SwaptionPricingResult",
    "cap_floor_context",
    "futures_option_context",
    "swaption_context",
    "swaption_option_type",
    "_normal_cdf",
    "_normal_pdf",
    "_resolve_surface_volatility",
    "_scale_greeks",
    "_sum_greeks",
    "_time_to_expiry",
    "_to_decimal",
]
