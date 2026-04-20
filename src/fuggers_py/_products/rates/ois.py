"""Tradable overnight indexed swaps.

This is the overnight-indexed alias of
:class:`~fuggers_py._products.rates.fixed_float_swap.FixedFloatSwap` with the
same contract economics and validation rules.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from .fixed_float_swap import FixedFloatSwap


@dataclass(frozen=True, slots=True)
class Ois(FixedFloatSwap):
    """Overnight indexed swap."""

    KIND: ClassVar[str] = "rates.swap.ois"

    def __post_init__(self) -> None:
        """Reuse the fixed-float swap validation."""

        FixedFloatSwap.__post_init__(self)


OvernightIndexedSwap = Ois


__all__ = ["Ois", "OvernightIndexedSwap"]
