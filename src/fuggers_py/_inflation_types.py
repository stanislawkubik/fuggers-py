"""Internal inflation enums shared across reference and market layers."""

from __future__ import annotations

from enum import Enum


class InflationInterpolation(str, Enum):
    """Interpolation convention for inflation fixings."""

    MONTHLY = "MONTHLY"
    LINEAR = "LINEAR"
    FLAT = "FLAT"


__all__ = ["InflationInterpolation"]
