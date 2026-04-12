"""Standalone analytics helpers.

This module provides thin analytics-facing wrappers over the bond-layer
pricing, duration, spread, accrued-interest, and yield-solving machinery.
Where return values are prices, they are expressed as percentage-of-par
``Price`` objects unless a raw decimal is explicitly noted.
"""

from __future__ import annotations

from decimal import Decimal

from fuggers_py.products.bonds.cashflows.accrued import AccruedInterestCalculator, AccruedInterestInputs
from fuggers_py.products.bonds.traits import Bond
from fuggers_py.reference.bonds.types import CompoundingKind, YieldCalculationRules, YieldConvention
from fuggers_py.core.daycounts import DayCountConvention
from fuggers_py.core.types import Compounding, Date, Price, Yield
from fuggers_py.market.curves import DiscountingCurve

from .errors import AnalyticsError
from .pricing import BondPricer
from .risk import (
    effective_convexity as _effective_convexity,
    effective_duration as _effective_duration,
    macaulay_duration as _macaulay_duration,
    modified_duration as _modified_duration,
)
from .risk.convexity import analytical_convexity, price_change_with_convexity
from .risk.dv01 import dv01_per_100_face, notional_from_dv01
from .spreads import z_spread
from .yields import YieldSolver


def _core_compounding(bond: Bond) -> Compounding:
    method = bond.rules().compounding
    if method.kind is CompoundingKind.CONTINUOUS:
        return Compounding.CONTINUOUS
    if method.kind in {CompoundingKind.SIMPLE, CompoundingKind.DISCOUNT}:
        return Compounding.SIMPLE
    if method.frequency == 1:
        return Compounding.ANNUAL
    if method.frequency == 2:
        return Compounding.SEMI_ANNUAL
    if method.frequency == 4:
        return Compounding.QUARTERLY
    if method.frequency == 12:
        return Compounding.MONTHLY
    return Compounding.ANNUAL


def yield_to_maturity(bond: Bond, price: Price, settlement_date: Date) -> Yield:
    """Return yield to maturity from a clean price.

    Parameters
    ----------
    bond:
        Bond to value.
    price:
        Clean price expressed as a :class:`~fuggers_py.core.types.Price`.
    settlement_date:
        Settlement date used for accrued-interest and cashflow filtering.

    Returns
    -------
    Yield
        Raw decimal yield, not a percentage.

    Notes
    -----
    The input ``price`` is interpreted as a clean price.
    """

    return BondPricer().yield_to_maturity(bond, price, settlement_date)


def yield_to_maturity_with_convention(
    bond: Bond, price: Price, settlement_date: Date, convention: YieldConvention
) -> Yield:
    """Return yield to maturity under an explicit bond-market convention.

    Parameters
    ----------
    bond:
        Bond to value.
    price:
        Clean price expressed as a :class:`~fuggers_py.core.types.Price`.
    settlement_date:
        Settlement date used for accrued-interest and cashflow filtering.
    convention:
        Bond-market yield convention to apply.

    Returns
    -------
    Yield
        Raw decimal yield under ``convention``.

    Notes
    -----
    For :attr:`~fuggers_py.reference.bonds.types.YieldConvention.STREET_CONVENTION`,
    this delegates to the standard bond-layer solver. For other conventions,
    the price is converted to a dirty price by adding accrued interest before
    solving.
    """

    if convention is YieldConvention.STREET_CONVENTION:
        return BondPricer().yield_to_maturity(bond, price, settlement_date)

    if price.currency() != bond.currency():
        raise AnalyticsError.invalid_input("Price currency does not match bond currency.")

    dirty_price = price.as_percentage() + bond.accrued_interest(settlement_date)
    rules = bond.rules()
    frequency = max(1, bond.frequency().periods_per_year())
    day_count = rules.yield_day_count_obj()
    future_cashflows = [cf for cf in bond.cash_flows() if cf.date > settlement_date]
    if not future_cashflows:
        raise AnalyticsError.invalid_settlement("No future cashflows remain after settlement.")

    solver = YieldSolver()
    result = solver.solve(
        dirty_price=float(dirty_price),
        cashflows=[float(cf.factored_amount()) for cf in future_cashflows],
        times=[float(day_count.year_fraction(settlement_date, cf.date)) for cf in future_cashflows],
        frequency=frequency,
        convention=convention,
    )
    return Yield.new(Decimal(str(result.yield_value)), _core_compounding(bond))


def dirty_price_from_yield(bond: Bond, ytm: Yield, settlement_date: Date) -> Price:
    """Return the dirty price implied by a yield.

    Parameters
    ----------
    bond:
        Bond to value.
    ytm:
        Yield to maturity as a raw decimal.
    settlement_date:
        Settlement date used for accrued-interest and cashflow filtering.

    Returns
    -------
    Price
        Dirty price in percent of par.
    """

    return BondPricer().price_from_yield(bond, ytm, settlement_date).dirty


def clean_price_from_yield(bond: Bond, ytm: Yield, settlement_date: Date) -> Price:
    """Return the clean price implied by a yield.

    Parameters
    ----------
    bond:
        Bond to value.
    ytm:
        Yield to maturity as a raw decimal.
    settlement_date:
        Settlement date used for accrued-interest and cashflow filtering.

    Returns
    -------
    Price
        Clean price in percent of par.
    """

    return BondPricer().price_from_yield(bond, ytm, settlement_date).clean


def macaulay_duration(bond: Bond, ytm: Yield, settlement_date: Date) -> Decimal:
    """Return Macaulay duration for the bond.

    The result is expressed in years and is measured off the settlement date.
    """

    return _macaulay_duration(bond, ytm, settlement_date)


def modified_duration(bond: Bond, ytm: Yield, settlement_date: Date) -> Decimal:
    """Return modified duration for the bond.

    The result is a raw-year sensitivity per unit yield, measured off the
    settlement date.
    """

    return _modified_duration(bond, ytm, settlement_date)


def effective_duration(bond: Bond, ytm: Yield, settlement_date: Date, *, bump: float = 1e-4) -> Decimal:
    """Return effective duration using a finite yield bump.

    The result is measured off the settlement date. ``bump`` is a raw decimal
    yield shock, so ``1e-4`` means 1 bp.
    """

    return _effective_duration(bond, ytm, settlement_date, bump=bump)


def convexity(bond: Bond, ytm: Yield, settlement_date: Date) -> Decimal:
    """Return analytical convexity for the bond.

    The result is measured off the settlement date and is based on the
    bond's yield/price relationship.
    """

    return analytical_convexity(bond, ytm, settlement_date)


def effective_convexity(bond: Bond, ytm: Yield, settlement_date: Date, *, bump: float = 1e-4) -> Decimal:
    """Return effective convexity using a finite yield bump.

    The result is measured off the settlement date. ``bump`` is a raw decimal
    yield shock, so ``1e-4`` means 1 bp.
    """

    return _effective_convexity(bond, ytm, settlement_date, bump=bump)


def dv01(bond: Bond, ytm: Yield, settlement_date: Date) -> Decimal:
    """Return DV01 per 100 face.

    The result uses the dirty price implied by ``ytm`` at ``settlement_date``.
    It is signed positive when bond value rises as yield falls by 1 bp.
    """

    pricer = BondPricer()
    dirty = pricer.price_from_yield(bond, ytm, settlement_date).dirty.as_percentage()
    md = modified_duration(bond, ytm, settlement_date)
    return dv01_per_100_face(md, dirty)


def dv01_notional(target_dv01: object, modified_duration_value: object, dirty_price: object) -> Decimal:
    """Return notional required to reach a target DV01.

    Parameters
    ----------
    target_dv01:
        Desired DV01 in currency units.
    modified_duration_value:
        Modified duration in years.
    dirty_price:
        Dirty price in percent of par.

    Returns
    -------
    Decimal
        Face notional needed to reach ``target_dv01``.
    """

    return notional_from_dv01(target_dv01, modified_duration_value, dirty_price)


def estimate_price_change(
    modified_duration_value: object,
    convexity_value: object,
    price_value: object,
    yield_change: object,
) -> Decimal:
    """Estimate price change using duration and convexity.

    The estimate uses the standard second-order approximation around the
    current price. ``yield_change`` is a raw decimal shock, so ``0.0001`` means
    1 bp.

    Returns
    -------
    Decimal
        Approximate price change in the same units as ``price_value``.
    """

    return price_change_with_convexity(modified_duration_value, convexity_value, price_value, yield_change)


def price_change_from_duration(
    modified_duration_value: object,
    price_value: object,
    yield_change: object,
) -> Decimal:
    """Estimate first-order price change from modified duration.

    ``yield_change`` is a raw decimal shock, so ``0.0001`` means 1 bp. The
    return value is negative when yield rises and positive when yield falls.

    Returns
    -------
    Decimal
        Approximate price change in the same units as ``price_value``.
    """

    duration = Decimal(str(modified_duration_value))
    price = Decimal(str(price_value))
    delta_yield = Decimal(str(yield_change))
    return -(duration * price * delta_yield)


def parse_day_count(text: str) -> DayCountConvention:
    """Parse a common market day-count string into a core enum value.

    Parameters
    ----------
    text:
        Market-style day-count label such as ``"ACT/360"`` or ``"30E/360"``.

    Returns
    -------
    DayCountConvention
        Matching core day-count enumeration value.

    Raises
    ------
    InvalidInput
        If ``text`` is missing or does not map to a supported alias.
    """

    if not isinstance(text, str):
        raise AnalyticsError.invalid_input("Day-count string must be provided.")
    key = text.strip().upper().replace(" ", "")
    mapping = {
        "ACT/360": DayCountConvention.ACT_360,
        "ACT/365F": DayCountConvention.ACT_365_FIXED,
        "ACT/365FIXED": DayCountConvention.ACT_365_FIXED,
        "ACT/365L": DayCountConvention.ACT_365_LEAP,
        "ACT/365LEAP": DayCountConvention.ACT_365_LEAP,
        "ACT/ACT": DayCountConvention.ACT_ACT_ISDA,
        "ACT/ACTISDA": DayCountConvention.ACT_ACT_ISDA,
        "ACT/ACTICMA": DayCountConvention.ACT_ACT_ICMA,
        "ACT/ACTAFB": DayCountConvention.ACT_ACT_AFB,
        "30/360": DayCountConvention.THIRTY_360_US,
        "30/360US": DayCountConvention.THIRTY_360_US,
        "30E/360": DayCountConvention.THIRTY_360_E,
        "30/360E": DayCountConvention.THIRTY_360_E,
        "30E/360ISDA": DayCountConvention.THIRTY_360_E_ISDA,
        "30/360GERMAN": DayCountConvention.THIRTY_360_GERMAN,
    }
    if key not in mapping:
        raise AnalyticsError.invalid_input(f"Unknown day-count convention: {text!r}.")
    return mapping[key]


def calculate_accrued_interest(inputs: AccruedInterestInputs, *, rules: YieldCalculationRules) -> Decimal:
    """Compatibility wrapper for the standard accrued-interest calculation.

    The return value is accrued interest in raw currency units under
    ``rules``.
    """

    return AccruedInterestCalculator.standard(inputs, rules=rules)


def calculate_macaulay_duration(bond: Bond, ytm: Yield, settlement_date: Date) -> Decimal:
    """Compatibility wrapper for :func:`macaulay_duration`."""

    return macaulay_duration(bond, ytm, settlement_date)


def calculate_modified_duration(bond: Bond, ytm: Yield, settlement_date: Date) -> Decimal:
    """Compatibility wrapper for :func:`modified_duration`."""

    return modified_duration(bond, ytm, settlement_date)


def calculate_yield_to_maturity(bond: Bond, price: Price, settlement_date: Date) -> Yield:
    """Compatibility wrapper for :func:`yield_to_maturity`."""

    return yield_to_maturity(bond, price, settlement_date)


def calculate_z_spread(
    bond: Bond,
    price: Price,
    curve: DiscountingCurve,
    settlement_date: Date,
) -> Decimal:
    """Return z-spread as a raw decimal spread over ``curve``."""

    return z_spread(bond, price, curve, settlement_date)


__all__ = [
    "yield_to_maturity",
    "yield_to_maturity_with_convention",
    "dirty_price_from_yield",
    "clean_price_from_yield",
    "macaulay_duration",
    "modified_duration",
    "effective_duration",
    "convexity",
    "effective_convexity",
    "dv01",
    "dv01_notional",
    "estimate_price_change",
    "price_change_from_duration",
    "parse_day_count",
    "calculate_accrued_interest",
    "calculate_macaulay_duration",
    "calculate_modified_duration",
    "calculate_yield_to_maturity",
    "calculate_z_spread",
]
