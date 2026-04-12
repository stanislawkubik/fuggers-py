"""Base public abstraction for rates term structures."""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from collections.abc import Sequence
from math import log

from fuggers_py.core.types import Date
from fuggers_py.market.quotes import AnyInstrumentQuote

from ..errors import CurveConstructionError, InvalidCurveInput, TenorOutOfBounds
from .enums import ExtrapolationPolicy, RateSpace
from .kernels import CurveKernel, CurveKernelKind, KernelSpec
from .reports import CalibrationReport
from .spec import CurveSpec


class RatesTermStructure(ABC):
    """Public root for rate term structures.

    Every public rates curve carries one immutable :class:`CurveSpec`, exposes
    one rate-space meaning, and declares a finite tenor domain.
    """

    __slots__ = ("_spec",)

    def __init__(self, spec: CurveSpec) -> None:
        if not isinstance(spec, CurveSpec):
            raise InvalidCurveInput("spec must be a CurveSpec.")
        self._spec = spec

    @property
    def spec(self) -> CurveSpec:
        """Return the immutable business identity of the curve."""

        return self._spec

    @property
    def reference_date(self) -> Date:
        """Return the curve anchor date."""

        return self._spec.reference_date

    @property
    @abstractmethod
    def rate_space(self) -> RateSpace:
        """Return the meaning of ``rate_at(tenor)``."""

    @abstractmethod
    def max_t(self) -> float:
        """Return the inclusive upper tenor bound in years."""

    @abstractmethod
    def rate_at(self, tenor: float) -> float:
        """Return the rate at tenor ``tenor`` in years, expressed in ``rate_space``."""

    def _validated_max_t(self) -> float:
        max_t = float(self.max_t())
        if not math.isfinite(max_t) or max_t < 0.0:
            raise InvalidCurveInput("max_t() must return a finite value >= 0.")
        return max_t

    def _check_t(self, t: float) -> None:
        tenor = float(t)
        if not math.isfinite(tenor):
            raise InvalidCurveInput("t must be finite.")
        if tenor < 0.0:
            raise InvalidCurveInput("t must be >= 0.")
        max_t = self._validated_max_t()
        if tenor > max_t and self.spec.extrapolation_policy is ExtrapolationPolicy.ERROR:
            raise TenorOutOfBounds(t=tenor, min=0.0, max=max_t)

    def validate_rate(self, tenor: float) -> float:
        """Validate and return ``rate_at(tenor)`` on the supported domain."""

        self._check_t(tenor)
        value = float(self.rate_at(tenor))
        if not math.isfinite(value):
            raise InvalidCurveInput("rate_at(tenor) must be finite on the valid domain.")
        return value


class DiscountingCurve(RatesTermStructure, ABC):
    """Public contract for curves that can discount future cash flows."""

    @abstractmethod
    def discount_factor_at(self, tenor: float) -> float:
        """Return the discount factor at tenor ``tenor`` in years."""

    def zero_rate_at(self, tenor: float) -> float:
        """Return the continuously compounded zero rate at ``tenor``."""

        checked_tenor = float(tenor)
        if not math.isfinite(checked_tenor) or checked_tenor <= 0.0:
            raise InvalidCurveInput("tenor must be finite and > 0.")
        self._check_t(checked_tenor)
        discount_factor = float(self.discount_factor_at(checked_tenor))
        if not math.isfinite(discount_factor) or discount_factor <= 0.0:
            raise InvalidCurveInput("discount_factor_at(tenor) must be finite and > 0.")
        return -log(discount_factor) / checked_tenor

    def forward_rate_between(self, start_tenor: float, end_tenor: float) -> float:
        """Return the continuously compounded forward rate between two tenors."""

        start = float(start_tenor)
        end = float(end_tenor)
        if not math.isfinite(start) or not math.isfinite(end):
            raise InvalidCurveInput("start_tenor and end_tenor must be finite.")
        if end <= start:
            raise InvalidCurveInput("end_tenor must be greater than start_tenor.")
        self._check_t(start)
        self._check_t(end)
        discount_factor_start = float(self.discount_factor_at(start))
        discount_factor_end = float(self.discount_factor_at(end))
        if (
            not math.isfinite(discount_factor_start)
            or not math.isfinite(discount_factor_end)
            or discount_factor_start <= 0.0
            or discount_factor_end <= 0.0
        ):
            raise InvalidCurveInput("discount_factor_at(...) must be finite and > 0.")
        return log(discount_factor_start / discount_factor_end) / (end - start)


class YieldCurve(DiscountingCurve):
    """Concrete public discounting curve backed by one internal kernel.

    ``YieldCurve`` is the public object callers should hold for discounting-
    style rates curves. It always exposes a public zero-rate view through
    ``rate_at(tenor)`` and delegates the fitted rate shape to one internal
    :class:`CurveKernel`.
    """

    __slots__ = ("_kernel", "_calibration_report")

    def __init__(
        self,
        *,
        spec: CurveSpec,
        kernel: CurveKernel,
        calibration_report: CalibrationReport | None = None,
    ) -> None:
        super().__init__(spec)
        if not isinstance(kernel, CurveKernel):
            raise InvalidCurveInput("kernel must be a CurveKernel.")
        if calibration_report is not None and not isinstance(calibration_report, CalibrationReport):
            raise InvalidCurveInput("calibration_report must be a CalibrationReport or None.")
        self._kernel = kernel
        self._calibration_report = calibration_report

    @classmethod
    def fit(
        cls,
        quotes: Sequence[AnyInstrumentQuote],
        *,
        spec: CurveSpec,
        kernel_spec: KernelSpec,
    ) -> "YieldCurve":
        """Build one public yield curve from quotes and a kernel choice.

        The public entry point stays the same no matter which live fitting path
        is used. The caller chooses the internal curve family through
        ``KernelSpec``, and the implementation routes to the matching fitting
        path internally.
        """

        if not isinstance(spec, CurveSpec):
            raise InvalidCurveInput("spec must be a CurveSpec.")
        if not isinstance(kernel_spec, KernelSpec):
            raise InvalidCurveInput("kernel_spec must be a KernelSpec.")

        if kernel_spec.kind in {
            CurveKernelKind.LINEAR_ZERO,
            CurveKernelKind.LOG_LINEAR_DISCOUNT,
            CurveKernelKind.PIECEWISE_CONSTANT,
            CurveKernelKind.PIECEWISE_FLAT_FORWARD,
            CurveKernelKind.MONOTONE_CONVEX,
            CurveKernelKind.CUBIC_SPLINE_ZERO,
            CurveKernelKind.CUBIC_SPLINE,
        }:
            from .calibrators import BootstrapCalibrator

            calibrator = BootstrapCalibrator()
        elif kernel_spec.kind in {
            CurveKernelKind.NELSON_SIEGEL,
            CurveKernelKind.SVENSSON,
            CurveKernelKind.EXPONENTIAL_SPLINE,
        }:
            from .calibrators import ParametricCalibrator

            calibrator = ParametricCalibrator()
        else:
            raise CurveConstructionError(f"no quote-driven fitting path exists for kernel kind {kernel_spec.kind.name}.")

        kernel, report = calibrator.fit(quotes, spec=spec, kernel_spec=kernel_spec)
        return cls(spec=spec, kernel=kernel, calibration_report=report)

    @property
    def rate_space(self) -> RateSpace:
        """Return the public rate-space view of the yield curve.

        In the simplified ontology, every public ``YieldCurve`` exposes a
        zero-rate view even if the internal kernel stores its math differently.
        """

        return RateSpace.ZERO

    def max_t(self) -> float:
        """Return the inclusive upper tenor bound delegated from the kernel."""

        max_t = float(self._kernel.max_t())
        if not math.isfinite(max_t) or max_t < 0.0:
            raise InvalidCurveInput("kernel.max_t() must return a finite value >= 0.")
        return max_t

    def rate_at(self, tenor: float) -> float:
        """Return the public zero-rate view implied by the kernel."""

        checked_tenor = float(tenor)
        if not math.isfinite(checked_tenor) or checked_tenor <= 0.0:
            raise InvalidCurveInput("tenor must be finite and > 0.")
        self._check_t(checked_tenor)
        rate = float(self._kernel.rate_at(checked_tenor))
        if not math.isfinite(rate):
            raise InvalidCurveInput("kernel.rate_at(tenor) must be finite.")
        return rate

    def discount_factor_at(self, tenor: float) -> float:
        """Return the discount factor implied by the kernel at ``tenor``."""

        checked_tenor = float(tenor)
        self._check_t(checked_tenor)
        discount_factor = float(self._kernel.discount_factor_at(checked_tenor))
        if not math.isfinite(discount_factor) or discount_factor <= 0.0:
            raise InvalidCurveInput("kernel.discount_factor_at(tenor) must be finite and > 0.")
        return discount_factor

    @property
    def calibration_report(self) -> CalibrationReport | None:
        """Return the optional calibration report attached to this curve."""

        return self._calibration_report


class RelativeRateCurve(RatesTermStructure):
    """Public root for rate curves that are not standalone discounting curves."""


__all__ = [
    "DiscountingCurve",
    "RatesTermStructure",
    "RelativeRateCurve",
    "YieldCurve",
]
