"""Sequential curve bootstrapper.

The bootstrapper inserts an anchor pillar at tenor zero, then solves each
instrument sequentially against the growing discrete curve. Calibration can be
performed on discount factors or on zero rates expressed in raw decimal form.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

import numpy as np

from fuggers_py.core.daycounts import DayCountConvention
from fuggers_py.core.types import Compounding, Date
from fuggers_py.math import SolverConfig, brent
from fuggers_py.math.errors import ConvergenceFailed, InvalidBracket

from ..discrete import DiscreteCurve, ExtrapolationMethod, InterpolationMethod
from ..errors import CurveConstructionError, InvalidCurveInput
from ..value_type import ValueType, ValueTypeKind
from ..wrappers import RateCurve
from .instruments import CalibrationInstrument, InstrumentSet


def _to_decimal(value: object, *, field_name: str) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _float(value: object) -> float:
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def _tenor_years(reference_date: Date, date: Date, *, day_count: DayCountConvention) -> float:
    dc = day_count.to_day_count()
    return float(dc.year_fraction(reference_date, date))


@dataclass(frozen=True, slots=True)
class CalibrationInstrumentResult:
    """Per-instrument calibration quote and residual."""

    instrument: CalibrationInstrument
    market_quote: Decimal
    model_quote: Decimal
    residual: Decimal


@dataclass(frozen=True, slots=True)
class CalibrationResult:
    """Result of a sequential or piecewise curve bootstrap."""

    curve: RateCurve
    instrument_results: list[CalibrationInstrumentResult]

    @property
    def max_abs_error(self) -> Decimal:
        """Return the maximum absolute quote residual."""
        if not self.instrument_results:
            return Decimal(0)
        return max(abs(item.residual) for item in self.instrument_results)


@dataclass(frozen=True, slots=True)
class SequentialBootstrapper:
    """Sequential bootstrapper for raw-decimal discount-factor or zero quotes."""

    reference_date: Date
    instruments: InstrumentSet
    value_type_kind: ValueTypeKind = ValueTypeKind.DISCOUNT_FACTOR
    interpolation_method: InterpolationMethod | None = None
    extrapolation_method: ExtrapolationMethod = ExtrapolationMethod.FLAT
    curve_day_count: DayCountConvention = DayCountConvention.ACT_365_FIXED
    zero_compounding: Compounding = Compounding.CONTINUOUS
    solver_config: SolverConfig = SolverConfig(tolerance=1e-12, max_iterations=200)

    def _value_type(self) -> ValueType:
        if self.value_type_kind is ValueTypeKind.DISCOUNT_FACTOR:
            return ValueType.discount_factor()
        if self.value_type_kind is ValueTypeKind.ZERO_RATE:
            return ValueType.zero_rate(self.zero_compounding, self.curve_day_count)
        raise InvalidCurveInput(f"Unsupported calibration value type: {self.value_type_kind}.")

    def _default_interpolation(self) -> InterpolationMethod:
        if self.value_type_kind is ValueTypeKind.DISCOUNT_FACTOR:
            return InterpolationMethod.LOG_LINEAR
        return InterpolationMethod.LINEAR

    def _anchor_pillar(self) -> tuple[float, float]:
        if self.value_type_kind is ValueTypeKind.DISCOUNT_FACTOR:
            return 0.0, 1.0
        return 0.0, 0.0

    def _build_curve(self, tenors: Iterable[float], values: Iterable[float]) -> RateCurve:
        t_list = list(tenors)
        v_list = list(values)
        if not t_list:
            raise CurveConstructionError("Cannot build a curve with zero pillars.")

        # Ensure anchor pillar at t=0 for numerical stability / required length.
        anchor_t, anchor_v = self._anchor_pillar()
        if t_list[0] > 0.0:
            t_list = [anchor_t] + t_list
            v_list = [anchor_v] + v_list
        elif t_list[0] < 0.0:
            raise InvalidCurveInput("Curve pillars must be non-negative in tenor.")
        elif abs(t_list[0]) < 1e-12 and len(t_list) == 1:
            # Need at least 2 pillars; append a tiny stub for interpolation.
            t_list = [anchor_t, max(1e-6, t_list[0] + 1e-6)]
            v_list = [anchor_v, v_list[0]]

        interpolation = self.interpolation_method or self._default_interpolation()
        curve = DiscreteCurve(
            self.reference_date,
            t_list,
            v_list,
            value_type=self._value_type(),
            interpolation_method=interpolation,
            extrapolation_method=self.extrapolation_method,
        )
        return RateCurve(curve)

    def _residual_fn(
        self,
        instrument: CalibrationInstrument,
        tenors: list[float],
        values: list[float],
        tenor: float,
    ):
        quote = _float(instrument.quote)

        def residual(x: float) -> float:
            curve = self._build_curve(tenors + [float(tenor)], values + [float(x)])
            model = _float(instrument.par_rate(curve))
            return model - quote

        return residual

    def _find_bracket(self, residual, grid: list[float]) -> tuple[float, float] | None:
        prev_x = None
        prev_val = None
        for x in grid:
            try:
                val = residual(x)
            except Exception:
                prev_x = None
                prev_val = None
                continue
            if not np.isfinite(val):
                prev_x = None
                prev_val = None
                continue
            if val == 0.0:
                return x, x
            if prev_x is not None and prev_val is not None and val * prev_val < 0:
                return prev_x, x
            prev_x, prev_val = x, val
        return None

    def _solve_for_pillar(self, residual) -> float:
        if self.value_type_kind is ValueTypeKind.DISCOUNT_FACTOR:
            grid = [1e-6, 0.01, 0.1, 0.5, 0.9, 1.1, 1.5, 2.0]
        else:
            grid = [-0.05, -0.01, 0.0, 0.01, 0.03, 0.05, 0.1, 0.2, 0.5]

        bracket = self._find_bracket(residual, grid)
        if bracket is None:
            raise CurveConstructionError("Unable to bracket bootstrap root for calibration instrument.")

        a, b = bracket
        if a == b:
            return float(a)
        try:
            result = brent(residual, float(a), float(b), config=self.solver_config)
        except (InvalidBracket, ConvergenceFailed) as exc:
            raise CurveConstructionError("Bootstrap root solve failed to converge.") from exc
        return float(result.root)

    def bootstrap(self) -> CalibrationResult:
        """Bootstrap a discrete rate curve from the configured instruments.

        Returns
        -------
        CalibrationResult
            Calibrated curve and per-instrument residuals where the residual is
            ``model_quote - market_quote`` in raw decimal quote units.
        """
        if not self.instruments.instruments:
            raise InvalidCurveInput("SequentialBootstrapper requires a non-empty InstrumentSet.")

        tenors: list[float] = []
        values: list[float] = []

        for instrument in self.instruments.instruments:
            maturity = instrument.maturity_date()
            tenor = _tenor_years(self.reference_date, maturity, day_count=self.curve_day_count)
            if tenor <= 0.0:
                raise InvalidCurveInput("Instrument maturity must be after reference date.")

            residual = self._residual_fn(instrument, tenors, values, tenor)
            solved = self._solve_for_pillar(residual)
            tenors.append(float(tenor))
            values.append(float(solved))

        curve = self._build_curve(tenors, values)
        results: list[CalibrationInstrumentResult] = []
        for instrument in self.instruments.instruments:
            model = _to_decimal(instrument.par_rate(curve), field_name="model_quote")
            market = _to_decimal(instrument.quote, field_name="market_quote")
            residual = model - market
            results.append(
                CalibrationInstrumentResult(
                    instrument=instrument,
                    market_quote=market,
                    model_quote=model,
                    residual=residual,
                )
            )

        return CalibrationResult(curve=curve, instrument_results=results)


__all__ = [
    "CalibrationInstrumentResult",
    "CalibrationResult",
    "SequentialBootstrapper",
]
