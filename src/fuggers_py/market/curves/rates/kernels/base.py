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

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum, auto
from types import MappingProxyType
from typing import Any

from fuggers_py.core.types import Compounding

from ...conversion import ValueConverter
from ...errors import InvalidCurveInput

_CONTINUOUS = Compounding.CONTINUOUS


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


class CurveKernelKind(Enum):
    """Internal family name for one mathematical curve representation."""

    LINEAR_ZERO = auto()
    LOG_LINEAR_DISCOUNT = auto()
    PIECEWISE_CONSTANT = auto()
    PIECEWISE_FLAT_FORWARD = auto()
    MONOTONE_CONVEX = auto()
    CUBIC_SPLINE = auto()
    NELSON_SIEGEL = auto()
    SVENSSON = auto()
    EXPONENTIAL_SPLINE = auto()


@dataclass(frozen=True, slots=True)
class KernelSpec:
    """Immutable internal config for one curve-kernel family.

    ``kind`` names the representation family. ``parameters`` carries family-
    specific settings such as fixed knots, decay values, or interpolation
    options. This is internal config only. It is not the realized kernel.
    """

    kind: CurveKernelKind
    parameters: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.kind, CurveKernelKind):
            raise InvalidCurveInput("kind must be a CurveKernelKind.")
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


__all__ = [
    "CurveKernel",
    "CurveKernelKind",
    "KernelSpec",
]
