"""Duration analytics (`fuggers_py._measures.risk.duration`).

Duration outputs are exposed as positive magnitudes. Key-rate helpers use the
standard key-rate tenor grid and the configured symmetric bump size.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .effective import effective_duration
from .key_rate import (
    KeyRateDuration,
    KeyRateDurations,
    KeyRateDurationCalculator,
    STANDARD_KEY_RATE_TENORS,
    key_rate_duration_at_tenor,
)
from .macaulay import macaulay_duration
from .modified import modified_duration, modified_from_macaulay
from .spread_duration import spread_duration

DEFAULT_BUMP_SIZE = 1e-4
SMALL_BUMP_SIZE = 1e-5


@dataclass(frozen=True, slots=True)
class Duration:
    """Wrapper for a duration value.

    Parameters
    ----------
    value:
        Duration expressed as a positive magnitude in years.
    """

    value: Decimal

    def as_decimal(self) -> Decimal:
        """Return the duration value as a Decimal."""

        return self.value


__all__ = [
    "Duration",
    "macaulay_duration",
    "modified_duration",
    "modified_from_macaulay",
    "effective_duration",
    "spread_duration",
    "key_rate_duration_at_tenor",
    "KeyRateDuration",
    "KeyRateDurations",
    "KeyRateDurationCalculator",
    "DEFAULT_BUMP_SIZE",
    "SMALL_BUMP_SIZE",
    "STANDARD_KEY_RATE_TENORS",
]
