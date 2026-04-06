"""Rates options product definitions.

The package exposes rate option wrappers built on top of the swap, cap/floor,
and futures underlying contract objects.
"""

from __future__ import annotations

from fuggers_py.products.instruments import HasExpiry, HasOptionType, HasUnderlyingInstrument

from ._common import OptionType
from .cap_floor import CapFloor, CapFloorType
from .futures_option import FuturesOption
from .swaption import Swaption

__all__ = [
    "CapFloor",
    "CapFloorType",
    "FuturesOption",
    "HasExpiry",
    "HasOptionType",
    "HasUnderlyingInstrument",
    "OptionType",
    "Swaption",
]
