"""Volatility surface records and source helpers.

This package is the canonical home for volatility surface data structures,
quote conventions, and in-memory surface providers used across rates and
other option workflows.

The scope is intentionally narrow today: it covers stored surfaces and source
helpers, not a full smile, cube, interpolation, calibration, or fitting stack.
"""

from __future__ import annotations

from .sources import InMemoryVolatilitySource, VolatilitySource
from .surface import VolPoint, VolQuoteType, VolSurfaceType, VolatilitySurface

__all__ = [
    "InMemoryVolatilitySource",
    "VolPoint",
    "VolQuoteType",
    "VolSurfaceType",
    "VolatilitySource",
    "VolatilitySurface",
]
