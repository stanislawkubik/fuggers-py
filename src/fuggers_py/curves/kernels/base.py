"""Shared internal kernel contracts for curve fitting.

The public curve classes define what callers may ask for. The kernel layer
defines the internal fitted curve shape that sits behind ``YieldCurve``.

The shared kernel contract is intentionally small. It keeps the base case rate-
first: each concrete kernel must be able to give the fitted rate curve on a
tenor domain. Discount factors are then derived from that fitted rate curve.

1. the supported tenor domain
2. the fitted rate at a tenor
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

from fuggers_py._core.types import Compounding

from ..conversion import ValueConverter
from ..errors import InvalidCurveInput

_CONTINUOUS = Compounding.CONTINUOUS
_KERNEL_KINDS = frozenset(
    {
        "linear_zero",
        "log_linear_discount",
        "piecewise_constant",
        "piecewise_flat_forward",
        "monotone_convex",
        "cubic_spline",
        "nelson_siegel",
        "svensson",
        "exponential_spline",
    }
)


def normalize_kernel_kind(value: object) -> str:
    """Return one supported kernel name."""

    if not isinstance(value, str):
        raise InvalidCurveInput("kind must be a kernel name string.")
    normalized = value.strip().lower()
    if normalized not in _KERNEL_KINDS:
        allowed = ", ".join(sorted(_KERNEL_KINDS))
        raise InvalidCurveInput(f"kind must be one of: {allowed}.")
    return normalized


def _freeze_parameter_value(value: Any) -> Any:
    """Return a read-only snapshot-friendly version of one kernel parameter."""

    if isinstance(value, Mapping):
        frozen_items = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise InvalidCurveInput("kernel parameter keys must be strings.")
            frozen_items[key] = _freeze_parameter_value(item)
        return MappingProxyType(frozen_items)
    if isinstance(value, list | tuple):
        return tuple(_freeze_parameter_value(item) for item in value)
    if isinstance(value, set | frozenset):
        return frozenset(_freeze_parameter_value(item) for item in value)
    return value


@dataclass(frozen=True, slots=True)
class KernelSpec:
    """Immutable internal config for one curve-kernel family.

    ``kind`` names the representation family. ``parameters`` carries family-
    specific settings such as fixed knots, decay values, or interpolation
    options. This is internal config only. It is not the realized kernel.
    """

    kind: str
    parameters: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "kind", normalize_kernel_kind(self.kind))
        if not isinstance(self.parameters, Mapping):
            raise InvalidCurveInput("parameters must be a mapping.")
        frozen_parameters = {}
        for name, value in self.parameters.items():
            if not isinstance(name, str):
                raise InvalidCurveInput("kernel parameter keys must be strings.")
            frozen_parameters[name] = _freeze_parameter_value(value)
        object.__setattr__(self, "parameters", MappingProxyType(frozen_parameters))


class CurveKernel(ABC):
    """Internal mathematical representation behind one fitted curve.

    Kernels are not public curve objects. They sit behind ``YieldCurve`` and
    let us swap interpolation families, spline families, or parametric models
    without changing the pricing-facing curve API.

    Concrete kernels may store zero rates, forward rates, discount factors, or
    model parameters internally. The shared interface does not expose that.
    The shared contract only says that the kernel must give the fitted rate
    curve at a tenor. Discount factors are derived from that fitted rate view
    unless a concrete kernel overrides the default implementation.
    """

    @abstractmethod
    def max_t(self) -> float:
        """Return the inclusive upper tenor bound in years."""

    @abstractmethod
    def rate_at(self, tenor: float) -> float:
        """Return the fitted curve rate at ``tenor``."""

    def discount_factor_at(self, tenor: float) -> float:
        """Return the discount factor implied by the fitted rate at ``tenor``."""

        checked_tenor = float(tenor)
        if checked_tenor == 0.0:
            return 1.0
        return ValueConverter.zero_to_df(self.rate_at(checked_tenor), checked_tenor, _CONTINUOUS)

    def _kernel_label(self) -> str:
        kind = getattr(self, "kind", None)
        if isinstance(kind, str):
            return kind
        return type(self).__name__

    def terminal_zero_rate(self) -> float:
        """Return the zero-rate view at the inclusive upper tenor bound."""

        return float(self.rate_at(self.max_t()))

    def terminal_native_rate(self) -> float:
        """Return the kernel-native final rate when that rate is well defined."""

        raise InvalidCurveInput(f"{self._kernel_label()} does not support hold_last_native_rate extrapolation.")

    def terminal_native_discount_factor_at(self, tenor: float) -> float:
        """Return the discount factor implied by holding the native final value."""

        return ValueConverter.zero_to_df(self.terminal_native_rate(), float(tenor), _CONTINUOUS)

    def terminal_forward_rate(self) -> float:
        """Return the final forward rate when that rate is well defined."""

        raise InvalidCurveInput(f"{self._kernel_label()} does not support hold_last_forward_rate extrapolation.")

    def terminal_forward_discount_factor_at(self, tenor: float) -> float:
        """Return the discount factor implied by holding the final forward rate."""

        max_t = float(self.max_t())
        if max_t <= 0.0:
            raise InvalidCurveInput("hold_last_forward_rate requires max_t() > 0.")
        final_discount_factor = float(self.discount_factor_at(max_t))
        final_forward_rate = float(self.terminal_forward_rate())
        return final_discount_factor * math.exp(-final_forward_rate * (float(tenor) - max_t))


__all__ = [
    "CurveKernel",
    "KernelSpec",
]
