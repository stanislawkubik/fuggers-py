"""Internal inflation analytics exports."""

from __future__ import annotations

from fuggers_py.inflation.analytics import (
    LinkerSwapParityCheck,
    breakeven_inflation_rate,
    linker_swap_parity_check,
    nominal_real_yield_basis,
    nominal_real_yield_spread,
)

__all__ = [
    "LinkerSwapParityCheck",
    "breakeven_inflation_rate",
    "linker_swap_parity_check",
    "nominal_real_yield_basis",
    "nominal_real_yield_spread",
]
