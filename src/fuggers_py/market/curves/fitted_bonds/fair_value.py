"""Fair-value helpers for fitted bond curves.

The fair-value helpers distinguish curve-implied dirty and clean prices from
regression-adjusted fair values. Regression adjustments are additive on dirty
price before the accrued-interest subtraction is applied.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Mapping

from fuggers_py.market.quotes import BondQuote
from fuggers_py.pricers.bonds import BondPricer
from fuggers_py.products.bonds.traits import Bond
from fuggers_py.core.traits import YieldCurve
from fuggers_py.core.types import Date, Price
from fuggers_py.core.ids import InstrumentId
from fuggers_py.reference.reference_data import BondReferenceData

from .model import FittedBondCurve
from .regression import evaluate_regression_adjustment


@dataclass(frozen=True, slots=True)
class BondFairValueRequest:
    """Input request for a fitted-bond fair value calculation.

    The request carries the bond, settlement date, and optional regression
    exposures needed to evaluate a fitted fair value against a fitted curve.
    """

    bond: Bond
    settlement_date: Date
    instrument_id: InstrumentId | None = None
    reference_data: BondReferenceData | None = None
    quote: BondQuote | None = None
    regression_exposures: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.instrument_id is not None:
            object.__setattr__(self, "instrument_id", InstrumentId.parse(self.instrument_id))
        object.__setattr__(self, "regression_exposures", dict(self.regression_exposures))
        if self.quote is not None and self.instrument_id is not None and self.quote.instrument_id != self.instrument_id:
            raise ValueError("BondFairValueRequest quote instrument_id must match instrument_id.")


@dataclass(frozen=True, slots=True)
class BondFairValueResult:
    """Fair-value output for a single bond.

    The result keeps both curve-implied and regression-adjusted prices so
    callers can inspect the effect of the regression overlay directly.
    """

    instrument_id: InstrumentId | None
    curve_dirty_price: Decimal
    curve_clean_price: Decimal
    fair_value_dirty_price: Decimal
    fair_value_clean_price: Decimal
    fair_value_yield: Decimal
    regression_adjustment: Decimal


def dirty_price_from_curve(bond: Bond, curve: YieldCurve, settlement_date: Date) -> Decimal:
    """Return the curve-implied dirty price in percent of par.

    The price is the discounted sum of remaining cash flows from the settlement
    date forward, without subtracting accrued interest.
    """
    present_value = Decimal(0)
    for cash_flow in bond.cash_flows(from_date=settlement_date):
        present_value += cash_flow.factored_amount() * curve.discount_factor(cash_flow.date)
    return present_value


def clean_price_from_curve(bond: Bond, curve: YieldCurve, settlement_date: Date) -> Decimal:
    """Return the curve-implied clean price in percent of par.

    The clean price is the dirty price minus accrued interest at the settlement
    date.
    """
    return dirty_price_from_curve(bond, curve, settlement_date) - bond.accrued_interest(settlement_date)


def fair_value_from_curve(bond: Bond, curve: YieldCurve, settlement_date: Date) -> BondFairValueResult:
    """Return a fair-value result without any regression adjustment.

    The curve-implied clean price is converted back to a yield so callers can
    compare the fair-value output to market quotes.
    """
    dirty = dirty_price_from_curve(bond, curve, settlement_date)
    clean = dirty - bond.accrued_interest(settlement_date)
    fair_yield = BondPricer().yield_from_price(
        bond,
        Price.new(clean, bond.currency()),
        settlement_date,
    ).ytm.value()
    return BondFairValueResult(
        instrument_id=None,
        curve_dirty_price=dirty,
        curve_clean_price=clean,
        fair_value_dirty_price=dirty,
        fair_value_clean_price=clean,
        fair_value_yield=fair_yield,
        regression_adjustment=Decimal(0),
    )


def fair_value_from_fit(
    fit_result: FittedBondCurve,
    request: BondFairValueRequest,
) -> BondFairValueResult:
    """Return the fitted fair value including the regression adjustment.

    The regression adjustment is added in dirty-price space before accrued
    interest is subtracted to obtain the fitted clean price.
    """
    pricing_adapter = fit_result.pricing_adapter
    if pricing_adapter is None:
        from .pricing_adapters import NominalGovernmentBondPricingAdapter

        pricing_adapter = NominalGovernmentBondPricingAdapter()

    instrument_id = request.instrument_id or (
        request.quote.instrument_id if request.quote is not None else None
    ) or getattr(request.bond, "instrument_id", None) or (
        request.reference_data.instrument_id if request.reference_data is not None else InstrumentId("FAIR_VALUE_REQUEST")
    )
    instrument_id = InstrumentId.parse(instrument_id)
    base_quote = request.quote or BondQuote(
        instrument_id=instrument_id,
        clean_price=Decimal("100"),
        as_of=request.settlement_date,
        currency=request.bond.currency(),
    )
    accrued_interest = pricing_adapter.observed_dirty_price(
        base_quote,
        bond=request.bond,
        settlement_date=request.settlement_date,
    ) - pricing_adapter.observed_clean_price(
        base_quote,
        bond=request.bond,
        settlement_date=request.settlement_date,
    )
    curve_dirty = pricing_adapter.curve_dirty_price(
        base_quote,
        fit_result.curve,
        bond=request.bond,
        settlement_date=request.settlement_date,
    )
    curve_clean = curve_dirty - accrued_interest
    evaluation_quote = (
        request.quote
        if request.quote is not None
        else BondQuote(
            instrument_id=instrument_id,
            clean_price=curve_clean,
            as_of=request.settlement_date,
            currency=request.bond.currency(),
        )
    )
    regression_adjustment = evaluate_regression_adjustment(
        request.regression_exposures,
        coefficients=fit_result.coefficients,
    )
    fair_dirty = curve_dirty + regression_adjustment
    fair_clean = fair_dirty - accrued_interest
    fair_yield = pricing_adapter.fitted_yield(
        evaluation_quote,
        fair_clean,
        fit_result.curve,
        bond=request.bond,
        settlement_date=request.settlement_date,
    )
    return BondFairValueResult(
        instrument_id=instrument_id,
        curve_dirty_price=curve_dirty,
        curve_clean_price=curve_clean,
        fair_value_dirty_price=fair_dirty,
        fair_value_clean_price=fair_clean,
        fair_value_yield=fair_yield,
        regression_adjustment=regression_adjustment,
    )


__all__ = [
    "BondFairValueRequest",
    "BondFairValueResult",
    "clean_price_from_curve",
    "dirty_price_from_curve",
    "fair_value_from_curve",
    "fair_value_from_fit",
]
