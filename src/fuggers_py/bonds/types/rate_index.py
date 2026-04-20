"""Reference rate indices (`fuggers_py.bonds.types.rate_index`)."""

from __future__ import annotations

from enum import Enum


class RateIndex(str, Enum):
    """Reference rate indices used by floating-rate notes."""

    SOFR = "SOFR"
    SONIA = "SONIA"
    ESTR = "ESTR"
    EURIBOR_3M = "EURIBOR_3M"
    EURIBOR_6M = "EURIBOR_6M"
    LIBOR_1M = "LIBOR_1M"
    LIBOR_3M = "LIBOR_3M"

    def display_name(self) -> str:
        """Return a presentation-friendly name for the index."""
        return self.value.replace("_", " ")


__all__ = ["RateIndex"]
