"""Analytics configuration objects.

These values control settlement anchoring, weighting, and key-rate tenor
selection across the portfolio analytics layer.
"""

from __future__ import annotations

from dataclasses import dataclass

from fuggers_py._core import Tenor
from fuggers_py._core.types import Currency, Date
from fuggers_py.curves import STANDARD_KEY_RATE_TENORS

from .weighting import WeightingMethod


@dataclass(frozen=True, slots=True)
class AnalyticsConfig:
    """Configuration for portfolio analytics aggregation.

    The config controls the settlement date used for accrued interest, the
    weighting basis used for portfolio averages, and the key-rate tenors used
    when building tenor profiles.
    """

    settlement_date: Date | None = None
    weighting_method: WeightingMethod = WeightingMethod.DIRTY_VALUE
    key_rate_tenors: tuple[Tenor, ...] = STANDARD_KEY_RATE_TENORS
    default_currency: Currency = Currency.USD


__all__ = ["AnalyticsConfig"]
