"""Composable balance-sheet spread overlays.

All overlay values are raw decimal spread adjustments. Positive adjustments
increase the base spread.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol, runtime_checkable


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


@dataclass(frozen=True, slots=True, kw_only=True)
class SpreadAdjustmentBreakdown:
    """Single spread-adjustment component."""

    name: str
    spread_adjustment: Decimal
    description: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", self.name.strip())
        object.__setattr__(self, "spread_adjustment", _to_decimal(self.spread_adjustment))
        if self.description is not None:
            object.__setattr__(self, "description", self.description.strip())


@runtime_checkable
class SpreadAdjustment(Protocol):
    """Protocol for spread adjustments that expose a breakdown and scalar view."""

    name: str

    def breakdown(self) -> SpreadAdjustmentBreakdown:
        """Return the detailed adjustment breakdown."""
        ...

    def spread_adjustment(self) -> Decimal:
        """Return the raw decimal spread adjustment."""
        ...


class BaseSpreadAdjustment:
    """Base class for spread adjustments with a default scalar implementation."""

    name: str

    def breakdown(self) -> SpreadAdjustmentBreakdown:
        """Return the detailed adjustment breakdown."""
        raise NotImplementedError

    def spread_adjustment(self) -> Decimal:
        """Return the raw decimal spread adjustment."""
        return self.breakdown().spread_adjustment


@dataclass(frozen=True, slots=True)
class SpreadAdjustmentSummary:
    """Summary of a base spread plus its component adjustments."""

    base_spread: Decimal
    total_adjustment: Decimal
    adjusted_spread: Decimal
    components: tuple[SpreadAdjustmentBreakdown, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "base_spread", _to_decimal(self.base_spread))
        object.__setattr__(self, "total_adjustment", _to_decimal(self.total_adjustment))
        object.__setattr__(self, "adjusted_spread", _to_decimal(self.adjusted_spread))
        object.__setattr__(self, "components", tuple(self.components))


@dataclass(frozen=True, slots=True)
class FundingSpreadOverlayResult:
    """Funding-spread overlay summary with optional credit-spread linkage."""

    base_funding_spread: Decimal
    adjusted_funding_spread: Decimal
    credit_spread: Decimal | None
    adjusted_all_in_spread: Decimal | None
    overlay_summary: SpreadAdjustmentSummary

    def __post_init__(self) -> None:
        object.__setattr__(self, "base_funding_spread", _to_decimal(self.base_funding_spread))
        object.__setattr__(self, "adjusted_funding_spread", _to_decimal(self.adjusted_funding_spread))
        if self.credit_spread is not None:
            object.__setattr__(self, "credit_spread", _to_decimal(self.credit_spread))
        if self.adjusted_all_in_spread is not None:
            object.__setattr__(self, "adjusted_all_in_spread", _to_decimal(self.adjusted_all_in_spread))


def compose_spread_adjustments(
    *,
    base_spread: object = Decimal(0),
    adjustments: tuple[SpreadAdjustment, ...] = (),
) -> SpreadAdjustmentSummary:
    """Compose raw decimal spread adjustments onto a base spread."""
    base_value = _to_decimal(base_spread)
    components = tuple(adjustment.breakdown() for adjustment in adjustments)
    total_adjustment = sum((component.spread_adjustment for component in components), start=Decimal(0))
    return SpreadAdjustmentSummary(
        base_spread=base_value,
        total_adjustment=total_adjustment,
        adjusted_spread=base_value + total_adjustment,
        components=components,
    )


@dataclass(frozen=True, slots=True)
class BalanceSheetSpreadOverlay:
    """Container for composable balance-sheet spread adjustments."""

    adjustments: tuple[SpreadAdjustment, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "adjustments", tuple(self.adjustments))

    def summary(self, *, base_spread: object = Decimal(0)) -> SpreadAdjustmentSummary:
        """Return the overlay summary for a base spread."""
        return compose_spread_adjustments(base_spread=base_spread, adjustments=self.adjustments)

    def apply(self, *, base_spread: object = Decimal(0)) -> SpreadAdjustmentSummary:
        """Alias for :meth:`summary`."""
        return self.summary(base_spread=base_spread)

    def apply_to_funding_spread(
        self,
        *,
        base_funding_spread: object,
        credit_spread: object | None = None,
    ) -> FundingSpreadOverlayResult:
        """Apply the overlay to a funding spread and optional credit spread."""
        overlay_summary = self.summary(base_spread=base_funding_spread)
        resolved_credit_spread = None if credit_spread is None else _to_decimal(credit_spread)
        adjusted_all_in_spread = (
            None if resolved_credit_spread is None else overlay_summary.adjusted_spread + resolved_credit_spread
        )
        return FundingSpreadOverlayResult(
            base_funding_spread=overlay_summary.base_spread,
            adjusted_funding_spread=overlay_summary.adjusted_spread,
            credit_spread=resolved_credit_spread,
            adjusted_all_in_spread=adjusted_all_in_spread,
            overlay_summary=overlay_summary,
        )


def apply_balance_sheet_overlays(
    *,
    base_spread: object,
    adjustments: tuple[SpreadAdjustment, ...] = (),
) -> SpreadAdjustmentSummary:
    """Apply spread adjustments to a base spread."""
    return compose_spread_adjustments(base_spread=base_spread, adjustments=adjustments)


def apply_funding_spread_overlays(
    *,
    base_funding_spread: object,
    adjustments: tuple[SpreadAdjustment, ...] = (),
    credit_spread: object | None = None,
) -> FundingSpreadOverlayResult:
    """Apply spread adjustments to a funding spread and optional credit spread."""
    return BalanceSheetSpreadOverlay(adjustments=adjustments).apply_to_funding_spread(
        base_funding_spread=base_funding_spread,
        credit_spread=credit_spread,
    )


__all__ = [
    "BaseSpreadAdjustment",
    "BalanceSheetSpreadOverlay",
    "FundingSpreadOverlayResult",
    "SpreadAdjustment",
    "SpreadAdjustmentBreakdown",
    "SpreadAdjustmentSummary",
    "apply_balance_sheet_overlays",
    "apply_funding_spread_overlays",
    "compose_spread_adjustments",
]
