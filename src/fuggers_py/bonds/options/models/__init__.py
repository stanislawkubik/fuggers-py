"""Short-rate models for bond options."""

from __future__ import annotations

from ..errors import ModelError
from .base import ShortRateModel
from .hull_white import HullWhiteModel

HullWhite = HullWhiteModel

__all__ = ["HullWhite", "HullWhiteModel", "ModelError", "ShortRateModel"]
