"""Typed observation records for internal curve calibration."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum, auto

from ...errors import InvalidCurveInput


class BootstrapObservationKind(Enum):
    """Meaning of one bootstrap observation value."""

    ZERO_RATE = auto()
    DISCOUNT_FACTOR = auto()


@dataclass(frozen=True, slots=True)
class BootstrapObservation:
    """One node-style observation used by the bootstrap calibrator."""

    instrument_id: str
    tenor: float
    value: float
    kind: BootstrapObservationKind
    weight: float = 1.0

    def __post_init__(self) -> None:
        if not isinstance(self.instrument_id, str) or not self.instrument_id.strip():
            raise InvalidCurveInput("instrument_id must be a non-empty string.")
        object.__setattr__(self, "instrument_id", self.instrument_id.strip())

        tenor = float(self.tenor)
        if not math.isfinite(tenor) or tenor < 0.0:
            raise InvalidCurveInput("tenor must be finite and >= 0.")
        object.__setattr__(self, "tenor", tenor)

        value = float(self.value)
        if not math.isfinite(value):
            raise InvalidCurveInput("value must be finite.")
        object.__setattr__(self, "value", value)

        if not isinstance(self.kind, BootstrapObservationKind):
            raise InvalidCurveInput("kind must be a BootstrapObservationKind.")

        weight = float(self.weight)
        if not math.isfinite(weight) or weight <= 0.0:
            raise InvalidCurveInput("weight must be finite and > 0.")
        object.__setattr__(self, "weight", weight)

        if self.kind is BootstrapObservationKind.DISCOUNT_FACTOR and value <= 0.0:
            raise InvalidCurveInput("discount-factor observations must be > 0.")
        if tenor == 0.0 and self.kind is BootstrapObservationKind.DISCOUNT_FACTOR and abs(value - 1.0) > 1e-12:
            raise InvalidCurveInput("discount factor at tenor 0 must equal 1.0.")
        if tenor == 0.0 and self.kind is BootstrapObservationKind.ZERO_RATE and abs(value) > 1e-12:
            raise InvalidCurveInput("zero rate at tenor 0 must equal 0.0.")


__all__ = [
    "BootstrapObservation",
    "BootstrapObservationKind",
]
