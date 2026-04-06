"""User-facing analytics, desk measures, and report-oriented helpers.

The package groups the public analytics surface into yield, spread, risk,
relative-value, options, credit, funding, cashflow, and YAS subpackages. Raw
decimal units are used for rates and spreads unless a helper explicitly says
otherwise.
"""

from __future__ import annotations

from . import cashflows, credit, funding, options, pricing, risk, rv, spreads, yas, yields
from .errors import AnalyticsError
from .functions import yield_to_maturity
from .yields import current_yield, current_yield_pct, simple_yield

__all__ = [
    "cashflows",
    "credit",
    "funding",
    "options",
    "pricing",
    "risk",
    "rv",
    "spreads",
    "yas",
    "yields",
    "AnalyticsError",
    "current_yield",
    "current_yield_pct",
    "simple_yield",
    "yield_to_maturity",
]
