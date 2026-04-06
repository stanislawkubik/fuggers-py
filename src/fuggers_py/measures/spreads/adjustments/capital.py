"""Capital-charge spread overlays.

Capital overlays return raw decimal spread adjustments derived from capital
consumption, hurdle rate, and pass-through assumptions.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .balance_sheet import BaseSpreadAdjustment, SpreadAdjustmentBreakdown


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


@dataclass(frozen=True, slots=True, kw_only=True)
class CapitalAdjustmentBreakdown(SpreadAdjustmentBreakdown):
    """Detailed capital spread adjustment breakdown."""

    exposure: Decimal
    risk_weight: Decimal
    capital_ratio: Decimal
    hurdle_rate: Decimal
    pass_through: Decimal
    capital_consumed: Decimal
    annual_capital_cost: Decimal
    passed_through_cost: Decimal

    def __post_init__(self) -> None:
        SpreadAdjustmentBreakdown.__post_init__(self)
        object.__setattr__(self, "exposure", _to_decimal(self.exposure))
        object.__setattr__(self, "risk_weight", _to_decimal(self.risk_weight))
        object.__setattr__(self, "capital_ratio", _to_decimal(self.capital_ratio))
        object.__setattr__(self, "hurdle_rate", _to_decimal(self.hurdle_rate))
        object.__setattr__(self, "pass_through", _to_decimal(self.pass_through))
        object.__setattr__(self, "capital_consumed", _to_decimal(self.capital_consumed))
        object.__setattr__(self, "annual_capital_cost", _to_decimal(self.annual_capital_cost))
        object.__setattr__(self, "passed_through_cost", _to_decimal(self.passed_through_cost))


def capital_adjustment_breakdown(
    *,
    exposure: object,
    risk_weight: object,
    capital_ratio: object,
    hurdle_rate: object,
    pass_through: object = Decimal(1),
    name: str = "capital",
) -> CapitalAdjustmentBreakdown:
    """Return the capital spread adjustment breakdown as raw decimals."""
    resolved_exposure = _to_decimal(exposure)
    resolved_risk_weight = _to_decimal(risk_weight)
    resolved_capital_ratio = _to_decimal(capital_ratio)
    resolved_hurdle_rate = _to_decimal(hurdle_rate)
    resolved_pass_through = _to_decimal(pass_through)
    if resolved_exposure <= Decimal(0):
        raise ValueError("Capital spread adjustment requires positive exposure.")
    if resolved_risk_weight < Decimal(0):
        raise ValueError("Capital spread adjustment requires non-negative risk_weight.")
    if resolved_capital_ratio < Decimal(0) or resolved_capital_ratio > Decimal(1):
        raise ValueError("Capital spread adjustment requires capital_ratio between 0 and 1.")
    if resolved_hurdle_rate < Decimal(0):
        raise ValueError("Capital spread adjustment requires non-negative hurdle_rate.")
    if resolved_pass_through < Decimal(0):
        raise ValueError("Capital spread adjustment requires non-negative pass_through.")

    capital_consumed = resolved_exposure * resolved_risk_weight * resolved_capital_ratio
    annual_capital_cost = capital_consumed * resolved_hurdle_rate
    passed_through_cost = annual_capital_cost * resolved_pass_through
    spread_adjustment = passed_through_cost / resolved_exposure
    return CapitalAdjustmentBreakdown(
        name=name,
        spread_adjustment=spread_adjustment,
        description="Capital consumption translated into an annualized spread overlay.",
        exposure=resolved_exposure,
        risk_weight=resolved_risk_weight,
        capital_ratio=resolved_capital_ratio,
        hurdle_rate=resolved_hurdle_rate,
        pass_through=resolved_pass_through,
        capital_consumed=capital_consumed,
        annual_capital_cost=annual_capital_cost,
        passed_through_cost=passed_through_cost,
    )


def capital_spread_adjustment(
    *,
    exposure: object,
    risk_weight: object,
    capital_ratio: object,
    hurdle_rate: object,
    pass_through: object = Decimal(1),
) -> Decimal:
    """Return the capital spread adjustment as a raw decimal."""
    return capital_adjustment_breakdown(
        exposure=exposure,
        risk_weight=risk_weight,
        capital_ratio=capital_ratio,
        hurdle_rate=hurdle_rate,
        pass_through=pass_through,
    ).spread_adjustment


@dataclass(frozen=True, slots=True)
class CapitalSpreadAdjustment(BaseSpreadAdjustment):
    """Capital-charge spread adjustment with stored input assumptions."""

    exposure: Decimal
    risk_weight: Decimal
    capital_ratio: Decimal
    hurdle_rate: Decimal
    pass_through: Decimal = Decimal(1)
    name: str = "capital"

    def __post_init__(self) -> None:
        object.__setattr__(self, "exposure", _to_decimal(self.exposure))
        object.__setattr__(self, "risk_weight", _to_decimal(self.risk_weight))
        object.__setattr__(self, "capital_ratio", _to_decimal(self.capital_ratio))
        object.__setattr__(self, "hurdle_rate", _to_decimal(self.hurdle_rate))
        object.__setattr__(self, "pass_through", _to_decimal(self.pass_through))
        object.__setattr__(self, "name", self.name.strip())

    def breakdown(self) -> CapitalAdjustmentBreakdown:
        """Return the capital adjustment breakdown."""
        return capital_adjustment_breakdown(
            exposure=self.exposure,
            risk_weight=self.risk_weight,
            capital_ratio=self.capital_ratio,
            hurdle_rate=self.hurdle_rate,
            pass_through=self.pass_through,
            name=self.name,
        )


__all__ = [
    "CapitalAdjustmentBreakdown",
    "CapitalSpreadAdjustment",
    "capital_adjustment_breakdown",
    "capital_spread_adjustment",
]
