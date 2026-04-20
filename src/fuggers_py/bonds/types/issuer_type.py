"""Issuer type enum (`fuggers_py.bonds.types.issuer_type`)."""

from __future__ import annotations

from enum import Enum


class IssuerType(str, Enum):
    """Normalized issuer categories used by bond reference records."""

    SOVEREIGN = "SOVEREIGN"
    AGENCY = "AGENCY"
    CORPORATE = "CORPORATE"
    MUNICIPAL = "MUNICIPAL"
    SUPRANATIONAL = "SUPRANATIONAL"
    ETF = "ETF"
    OTHER = "OTHER"


__all__ = ["IssuerType"]
