"""Hypothetical new-issue fair-value estimation.

Fair values are reported as clean and dirty prices plus a raw decimal yield.
When a marketed clean price is supplied, concession is measured as
`fair_value_clean_price - marketed_clean_price`, while concession bps is
`marketed_yield - fair_value_yield` scaled to basis points.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Mapping

from fuggers_py.products.bonds.instruments import FixedBondBuilder
from fuggers_py.pricers.bonds import BondPricer
from fuggers_py.reference.bonds.types import YieldCalculationRules
from fuggers_py.core.types import Currency, Date, Frequency, Price
from fuggers_py.market.curves.fitted_bonds import BondFairValueRequest, FittedBondCurve, fair_value_from_fit


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


@dataclass(frozen=True, slots=True)
class NewIssueRequest:
    """Inputs for a hypothetical new-issue fair-value estimate.

    ``regression_exposures`` should carry any fitted-bond regression exposures
    needed by the fitted curve used for fair value.
    """

    issue_date: Date
    maturity_date: Date
    coupon_rate: Decimal
    marketed_clean_price: Decimal | None = None
    currency: Currency = Currency.USD
    frequency: Frequency = Frequency.SEMI_ANNUAL
    regression_exposures: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "coupon_rate", _to_decimal(self.coupon_rate))
        object.__setattr__(self, "regression_exposures", dict(self.regression_exposures))
        if self.marketed_clean_price is not None:
            object.__setattr__(self, "marketed_clean_price", _to_decimal(self.marketed_clean_price))


@dataclass(frozen=True, slots=True)
class NewIssueFairValue:
    """Fair-value estimate for a new issue."""

    fair_value_clean_price: Decimal
    fair_value_dirty_price: Decimal
    fair_value_yield: Decimal
    concession_price: Decimal | None
    concession_bps: Decimal | None


def estimate_new_issue_fair_value(
    fit_result: FittedBondCurve,
    request: NewIssueRequest,
) -> NewIssueFairValue:
    """Estimate new-issue fair value from a fitted-bond curve.

    The request passes ``regression_exposures`` through to the fitted-bond
    fair-value helper so the fitted regression overlay can be re-evaluated
    consistently.
    """
    bond = (
        FixedBondBuilder.new()
        .with_issue_date(request.issue_date)
        .with_maturity_date(request.maturity_date)
        .with_coupon_rate(request.coupon_rate)
        .with_frequency(request.frequency)
        .with_currency(request.currency)
        .with_rules(YieldCalculationRules.us_corporate())
        .build()
    )
    fair_value = fair_value_from_fit(
        fit_result,
        BondFairValueRequest(
            bond=bond,
            settlement_date=fit_result.reference_date,
            regression_exposures=request.regression_exposures,
        ),
    )
    if request.marketed_clean_price is None:
        concession_price = None
        concession_bps = None
    else:
        marketed_yield = BondPricer().yield_from_price(
            bond,
            Price.new(request.marketed_clean_price, request.currency),
            fit_result.reference_date,
        ).ytm.value()
        concession_price = fair_value.fair_value_clean_price - request.marketed_clean_price
        concession_bps = (marketed_yield - fair_value.fair_value_yield) * Decimal("10000")
    return NewIssueFairValue(
        fair_value_clean_price=fair_value.fair_value_clean_price,
        fair_value_dirty_price=fair_value.fair_value_dirty_price,
        fair_value_yield=fair_value.fair_value_yield,
        concession_price=concession_price,
        concession_bps=concession_bps,
    )


__all__ = ["NewIssueFairValue", "NewIssueRequest", "estimate_new_issue_fair_value"]
