"""Parametric curve fitting for zero-rate and instrument data.

The fitter estimates Nelson-Siegel or Svensson zero curves from either raw
zero-rate observations or calibration instruments quoted in raw decimal form.
Observed rates can be supplied in a non-continuous compounding convention and
are converted internally to continuous zero rates for the objective function.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable

import numpy as np
from numpy.typing import ArrayLike, NDArray

from fuggers_py.core.daycounts import DayCountConvention
from fuggers_py.core.types import Compounding, Date
from fuggers_py.math.optimization import OptimizationConfig, OptimizationResult, levenberg_marquardt

from ..conversion import ValueConverter
from ..errors import InvalidCurveInput
from ..term_structure import TermStructure
from ..wrappers import RateCurve
from .instruments import CalibrationInstrument, InstrumentSet


def _to_float_array(values: ArrayLike, *, name: str) -> NDArray[np.float64]:
    arr = np.asarray(values, dtype=float)
    if arr.ndim != 1:
        raise InvalidCurveInput(f"{name} must be 1D; got shape {arr.shape}.")
    if arr.size == 0:
        raise InvalidCurveInput(f"{name} must be non-empty.")
    if not np.all(np.isfinite(arr)):
        raise InvalidCurveInput(f"{name} must be finite.")
    return arr.astype(float, copy=False)


class ParametricModel(str, Enum):
    """Supported parametric zero-curve families."""

    NELSON_SIEGEL = "NELSON_SIEGEL"
    SVENSSON = "SVENSSON"


@dataclass(frozen=True, slots=True)
class FitterConfig:
    """Configuration for global parametric curve fitting.

    Parameters
    ----------
    model:
        Parametric model family to fit.
    compounding:
        Compounding convention used by observed zero-rate inputs.
    day_count:
        Day-count convention associated with the output curve.
    optimization:
        Optimization controls passed to the nonlinear solver.
    initial_parameters:
        Optional initial parameter vector in model order.
    """

    model: ParametricModel = ParametricModel.NELSON_SIEGEL
    compounding: Compounding = Compounding.CONTINUOUS
    day_count: DayCountConvention = DayCountConvention.ACT_365_FIXED
    optimization: OptimizationConfig = OptimizationConfig()
    initial_parameters: ArrayLike | None = None


@dataclass(frozen=True, slots=True)
class GlobalFitResult:
    """Result of a global parametric fit."""

    curve: RateCurve
    parameters: NDArray[np.float64]
    objective_value: float
    iterations: int
    converged: bool


def _nelson_siegel_zero(t: float, params: NDArray[np.float64]) -> float:
    beta0, beta1, beta2, tau = params
    if tau <= 0.0:
        return float(beta0)
    if t <= 0.0:
        return float(beta0 + beta1)
    x = t / tau
    exp_x = np.exp(-x)
    factor = (1.0 - exp_x) / x
    return float(beta0 + beta1 * factor + beta2 * (factor - exp_x))


def _svensson_zero(t: float, params: NDArray[np.float64]) -> float:
    beta0, beta1, beta2, beta3, tau1, tau2 = params
    if tau1 <= 0.0 or tau2 <= 0.0:
        return float(beta0)
    if t <= 0.0:
        return float(beta0 + beta1)
    x1 = t / tau1
    x2 = t / tau2
    exp1 = np.exp(-x1)
    exp2 = np.exp(-x2)
    factor1 = (1.0 - exp1) / x1
    factor2 = (1.0 - exp2) / x2
    return float(
        beta0
        + beta1 * factor1
        + beta2 * (factor1 - exp1)
        + beta3 * (factor2 - exp2)
    )


@dataclass(frozen=True, slots=True)
class ParametricZeroCurve(TermStructure):
    """Parametric zero-rate curve with explicit compounding semantics."""

    _reference_date: Date
    parameters: NDArray[np.float64]
    model: ParametricModel
    compounding: Compounding
    day_count: DayCountConvention
    max_t: float

    def date(self) -> Date:  # type: ignore[override]
        """Return the curve date."""
        return self._reference_date

    def value_at_tenor(self, t: float) -> float:
        """Return the model zero rate at tenor ``t`` in the configured compounding."""
        tau = float(t)
        if self.model is ParametricModel.NELSON_SIEGEL:
            r_cont = _nelson_siegel_zero(tau, self.parameters)
        else:
            r_cont = _svensson_zero(tau, self.parameters)
        if self.compounding is Compounding.CONTINUOUS:
            return float(r_cont)
        return ValueConverter.convert_compounding(r_cont, Compounding.CONTINUOUS, self.compounding)


class GlobalFitter:
    """Fit a parametric zero curve against zero rates or calibration instruments."""

    def __init__(self, reference_date: Date, *, config: FitterConfig = FitterConfig()) -> None:
        self.reference_date = reference_date
        self.config = config

    def _parameter_count(self) -> int:
        return 4 if self.config.model is ParametricModel.NELSON_SIEGEL else 6

    def _sanitize_initial(self, initial: NDArray[np.float64]) -> NDArray[np.float64]:
        if initial.size != self._parameter_count():
            raise InvalidCurveInput(
                f"initial_parameters has length {initial.size}, expected {self._parameter_count()} for {self.config.model.value}."
            )
        return initial.astype(float, copy=True)

    def _encode_parameters(self, parameters: NDArray[np.float64]) -> NDArray[np.float64]:
        encoded = self._sanitize_initial(parameters)
        if self.config.model is ParametricModel.NELSON_SIEGEL:
            encoded[3] = np.log(max(float(encoded[3]), 1e-6))
            return encoded

        tau1 = max(float(encoded[4]), 1e-6)
        tau2 = max(float(encoded[5]), tau1 + 1e-6)
        encoded[4] = np.log(tau1)
        encoded[5] = np.log(tau2 - tau1)
        return encoded

    def _decode_parameters(self, encoded: NDArray[np.float64]) -> NDArray[np.float64]:
        decoded = self._sanitize_initial(encoded)
        if self.config.model is ParametricModel.NELSON_SIEGEL:
            decoded[3] = float(np.exp(np.clip(decoded[3], -20.0, 20.0)))
            return decoded

        tau1 = float(np.exp(np.clip(decoded[4], -20.0, 20.0)))
        tau2 = tau1 + float(np.exp(np.clip(decoded[5], -20.0, 20.0)))
        decoded[4] = tau1
        decoded[5] = tau2
        return decoded

    def _default_initial(self, tenors: NDArray[np.float64], zero_rates: NDArray[np.float64]) -> NDArray[np.float64]:
        if self.config.model is ParametricModel.NELSON_SIEGEL:
            beta0 = float(zero_rates[-1])
            beta1 = float(zero_rates[0] - zero_rates[-1])
            beta2 = 0.0
            tau = max(float(tenors.mean()), 1.0)
            return np.array([beta0, beta1, beta2, tau], dtype=float)

        beta0 = float(zero_rates[-1])
        beta1 = float(zero_rates[0] - zero_rates[-1])
        beta2 = 0.0
        beta3 = 0.0
        tau1 = max(float(tenors.mean()), 1.0)
        tau2 = max(float(tenors.max()), 2.0)
        return np.array([beta0, beta1, beta2, beta3, tau1, tau2], dtype=float)

    def _fit(self, residual_fn, initial_parameters: NDArray[np.float64]) -> OptimizationResult:
        encoded_initial = self._encode_parameters(initial_parameters)
        opt = levenberg_marquardt(residual_fn, encoded_initial, config=self.config.optimization)
        return OptimizationResult(
            parameters=self._decode_parameters(opt.parameters),
            objective_value=opt.objective_value,
            iterations=opt.iterations,
            converged=opt.converged,
        )

    def fit_zero_rates(self, tenors: ArrayLike, zero_rates: ArrayLike) -> GlobalFitResult:
        """Fit the configured parametric curve to observed zero rates.

        Parameters
        ----------
        tenors:
            Positive year-fraction tenors of the observed zero rates.
        zero_rates:
            Raw decimal observed zero rates in the compounding convention
            specified by :attr:`FitterConfig.compounding`.
        """
        t = _to_float_array(tenors, name="tenors")
        z = _to_float_array(zero_rates, name="zero_rates")
        if t.size != z.size:
            raise InvalidCurveInput("tenors and zero_rates must have the same length.")
        if np.any(t <= 0.0):
            raise InvalidCurveInput("tenors must be strictly positive for parametric fit.")
        order = np.argsort(t)
        t = t[order]
        z = z[order]

        if self.config.compounding is Compounding.CONTINUOUS:
            observed_zero_rates = z
        else:
            observed_zero_rates = np.array(
                [
                    ValueConverter.convert_compounding(rate, self.config.compounding, Compounding.CONTINUOUS)
                    for rate in z
                ],
                dtype=float,
            )

        initial = (
            self._sanitize_initial(_to_float_array(self.config.initial_parameters, name="initial_parameters"))
            if self.config.initial_parameters is not None
            else self._default_initial(t, observed_zero_rates)
        )

        def residuals(raw_params: NDArray[np.float64]) -> NDArray[np.float64]:
            params = self._decode_parameters(raw_params)
            if self.config.model is ParametricModel.NELSON_SIEGEL:
                modeled = np.array([_nelson_siegel_zero(ti, params) for ti in t], dtype=float)
            else:
                modeled = np.array([_svensson_zero(ti, params) for ti in t], dtype=float)
            return modeled - observed_zero_rates

        opt = self._fit(residuals, initial)
        max_t = float(t.max())
        curve = RateCurve(
            ParametricZeroCurve(
                _reference_date=self.reference_date,
                parameters=opt.parameters,
                model=self.config.model,
                compounding=self.config.compounding,
                day_count=self.config.day_count,
                max_t=max_t,
            )
        )
        return GlobalFitResult(
            curve=curve,
            parameters=opt.parameters,
            objective_value=opt.objective_value,
            iterations=opt.iterations,
            converged=opt.converged,
        )

    def fit_instruments(self, instruments: InstrumentSet) -> GlobalFitResult:
        """Fit the configured parametric curve to instrument par quotes."""
        insts = instruments.instruments
        if not insts:
            raise InvalidCurveInput("Instrument set must be non-empty for parametric fit.")
        insts = tuple(sorted(insts, key=lambda inst: inst.maturity_date()))

        maturities = np.array(
            [float(self.reference_date.days_between(inst.maturity_date())) / 365.0 for inst in insts],
            dtype=float,
        )
        quotes = np.array([float(inst.quote) for inst in insts], dtype=float)

        initial = (
            self._sanitize_initial(_to_float_array(self.config.initial_parameters, name="initial_parameters"))
            if self.config.initial_parameters is not None
            else self._default_initial(maturities, quotes)
        )

        def residuals(raw_params: NDArray[np.float64]) -> NDArray[np.float64]:
            params = self._decode_parameters(raw_params)
            max_t = float(maturities.max())
            curve = RateCurve(
                ParametricZeroCurve(
                    _reference_date=self.reference_date,
                    parameters=params,
                    model=self.config.model,
                    compounding=self.config.compounding,
                    day_count=self.config.day_count,
                    max_t=max_t,
                )
            )
            modeled = np.array([float(inst.par_rate(curve)) for inst in insts], dtype=float)
            return modeled - quotes

        opt = self._fit(residuals, initial)
        max_t = float(maturities.max())
        curve = RateCurve(
            ParametricZeroCurve(
                _reference_date=self.reference_date,
                parameters=opt.parameters,
                model=self.config.model,
                compounding=self.config.compounding,
                day_count=self.config.day_count,
                max_t=max_t,
            )
        )
        return GlobalFitResult(
            curve=curve,
            parameters=opt.parameters,
            objective_value=opt.objective_value,
            iterations=opt.iterations,
            converged=opt.converged,
        )


__all__ = [
    "ParametricModel",
    "FitterConfig",
    "GlobalFitResult",
    "GlobalFitter",
]
