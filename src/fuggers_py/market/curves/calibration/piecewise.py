"""Thin wrapper around the sequential bootstrapper.

The piecewise bootstrap path uses the same sequential solve but keeps a
separate entry point for callers that prefer a more explicit bootstrap name.
"""

from __future__ import annotations

from dataclasses import dataclass

from fuggers_py.core.daycounts import DayCountConvention
from fuggers_py.core.types import Compounding, Date
from fuggers_py.math import SolverConfig

from ..discrete import ExtrapolationMethod, InterpolationMethod
from ..value_type import ValueTypeKind
from .instruments import InstrumentSet
from .sequential import CalibrationResult, SequentialBootstrapper


@dataclass(frozen=True, slots=True)
class PiecewiseBootstrapper:
    """Alias-style wrapper around :class:`SequentialBootstrapper`."""

    reference_date: Date
    instruments: InstrumentSet
    value_type_kind: ValueTypeKind = ValueTypeKind.DISCOUNT_FACTOR
    interpolation_method: InterpolationMethod | None = None
    extrapolation_method: ExtrapolationMethod = ExtrapolationMethod.FLAT
    curve_day_count: DayCountConvention = DayCountConvention.ACT_365_FIXED
    zero_compounding: Compounding = Compounding.CONTINUOUS
    solver_config: SolverConfig = SolverConfig(tolerance=1e-12, max_iterations=200)

    def bootstrap(self) -> CalibrationResult:
        """Delegate to :class:`SequentialBootstrapper` without changing behavior."""
        bootstrapper = SequentialBootstrapper(
            reference_date=self.reference_date,
            instruments=self.instruments,
            value_type_kind=self.value_type_kind,
            interpolation_method=self.interpolation_method,
            extrapolation_method=self.extrapolation_method,
            curve_day_count=self.curve_day_count,
            zero_compounding=self.zero_compounding,
            solver_config=self.solver_config,
        )
        return bootstrapper.bootstrap()


__all__ = ["PiecewiseBootstrapper"]
