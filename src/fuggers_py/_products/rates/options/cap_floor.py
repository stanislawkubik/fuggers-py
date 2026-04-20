"""Cap/floor product definitions.

Caps and floors are parameterized by a floating leg, a strike in raw decimal
rate space, and the effective/maturity dates that define the optionlet grid.
The product object does not infer a schedule on its own; it reuses the
underlying floating-leg accrual periods.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import ClassVar

from fuggers_py._core import OptionType
from fuggers_py._core.types import Date
from fuggers_py._core.ids import InstrumentId
from fuggers_py._products.instruments import KindedInstrumentMixin

from ..common import FloatingLegSpec
from ._common import _to_decimal


class CapFloorType(str, Enum):
    """Cap or floor product type."""

    CAP = "CAP"
    FLOOR = "FLOOR"

    @classmethod
    def parse(cls, value: "CapFloorType" | str) -> "CapFloorType":
        """Parse a cap/floor label or strip-style alias."""
        if isinstance(value, cls):
            return value
        normalized = value.strip().upper()
        aliases = {
            "CAP": cls.CAP,
            "CAPLET_STRIP": cls.CAP,
            "FLOOR": cls.FLOOR,
            "FLOORLET_STRIP": cls.FLOOR,
        }
        try:
            return aliases[normalized]
        except KeyError as exc:
            raise ValueError(f"Unsupported cap/floor type: {value!r}.") from exc

    def option_type(self) -> OptionType:
        """Return the corresponding call/put option type."""
        return OptionType.CALL if self is CapFloorType.CAP else OptionType.PUT


@dataclass(frozen=True, slots=True)
class CapFloor(KindedInstrumentMixin):
    """Interest-rate cap or floor keyed to a floating leg specification.

    Parameters
    ----------
    effective_date, maturity_date:
        Optionlet window.
    floating_leg:
        Floating-leg specification the cap or floor is written on.
    strike:
        Strike rate as a raw decimal.
    cap_floor_type:
        Whether the contract is a cap or a floor.
    instrument_id:
        Optional stable identifier for the contract.
    """

    KIND: ClassVar[str] = "rates.option.cap_floor"

    effective_date: Date
    maturity_date: Date
    floating_leg: FloatingLegSpec
    strike: Decimal
    cap_floor_type: CapFloorType | str = CapFloorType.CAP
    instrument_id: InstrumentId | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "strike", _to_decimal(self.strike))
        object.__setattr__(self, "cap_floor_type", CapFloorType.parse(self.cap_floor_type))
        if self.instrument_id is not None:
            object.__setattr__(self, "instrument_id", InstrumentId.parse(self.instrument_id))
        if self.strike < Decimal(0):
            raise ValueError("CapFloor strike must be non-negative.")
        if self.maturity_date <= self.effective_date:
            raise ValueError("CapFloor requires maturity_date after effective_date.")

    def currency(self):
        """Return the currency of the floating leg."""
        return self.floating_leg.currency

    def option_type(self) -> OptionType:
        """Return the cap/floor as a call/put option type."""
        return self.cap_floor_type.option_type()

    def optionlet_periods(self):
        """Return the optionlet accrual periods for the cap/floor."""
        return self.floating_leg.accrual_periods(self.effective_date, self.maturity_date)


__all__ = ["CapFloor", "CapFloorType"]
