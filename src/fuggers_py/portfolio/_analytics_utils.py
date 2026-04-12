"""Shared portfolio analytics helpers.

These helpers bridge bond-level pricing and risk calculations to the portfolio
analytics layer. They are not part of the main user-facing surface but carry
the same clean/dirty and raw-decimal conventions.
"""

from __future__ import annotations

from decimal import Decimal

from fuggers_py.measures.pricing import BondPricer
from fuggers_py.measures.risk import BondRiskCalculator
from fuggers_py.measures.spreads import OASCalculator, z_spread_from_curve
from fuggers_py.measures.yields import current_yield_from_bond
from fuggers_py.products.bonds.instruments import CallableBond
from fuggers_py.products.bonds.traits import Bond
from fuggers_py.core.types import Date, Price
from fuggers_py.market.curve_support import key_rate_bumped_curve
from fuggers_py.market.curves import DiscountingCurve

from .types import AnalyticsConfig, CashPosition, Holding, PortfolioMetrics, Position, PositionAnalytics, WeightingMethod


def _cash_position_analytics(position: CashPosition) -> PositionAnalytics:
    amount = position.market_value()
    return PositionAnalytics(
        name=position.label,
        market_value=amount,
        dirty_value=amount,
        clean_value=amount,
        accrued_value=Decimal(0),
        duration=Decimal(0),
        convexity=Decimal(0),
        dv01=Decimal(0),
        ytm=None,
        ytw=None,
        ytc=None,
        best_yield=None,
        current_yield=Decimal(0),
        z_spread=None,
        oas=None,
        g_spread=None,
        i_spread=None,
        asw=None,
        best_spread=None,
        spread_duration=Decimal(0),
        cs01=Decimal(0),
        modified_duration=Decimal(0),
        effective_duration=Decimal(0),
        macaulay_duration=Decimal(0),
        effective_convexity=Decimal(0),
        key_rate_profile={},
        liquidity_score=Decimal(1),
        coupon=Decimal(0),
    )


def _clean_price_for(position: Position, settlement_date: Date, curve: DiscountingCurve | None, pricer: BondPricer) -> Price:
    if position.clean_price is not None:
        if isinstance(position.clean_price, Price):
            return position.clean_price
        return Price.new(position.clean_price, position.instrument.currency())
    if position.market_value is not None and position.quantity != 0:
        return Price.new(position.market_value / position.quantity, position.instrument.currency())
    if curve is None:
        raise ValueError("Curve is required when no clean_price or market_value is supplied.")
    return pricer.price_from_curve(position.instrument, curve, settlement_date).clean


def _weight_base(analytics: PositionAnalytics, weighting_method: WeightingMethod) -> Decimal:
    if weighting_method is WeightingMethod.CLEAN_VALUE:
        return analytics.clean_value
    if weighting_method is WeightingMethod.MARKET_VALUE:
        return analytics.market_value
    return analytics.dirty_value


def _weighted_optional_average(
    analytics_list: list[PositionAnalytics],
    *,
    weights: dict[str, Decimal],
    getter,
) -> Decimal | None:
    covered = [(value, weights[item.name]) for item in analytics_list if (value := getter(item)) is not None]
    if not covered:
        return None
    covered_weight = sum((weight for _, weight in covered), Decimal(0))
    if covered_weight == 0:
        return None
    return sum((value * weight for value, weight in covered), Decimal(0)) / covered_weight


def position_analytics(
    position: Position | CashPosition,
    *,
    curve: DiscountingCurve | None,
    settlement_date: Date,
    config: AnalyticsConfig,
    spread_curve: DiscountingCurve | None = None,
    oas_calculator: OASCalculator | None = None,
) -> PositionAnalytics:
    """Return analytics for a single position or cash holding."""

    if isinstance(position, CashPosition):
        return _cash_position_analytics(position)

    if isinstance(position, Holding) and position.analytics is not None:
        return position.analytics

    pricer = BondPricer()
    bond = position.instrument
    clean_price = _clean_price_for(position, settlement_date, curve, pricer)

    if position.market_value is not None:
        clean_value = position.market_value
        accrued_value = bond.accrued_interest(settlement_date) * position.quantity
        dirty_value = clean_value + accrued_value
    elif curve is not None and position.clean_price is None:
        price_result = pricer.price_from_curve(bond, curve, settlement_date)
        clean_value = price_result.clean.as_percentage() * position.quantity
        dirty_value = price_result.dirty.as_percentage() * position.quantity
        accrued_value = price_result.accrued * position.quantity
    else:
        clean_value = clean_price.as_percentage() * position.quantity
        accrued_unit = bond.accrued_interest(settlement_date)
        accrued_value = accrued_unit * position.quantity
        dirty_value = (clean_price.as_percentage() + accrued_unit) * position.quantity

    ytm = pricer.yield_to_maturity(bond, clean_price, settlement_date)
    risk = BondRiskCalculator(bond, ytm, settlement_date).all_metrics()
    ytw = getattr(bond, "yield_to_worst")(clean_price.as_percentage(), settlement_date) if hasattr(bond, "yield_to_worst") else None
    ytc = (
        getattr(bond, "yield_to_first_call")(clean_price.as_percentage(), settlement_date)
        if hasattr(bond, "yield_to_first_call")
        else None
    )

    current_yield = None
    if hasattr(bond, "coupon_rate"):
        current_yield = current_yield_from_bond(bond, clean_price.as_percentage())

    z_spread = None
    if curve is not None:
        z_spread = z_spread_from_curve(
            bond.cash_flows(),
            dirty_price=clean_price.as_percentage() + bond.accrued_interest(settlement_date),
            curve=spread_curve or curve,
            settlement_date=settlement_date,
        )

    oas = None
    if oas_calculator is not None and isinstance(bond, CallableBond) and bond.call_schedule is not None:
        oas = oas_calculator.calculate(bond, clean_price.as_percentage(), settlement_date)

    key_rate_profile: dict[str, Decimal] = {}
    if curve is not None:
        base_dirty_unit = pricer.price_from_curve(bond, curve, settlement_date).dirty.as_percentage()
        for tenor in config.key_rate_tenors:
            bumped_curve = key_rate_bumped_curve(curve, tenor_grid=config.key_rate_tenors, key_tenor=tenor, bump=1e-4)
            bumped_price = pricer.price_from_curve(bond, bumped_curve, settlement_date).dirty.as_percentage()
            key_rate_profile[str(tenor)] = (bumped_price - (base_dirty_unit)) * position.quantity

    spread_duration = risk.modified_duration if z_spread is not None else Decimal(0)
    cs01 = dirty_value * spread_duration / Decimal(10_000) if z_spread is not None else Decimal(0)
    liquidity_score = position.liquidity_score if position.liquidity_score is not None else Decimal(1)
    coupon = None
    if hasattr(bond, "coupon_rate"):
        coupon = bond.coupon_rate()
    elif hasattr(bond, "current_coupon_rate"):
        coupon = bond.current_coupon_rate()
    maturity_years = Decimal(str(max(settlement_date.days_between(bond.maturity_date()), 0) / 365.0))

    return PositionAnalytics(
        name=position.name(),
        market_value=clean_value,
        dirty_value=dirty_value,
        clean_value=clean_value,
        accrued_value=accrued_value,
        duration=risk.modified_duration,
        convexity=risk.convexity,
        dv01=risk.dv01 * position.quantity,
        ytm=ytm.value(),
        ytw=ytw,
        ytc=ytc,
        best_yield=min(value for value in [ytm.value(), ytw, ytc] if value is not None),
        current_yield=current_yield,
        z_spread=z_spread,
        oas=oas,
        g_spread=None,
        i_spread=None,
        asw=None,
        best_spread=oas if oas is not None else z_spread,
        spread_duration=spread_duration,
        cs01=cs01,
        modified_duration=risk.modified_duration,
        effective_duration=risk.modified_duration,
        macaulay_duration=risk.macaulay_duration,
        effective_convexity=risk.convexity,
        key_rate_profile=key_rate_profile,
        liquidity_score=liquidity_score,
        weighted_average_life=maturity_years,
        coupon=coupon,
    )


def aggregate_metrics(
    analytics_list: list[PositionAnalytics],
    *,
    currency,
    weighting_method: WeightingMethod,
) -> PortfolioMetrics:
    """Aggregate a list of position analytics into portfolio metrics."""

    clean_pv = sum((item.clean_value for item in analytics_list), Decimal(0))
    dirty_pv = sum((item.dirty_value for item in analytics_list), Decimal(0))
    accrued = sum((item.accrued_value for item in analytics_list), Decimal(0))
    if not analytics_list:
        return PortfolioMetrics(
            clean_pv=Decimal(0),
            dirty_pv=Decimal(0),
            accrued=Decimal(0),
            duration=Decimal(0),
            convexity=Decimal(0),
            dv01=Decimal(0),
            weights={},
            currency=currency,
        )

    if weighting_method is WeightingMethod.EQUAL:
        equal_weight = Decimal(1) / Decimal(len(analytics_list))
        weights = {item.name: equal_weight for item in analytics_list}
    else:
        total_base = sum((_weight_base(item, weighting_method) for item in analytics_list), Decimal(0))
        weights = {
            item.name: (Decimal(0) if total_base == 0 else _weight_base(item, weighting_method) / total_base)
            for item in analytics_list
        }

    duration = sum((item.duration * weights[item.name] for item in analytics_list), Decimal(0))
    convexity = sum((item.convexity * weights[item.name] for item in analytics_list), Decimal(0))
    dv01 = sum((item.dv01 for item in analytics_list), Decimal(0))
    current_yield = sum(((item.current_yield or Decimal(0)) * weights[item.name] for item in analytics_list), Decimal(0))
    ytm = sum(((item.ytm or Decimal(0)) * weights[item.name] for item in analytics_list), Decimal(0))
    ytw = sum(((item.ytw or item.ytm or Decimal(0)) * weights[item.name] for item in analytics_list), Decimal(0))
    ytc = sum(((item.ytc or Decimal(0)) * weights[item.name] for item in analytics_list), Decimal(0))
    z_spread = sum(((item.z_spread or Decimal(0)) * weights[item.name] for item in analytics_list), Decimal(0))
    oas = sum(((item.oas or Decimal(0)) * weights[item.name] for item in analytics_list), Decimal(0))
    g_spread = _weighted_optional_average(analytics_list, weights=weights, getter=lambda item: item.g_spread)
    i_spread = _weighted_optional_average(analytics_list, weights=weights, getter=lambda item: item.i_spread)
    asw = _weighted_optional_average(analytics_list, weights=weights, getter=lambda item: item.asw)
    spread_duration = sum(((item.spread_duration or Decimal(0)) * weights[item.name] for item in analytics_list), Decimal(0))
    cs01 = sum(((item.cs01 or Decimal(0)) for item in analytics_list), Decimal(0))
    liquidity = sum(((item.liquidity_score or Decimal(0)) * weights[item.name] for item in analytics_list), Decimal(0))
    macaulay_duration = sum(((item.macaulay_duration or Decimal(0)) * weights[item.name] for item in analytics_list), Decimal(0))
    effective_duration = sum(((item.effective_duration or Decimal(0)) * weights[item.name] for item in analytics_list), Decimal(0))
    effective_convexity = sum(((item.effective_convexity or Decimal(0)) * weights[item.name] for item in analytics_list), Decimal(0))
    best_yield = sum(((item.best_yield or item.ytw or item.ytm or Decimal(0)) * weights[item.name] for item in analytics_list), Decimal(0))
    best_spread = sum(((item.best_spread or item.oas or item.z_spread or Decimal(0)) * weights[item.name] for item in analytics_list), Decimal(0))
    weighted_coupon = sum(((item.coupon or Decimal(0)) * weights[item.name] for item in analytics_list), Decimal(0))
    key_rate_profile: dict[str, Decimal] = {}
    for item in analytics_list:
        for tenor, value in item.key_rate_profile.items():
            key_rate_profile[tenor] = key_rate_profile.get(tenor, Decimal(0)) + value

    total_dirty = dirty_pv if dirty_pv != 0 else Decimal(1)
    weighted_average_maturity = sum(
        ((item.weighted_average_life or Decimal(0)) * weights[item.name] for item in analytics_list),
        Decimal(0),
    )

    return PortfolioMetrics(
        clean_pv=clean_pv,
        dirty_pv=dirty_pv,
        accrued=accrued,
        duration=duration,
        convexity=convexity,
        dv01=dv01,
        weights=weights,
        currency=currency,
        current_yield=current_yield,
        ytm=ytm,
        ytw=ytw,
        ytc=ytc,
        best_yield=best_yield,
        z_spread=z_spread,
        oas=oas,
        g_spread=g_spread,
        i_spread=i_spread,
        asw=asw,
        best_spread=best_spread,
        spread_duration=spread_duration,
        cs01=cs01,
        liquidity_score=liquidity,
        key_rate_profile=key_rate_profile,
        total_market_value=clean_pv,
        total_dirty_market_value=dirty_pv,
        total_accrued_interest=accrued,
        cash_value=sum((item.clean_value for item in analytics_list if item.duration == 0 and item.convexity == 0), Decimal(0)),
        holding_count=len(analytics_list),
        priced_count=sum(1 for item in analytics_list if item.clean_value != 0 or item.dirty_value != 0),
        coverage_count=sum(1 for item in analytics_list if item.ytm is not None),
        modified_duration=duration,
        effective_duration=effective_duration,
        macaulay_duration=macaulay_duration,
        effective_convexity=effective_convexity,
        weighted_average_maturity=weighted_average_maturity,
        weighted_average_coupon=weighted_coupon,
    )
