"""Base public abstraction for rates term structures."""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from decimal import Decimal
from math import log

from fuggers_py._core import Tenor
from fuggers_py._core.types import Date

from .calibrators.base import CalibrationSpec
from .errors import CurveConstructionError, InvalidCurveInput, TenorOutOfBounds
from .kernels import KernelSpec
from .kernels.base import CurveKernel
from .reports import CalibrationReport
from .spec import CurveSpec


class RatesTermStructure(ABC):
    """Public root for rate term structures.

    Every public rates curve carries one immutable :class:`CurveSpec` and
    declares a finite tenor domain.
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

    @abstractmethod
    def max_t(self) -> float:
        """Return the inclusive upper tenor bound in years."""

    @abstractmethod
    def rate_at(self, tenor: float) -> float:
        """Return the rate at tenor ``tenor`` in years."""

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
        if tenor > max_t and self.spec.extrapolation_policy == "error":
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

    def shifted(self, *, shift: float) -> "DiscountingCurve":
        """Return this curve with all zero rates shifted by one amount."""

        from .movements import _shifted_curve

        return _shifted_curve(self, shift=shift)

    def bumped(
        self,
        *,
        bumps: Mapping[Tenor | float | int | Decimal, float],
        tenor_grid: Sequence[Tenor | float | int | Decimal] | None = None,
    ) -> "DiscountingCurve":
        """Return this curve with one or more tenor-specific zero-rate bumps."""

        from .movements import _bumped_curve

        return _bumped_curve(self, bumps=bumps, tenor_grid=tenor_grid)


class YieldCurve(DiscountingCurve):
    """Concrete public discounting curve backed by one internal kernel.

    ``YieldCurve`` is the public object callers should hold for discounting-
    style rates curves. It always exposes a public zero-rate view through
    ``rate_at(tenor)`` and delegates the fitted rate shape to one internal
    :class:`CurveKernel`.

    Most callers should build it through ``YieldCurve.fit(...)``. Direct
    construction from ``spec=...`` plus ``kernel=...`` is the advanced path
    for code that already has a built kernel.
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
        quotes: Sequence[object],
        *,
        spec: CurveSpec,
        kernel: str | KernelSpec = "linear_zero",
        method: str | CalibrationSpec = "bootstrap",
        bond_target: str = "dirty_price",
        regressors: Sequence[str] = (),
        kernel_params: Mapping[str, object] | None = None,
    ) -> "YieldCurve":
        """Build one public yield curve from quotes and simple fit settings."""

        if not isinstance(spec, CurveSpec):
            raise InvalidCurveInput("spec must be a CurveSpec.")
        if isinstance(kernel, KernelSpec):
            if kernel_params is not None:
                raise InvalidCurveInput("kernel_params cannot be used when kernel is a KernelSpec.")
            kernel_spec = kernel
        else:
            kernel_spec = KernelSpec(kind=kernel, parameters=kernel_params or {})

        if isinstance(method, CalibrationSpec):
            calibration_spec = method
        else:
            calibration_spec = CalibrationSpec(
                method=method,
                bond_target=bond_target,
                regressors=tuple(regressors),
            )

        if calibration_spec.method == "bootstrap":
            from .calibrators.bootstrap import BootstrapCalibrator

            calibrator = BootstrapCalibrator(calibration_spec=calibration_spec)
        elif calibration_spec.method == "global_fit":
            from .calibrators.global_fit import GlobalFitCalibrator

            calibrator = GlobalFitCalibrator(calibration_spec=calibration_spec)
        else:
            raise CurveConstructionError(
                f"no quote-driven fitting path exists for calibration method {calibration_spec.method}."
            )

        kernel, report = calibrator.fit(
            quotes,
            spec=spec,
            kernel_spec=kernel_spec,
        )
        return cls(spec=spec, kernel=kernel, calibration_report=report)

    def max_t(self) -> float:
        """Return the inclusive upper tenor bound delegated from the kernel."""

        max_t = float(self._kernel.max_t())
        if not math.isfinite(max_t) or max_t < 0.0:
            raise InvalidCurveInput("kernel.max_t() must return a finite value >= 0.")
        return max_t

    def _is_above_max_t(self, tenor: float) -> bool:
        return float(tenor) > self.max_t()

    @staticmethod
    def _finite_rate(value: float, *, message: str) -> float:
        rate = float(value)
        if not math.isfinite(rate):
            raise InvalidCurveInput(message)
        return rate

    @staticmethod
    def _positive_discount_factor(value: float, *, message: str) -> float:
        discount_factor = float(value)
        if not math.isfinite(discount_factor) or discount_factor <= 0.0:
            raise InvalidCurveInput(message)
        return discount_factor

    def _terminal_zero_rate(self) -> float:
        return self._finite_rate(
            self._kernel.terminal_zero_rate(),
            message="kernel.terminal_zero_rate() must be finite.",
        )

    def _extrapolated_discount_factor_at(self, tenor: float) -> float:
        policy = self.spec.extrapolation_policy
        checked_tenor = float(tenor)
        if policy == "hold_last_zero_rate":
            discount_factor = math.exp(-self._terminal_zero_rate() * checked_tenor)
        elif policy == "hold_last_native_rate":
            discount_factor = self._kernel.terminal_native_discount_factor_at(checked_tenor)
        elif policy == "hold_last_forward_rate":
            discount_factor = self._kernel.terminal_forward_discount_factor_at(checked_tenor)
        else:
            raise TenorOutOfBounds(t=checked_tenor, min=0.0, max=self.max_t())
        return self._positive_discount_factor(
            discount_factor,
            message=f"kernel {policy} discount factor must be finite and > 0.",
        )

    def _extrapolated_rate_at(self, tenor: float) -> float:
        checked_tenor = float(tenor)
        if self.spec.extrapolation_policy == "hold_last_zero_rate":
            return self._terminal_zero_rate()
        discount_factor = self._extrapolated_discount_factor_at(checked_tenor)
        return self._finite_rate(
            -log(discount_factor) / checked_tenor,
            message="extrapolated zero rate must be finite.",
        )

    def rate_at(self, tenor: float) -> float:
        """Return the public zero-rate view implied by the kernel."""

        checked_tenor = float(tenor)
        if not math.isfinite(checked_tenor) or checked_tenor <= 0.0:
            raise InvalidCurveInput("tenor must be finite and > 0.")
        self._check_t(checked_tenor)
        if self._is_above_max_t(checked_tenor):
            return self._extrapolated_rate_at(checked_tenor)
        rate = float(self._kernel.rate_at(checked_tenor))
        if not math.isfinite(rate):
            raise InvalidCurveInput("kernel.rate_at(tenor) must be finite.")
        return rate

    def discount_factor_at(self, tenor: float) -> float:
        """Return the discount factor implied by the kernel at ``tenor``."""

        checked_tenor = float(tenor)
        self._check_t(checked_tenor)
        if self._is_above_max_t(checked_tenor):
            return self._extrapolated_discount_factor_at(checked_tenor)
        discount_factor = float(self._kernel.discount_factor_at(checked_tenor))
        if not math.isfinite(discount_factor) or discount_factor <= 0.0:
            raise InvalidCurveInput("kernel.discount_factor_at(tenor) must be finite and > 0.")
        return discount_factor

    @property
    def calibration_report(self) -> CalibrationReport | None:
        """Return the optional calibration report attached to this curve."""

        return self._calibration_report


__all__ = [
    "DiscountingCurve",
    "RatesTermStructure",
    "YieldCurve",
]
