"""ETF holding records for portfolio workflows."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from fuggers_py._core.ids import InstrumentId


def _to_decimal(value: object | None) -> Decimal | None:
    if value is None or isinstance(value, Decimal):
        return value
    return Decimal(str(value))


@dataclass(frozen=True, slots=True)
class EtfHolding:
    """ETF holding record with either quantity or weight populated."""

    instrument_id: InstrumentId
    quantity: Decimal | None = None
    weight: Decimal | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "instrument_id", InstrumentId.parse(self.instrument_id))
        quantity = _to_decimal(self.quantity)
        weight = _to_decimal(self.weight)
        if quantity is None and weight is None:
            raise ValueError("EtfHolding requires either quantity or weight.")
        object.__setattr__(self, "quantity", quantity)
        object.__setattr__(self, "weight", weight)


__all__ = ["EtfHolding"]
