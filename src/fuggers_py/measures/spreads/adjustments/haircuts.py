"""Haircut-driven spread overlays.

Haircut overlays are returned as raw decimal spread adjustments translated
from funding drag and financing base assumptions.
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
class HaircutAdjustmentBreakdown(SpreadAdjustmentBreakdown):
    """Detailed haircut spread adjustment breakdown."""

    haircut: Decimal
    repo_rate: Decimal
    haircut_funding_rate: Decimal
    year_fraction: Decimal
    collateral_value: Decimal
    financing_base: Decimal
    haircut_amount: Decimal
    drag_amount: Decimal

    def __post_init__(self) -> None:
        SpreadAdjustmentBreakdown.__post_init__(self)
        object.__setattr__(self, "haircut", _to_decimal(self.haircut))
        object.__setattr__(self, "repo_rate", _to_decimal(self.repo_rate))
        object.__setattr__(self, "haircut_funding_rate", _to_decimal(self.haircut_funding_rate))
        object.__setattr__(self, "year_fraction", _to_decimal(self.year_fraction))
        object.__setattr__(self, "collateral_value", _to_decimal(self.collateral_value))
        object.__setattr__(self, "financing_base", _to_decimal(self.financing_base))
        object.__setattr__(self, "haircut_amount", _to_decimal(self.haircut_amount))
        object.__setattr__(self, "drag_amount", _to_decimal(self.drag_amount))


def haircut_adjustment_breakdown(
    *,
    collateral_value: object,
    haircut: object,
    repo_rate: object,
    haircut_funding_rate: object,
    year_fraction: object = Decimal(1),
    financing_base: object | None = None,
    name: str = "haircut",
) -> HaircutAdjustmentBreakdown:
    """Return the haircut spread adjustment breakdown as raw decimals."""
    from fuggers_py.measures.funding.haircuts import haircut_amount as funding_haircut_amount
    from fuggers_py.measures.funding.haircuts import haircut_drag as funding_haircut_drag

    resolved_collateral_value = _to_decimal(collateral_value)
    resolved_haircut = _to_decimal(haircut)
    resolved_repo_rate = _to_decimal(repo_rate)
    resolved_haircut_funding_rate = _to_decimal(haircut_funding_rate)
    resolved_year_fraction = _to_decimal(year_fraction)
    resolved_financing_base = (
        resolved_collateral_value if financing_base is None else _to_decimal(financing_base)
    )
    if resolved_collateral_value <= Decimal(0):
        raise ValueError("Haircut spread adjustment requires positive collateral_value.")
    if resolved_financing_base <= Decimal(0):
        raise ValueError("Haircut spread adjustment requires positive financing_base.")
    if resolved_year_fraction <= Decimal(0):
        raise ValueError("Haircut spread adjustment requires positive year_fraction.")
    if resolved_haircut < Decimal(0) or resolved_haircut > Decimal(1):
        raise ValueError("Haircut spread adjustment requires haircut between 0 and 1.")

    haircut_amount = funding_haircut_amount(
        collateral_value=resolved_collateral_value,
        haircut=resolved_haircut,
    )
    drag_amount = funding_haircut_drag(
        collateral_value=resolved_collateral_value,
        haircut=resolved_haircut,
        repo_rate=resolved_repo_rate,
        haircut_funding_rate=resolved_haircut_funding_rate,
        year_fraction=resolved_year_fraction,
    )
    spread_adjustment = drag_amount / (resolved_financing_base * resolved_year_fraction)
    return HaircutAdjustmentBreakdown(
        name=name,
        spread_adjustment=spread_adjustment,
        description="Haircut financing drag converted into an annualized spread overlay.",
        haircut=resolved_haircut,
        repo_rate=resolved_repo_rate,
        haircut_funding_rate=resolved_haircut_funding_rate,
        year_fraction=resolved_year_fraction,
        collateral_value=resolved_collateral_value,
        financing_base=resolved_financing_base,
        haircut_amount=haircut_amount,
        drag_amount=drag_amount,
    )


def haircut_spread_adjustment(
    *,
    collateral_value: object,
    haircut: object,
    repo_rate: object,
    haircut_funding_rate: object,
    year_fraction: object = Decimal(1),
    financing_base: object | None = None,
) -> Decimal:
    """Return the haircut spread adjustment as a raw decimal."""
    return haircut_adjustment_breakdown(
        collateral_value=collateral_value,
        haircut=haircut,
        repo_rate=repo_rate,
        haircut_funding_rate=haircut_funding_rate,
        year_fraction=year_fraction,
        financing_base=financing_base,
    ).spread_adjustment


@dataclass(frozen=True, slots=True)
class HaircutSpreadAdjustment(BaseSpreadAdjustment):
    """Haircut-driven spread adjustment with stored inputs."""

    collateral_value: Decimal
    haircut: Decimal
    repo_rate: Decimal
    haircut_funding_rate: Decimal
    year_fraction: Decimal = Decimal(1)
    financing_base: Decimal | None = None
    name: str = "haircut"

    def __post_init__(self) -> None:
        object.__setattr__(self, "collateral_value", _to_decimal(self.collateral_value))
        object.__setattr__(self, "haircut", _to_decimal(self.haircut))
        object.__setattr__(self, "repo_rate", _to_decimal(self.repo_rate))
        object.__setattr__(self, "haircut_funding_rate", _to_decimal(self.haircut_funding_rate))
        object.__setattr__(self, "year_fraction", _to_decimal(self.year_fraction))
        if self.financing_base is not None:
            object.__setattr__(self, "financing_base", _to_decimal(self.financing_base))
        object.__setattr__(self, "name", self.name.strip())

    def breakdown(self) -> HaircutAdjustmentBreakdown:
        """Return the haircut adjustment breakdown."""
        return haircut_adjustment_breakdown(
            collateral_value=self.collateral_value,
            haircut=self.haircut,
            repo_rate=self.repo_rate,
            haircut_funding_rate=self.haircut_funding_rate,
            year_fraction=self.year_fraction,
            financing_base=self.financing_base,
            name=self.name,
        )


__all__ = [
    "HaircutAdjustmentBreakdown",
    "HaircutSpreadAdjustment",
    "haircut_adjustment_breakdown",
    "haircut_spread_adjustment",
]
