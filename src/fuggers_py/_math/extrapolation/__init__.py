"""Extrapolation helpers used by the curve and math layers.

The public API includes simple constant and linear extrapolators plus the
Smith-Wilson discount-factor extrapolator used in fixed-income curve work.
"""

from __future__ import annotations

from .base import ExtrapolationMethod, Extrapolator
from .flat import FlatExtrapolator
from .linear import LinearExtrapolator
from .smith_wilson import SmithWilson

__all__ = [
    "Extrapolator",
    "ExtrapolationMethod",
    "FlatExtrapolator",
    "LinearExtrapolator",
    "SmithWilson",
]
