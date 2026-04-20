"""Sector compatibility types."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Sector(str, Enum):
    """High-level issuer sector classification."""

    GOVERNMENT = "GOVERNMENT"
    AGENCY = "AGENCY"
    MUNICIPAL = "MUNICIPAL"
    CORPORATE = "CORPORATE"
    FINANCIALS = "FINANCIALS"
    INDUSTRIALS = "INDUSTRIALS"
    UTILITIES = "UTILITIES"
    ETF = "ETF"
    CASH = "CASH"
    OTHER = "OTHER"


@dataclass(frozen=True, slots=True)
class SectorInfo:
    """Sector metadata attached to a bond or issuer."""

    sector: Sector
    issuer: str | None = None
    country: str | None = None
    region: str | None = None
    subsector: str | None = None


__all__ = ["Sector", "SectorInfo"]
