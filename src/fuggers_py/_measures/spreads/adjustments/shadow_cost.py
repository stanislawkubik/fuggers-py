"""Shadow-cost spread overlays.

Shadow-cost overlays are raw decimal spread adjustments derived from a shadow
cost rate, utilization, and pass-through factor.
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
class ShadowCostAdjustmentBreakdown(SpreadAdjustmentBreakdown):
    """Detailed shadow-cost spread adjustment breakdown."""

    shadow_cost_rate: Decimal
    utilization: Decimal
    pass_through: Decimal
    usage: Decimal | None = None
    capacity: Decimal | None = None

    def __post_init__(self) -> None:
        SpreadAdjustmentBreakdown.__post_init__(self)
        object.__setattr__(self, "shadow_cost_rate", _to_decimal(self.shadow_cost_rate))
        object.__setattr__(self, "utilization", _to_decimal(self.utilization))
        object.__setattr__(self, "pass_through", _to_decimal(self.pass_through))
        if self.usage is not None:
            object.__setattr__(self, "usage", _to_decimal(self.usage))
        if self.capacity is not None:
            object.__setattr__(self, "capacity", _to_decimal(self.capacity))


def utilization_ratio(*, usage: object, capacity: object) -> Decimal:
    """Return utilization as usage divided by capacity."""
    resolved_usage = _to_decimal(usage)
    resolved_capacity = _to_decimal(capacity)
    if resolved_capacity <= Decimal(0):
        raise ValueError("Shadow-cost utilization requires positive capacity.")
    if resolved_usage < Decimal(0):
        raise ValueError("Shadow-cost utilization requires non-negative usage.")
    return resolved_usage / resolved_capacity


def shadow_cost_adjustment_breakdown(
    *,
    shadow_cost_rate: object,
    utilization: object | None = None,
    usage: object | None = None,
    capacity: object | None = None,
    pass_through: object = Decimal(1),
    name: str = "shadow_cost",
) -> ShadowCostAdjustmentBreakdown:
    """Return the shadow-cost spread adjustment breakdown."""
    resolved_shadow_cost_rate = _to_decimal(shadow_cost_rate)
    resolved_pass_through = _to_decimal(pass_through)
    resolved_usage = None if usage is None else _to_decimal(usage)
    resolved_capacity = None if capacity is None else _to_decimal(capacity)
    if utilization is not None:
        resolved_utilization = _to_decimal(utilization)
    elif resolved_usage is not None or resolved_capacity is not None:
        if resolved_usage is None or resolved_capacity is None:
            raise ValueError("Shadow-cost adjustment requires both usage and capacity when utilization is omitted.")
        resolved_utilization = utilization_ratio(usage=resolved_usage, capacity=resolved_capacity)
    else:
        resolved_utilization = Decimal(1)
    if resolved_shadow_cost_rate < Decimal(0):
        raise ValueError("Shadow-cost adjustment requires non-negative shadow_cost_rate.")
    if resolved_utilization < Decimal(0):
        raise ValueError("Shadow-cost adjustment requires non-negative utilization.")
    if resolved_pass_through < Decimal(0):
        raise ValueError("Shadow-cost adjustment requires non-negative pass_through.")

    return ShadowCostAdjustmentBreakdown(
        name=name,
        spread_adjustment=resolved_shadow_cost_rate * resolved_utilization * resolved_pass_through,
        description="Shadow balance-sheet cost scaled by utilization and pass-through.",
        shadow_cost_rate=resolved_shadow_cost_rate,
        utilization=resolved_utilization,
        pass_through=resolved_pass_through,
        usage=resolved_usage,
        capacity=resolved_capacity,
    )


def shadow_cost_spread_adjustment(
    *,
    shadow_cost_rate: object,
    utilization: object | None = None,
    usage: object | None = None,
    capacity: object | None = None,
    pass_through: object = Decimal(1),
) -> Decimal:
    """Return the shadow-cost spread adjustment as a raw decimal."""
    return shadow_cost_adjustment_breakdown(
        shadow_cost_rate=shadow_cost_rate,
        utilization=utilization,
        usage=usage,
        capacity=capacity,
        pass_through=pass_through,
    ).spread_adjustment


@dataclass(frozen=True, slots=True)
class ShadowCostSpreadAdjustment(BaseSpreadAdjustment):
    """Shadow-cost spread adjustment with stored assumptions."""

    shadow_cost_rate: Decimal
    utilization: Decimal | None = None
    usage: Decimal | None = None
    capacity: Decimal | None = None
    pass_through: Decimal = Decimal(1)
    name: str = "shadow_cost"

    def __post_init__(self) -> None:
        object.__setattr__(self, "shadow_cost_rate", _to_decimal(self.shadow_cost_rate))
        if self.utilization is not None:
            object.__setattr__(self, "utilization", _to_decimal(self.utilization))
        if self.usage is not None:
            object.__setattr__(self, "usage", _to_decimal(self.usage))
        if self.capacity is not None:
            object.__setattr__(self, "capacity", _to_decimal(self.capacity))
        object.__setattr__(self, "pass_through", _to_decimal(self.pass_through))
        object.__setattr__(self, "name", self.name.strip())

    def breakdown(self) -> ShadowCostAdjustmentBreakdown:
        """Return the shadow-cost adjustment breakdown."""
        return shadow_cost_adjustment_breakdown(
            shadow_cost_rate=self.shadow_cost_rate,
            utilization=self.utilization,
            usage=self.usage,
            capacity=self.capacity,
            pass_through=self.pass_through,
            name=self.name,
        )


__all__ = [
    "ShadowCostAdjustmentBreakdown",
    "ShadowCostSpreadAdjustment",
    "shadow_cost_adjustment_breakdown",
    "shadow_cost_spread_adjustment",
    "utilization_ratio",
]
