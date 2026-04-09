"""Common calibrated yield-curve abstractions.

This module defines the common market-level yield-curve surface used by
concrete calibrated curve classes. The public curve object owns both the
calibrated term-structure state and the calibration metadata.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
import math

from fuggers_py.core.traits import YieldCurve as CoreYieldCurve
from fuggers_py.core.types import Compounding, Date, Yield

from .conversion import ValueConverter
from .term_structure import TermStructure


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


class CurveObjective(str, Enum):
    """Common objective families for calibrated curves."""

    L1 = "L1"
    L2 = "L2"


@dataclass(frozen=True, slots=True)
class CurveDiagnostics:
    """Common calibration diagnostics shared by calibrated curve classes."""

    objective_value: Decimal
    iterations: int
    converged: bool
    observation_count: int
    parameter_count: int


class YieldCurve(TermStructure, CoreYieldCurve):
    """Base calibrated yield curve.

    The wrapped ``TermStructure`` is the only storage of the actual fitted
    tenor-to-rate function. For yield curves, that function is the continuous
    zero rate as a function of tenor in years.
    """

    __slots__ = (
        "_date",
        "_term_structure",
        "_shape",
        "_objective",
        "_parameter_names",
        "_parameters",
        "_diagnostics",
    )

    def __init__(
        self,
        *,
        date: Date,
        term_structure: TermStructure,
        shape: object,
        objective: CurveObjective,
        parameter_names: tuple[str, ...],
        parameters: tuple[Decimal, ...],
        diagnostics: CurveDiagnostics,
    ) -> None:
        self._date = date
        self._term_structure = term_structure
        self._shape = shape
        self._objective = objective
        self._parameter_names = parameter_names
        self._parameters = tuple(_to_decimal(value) for value in parameters)
        self._diagnostics = diagnostics

    def date(self) -> Date:
        return self._date

    def value_at_tenor(self, t: float) -> float:
        return float(self._term_structure.value_at_tenor(float(t)))

    def discount_factor(self, date: Date) -> Decimal:
        return Decimal(str(self.discount_factor_at_tenor(self.date_to_tenor(date))))

    def zero_rate(self, date: Date) -> Yield:
        return Yield.new(
            _to_decimal(self.zero_rate_at_tenor(self.date_to_tenor(date), compounding=Compounding.CONTINUOUS)),
            Compounding.CONTINUOUS,
        )

    def discount_factor_at_tenor(self, t: float) -> float:
        tenor = float(t)
        if tenor <= 0.0:
            return 1.0
        zero_rate = float(self._term_structure.value_at_tenor(tenor))
        return float(math.exp(-tenor * zero_rate))

    def zero_rate_at_tenor(self, t: float, *, compounding: Compounding = Compounding.CONTINUOUS) -> float:
        tenor = float(t)
        if tenor <= 0.0:
            return 0.0
        continuous_zero_rate = float(self._term_structure.value_at_tenor(tenor))
        if compounding is Compounding.CONTINUOUS:
            return continuous_zero_rate
        return ValueConverter.convert_compounding(
            continuous_zero_rate,
            Compounding.CONTINUOUS,
            compounding,
        )

    @property
    def term_structure(self) -> TermStructure:
        return self._term_structure

    @property
    def shape(self) -> object:
        return self._shape

    @property
    def objective(self) -> CurveObjective:
        return self._objective

    @property
    def parameter_names(self) -> tuple[str, ...]:
        return self._parameter_names

    @property
    def parameters(self) -> tuple[Decimal, ...]:
        return self._parameters

    @property
    def diagnostics(self) -> CurveDiagnostics:
        return self._diagnostics

    def parameter_map(self) -> dict[str, Decimal]:
        return dict(zip(self._parameter_names, self._parameters, strict=True))


__all__ = [
    "CurveDiagnostics",
    "CurveObjective",
    "YieldCurve",
]
