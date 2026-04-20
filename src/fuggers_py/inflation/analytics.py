"""Inflation analytics for the first-layer public facade."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from fuggers_py._core import Compounding


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


@dataclass(frozen=True, slots=True)
class LinkerSwapParityCheck:
    """Compare linker-implied breakeven inflation against an inflation swap rate."""

    nominal_yield: Decimal
    real_yield: Decimal
    linker_breakeven: Decimal
    swap_breakeven: Decimal
    parity_gap: Decimal

    def __post_init__(self) -> None:
        for field_name in (
            "nominal_yield",
            "real_yield",
            "linker_breakeven",
            "swap_breakeven",
            "parity_gap",
        ):
            object.__setattr__(self, field_name, _to_decimal(getattr(self, field_name)))


def breakeven_inflation_rate(
    *,
    nominal_yield: object,
    real_yield: object,
    compounding: Compounding = Compounding.ANNUAL,
) -> Decimal:
    """Return the breakeven inflation rate implied by nominal and real yields."""

    nominal = _to_decimal(nominal_yield)
    real = _to_decimal(real_yield)
    if nominal <= Decimal("-1") or real <= Decimal("-1"):
        raise ValueError("breakeven_inflation_rate requires nominal_yield and real_yield greater than -100%.")
    if compounding is Compounding.CONTINUOUS:
        return nominal - real
    return (Decimal(1) + nominal) / (Decimal(1) + real) - Decimal(1)


def nominal_real_yield_basis(
    *,
    nominal_yield: object,
    real_yield: object,
    compounding: Compounding = Compounding.CONTINUOUS,
) -> Decimal:
    """Return the nominal-minus-real yield basis."""

    if compounding is Compounding.CONTINUOUS:
        return _to_decimal(nominal_yield) - _to_decimal(real_yield)
    return breakeven_inflation_rate(
        nominal_yield=nominal_yield,
        real_yield=real_yield,
        compounding=compounding,
    )


def nominal_real_yield_spread(
    *,
    nominal_yield: object,
    real_yield: object,
    compounding: Compounding = Compounding.CONTINUOUS,
) -> Decimal:
    """Alias for the nominal-minus-real yield basis."""

    return nominal_real_yield_basis(
        nominal_yield=nominal_yield,
        real_yield=real_yield,
        compounding=compounding,
    )


def linker_swap_parity_check(
    *,
    nominal_yield: object,
    real_yield: object,
    inflation_swap_rate: object,
    compounding: Compounding = Compounding.ANNUAL,
) -> LinkerSwapParityCheck:
    """Return a simple linker-versus-swap parity comparison."""

    nominal = _to_decimal(nominal_yield)
    real = _to_decimal(real_yield)
    swap_rate = _to_decimal(inflation_swap_rate)
    linker_breakeven = breakeven_inflation_rate(
        nominal_yield=nominal,
        real_yield=real,
        compounding=compounding,
    )
    return LinkerSwapParityCheck(
        nominal_yield=nominal,
        real_yield=real,
        linker_breakeven=linker_breakeven,
        swap_breakeven=swap_rate,
        parity_gap=linker_breakeven - swap_rate,
    )


__all__ = [
    "LinkerSwapParityCheck",
    "breakeven_inflation_rate",
    "linker_swap_parity_check",
    "nominal_real_yield_basis",
    "nominal_real_yield_spread",
]
