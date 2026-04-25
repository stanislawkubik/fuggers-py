"""Bond market identifiers for convention lookup."""

from __future__ import annotations

from enum import Enum


class BondMarket(str, Enum):
    """Named bond markets with bundled convention presets."""

    US_TREASURY = "US_TREASURY"
    US_CORPORATE = "US_CORPORATE"
    UK_GILT = "UK_GILT"
    EUROBOND = "EUROBOND"
    GERMAN_BUND = "GERMAN_BUND"
    JAPANESE_JGB = "JAPANESE_JGB"


__all__ = ["BondMarket"]
