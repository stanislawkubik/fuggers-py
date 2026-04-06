"""Exceptions raised by calc-layer routing, scheduling, and orchestration.

The calc layer uses a small error hierarchy so routing failures, scheduling
failures, and missing configuration are easy to separate in callers.
"""

from __future__ import annotations

from fuggers_py.core.errors import FuggersError


class EngineError(FuggersError):
    """Base exception for calc-layer failures."""


class CurveNotFoundError(EngineError):
    """Raised when a named curve or stored curve input cannot be found."""


class RoutingError(EngineError):
    """Raised when the router cannot dispatch or complete a pricing path."""


class EngineConfigurationError(EngineError):
    """Raised when an engine component is missing a required dependency."""


class SchedulerError(EngineError):
    """Raised when a scheduler cannot be configured or run."""


__all__ = ["CurveNotFoundError", "EngineConfigurationError", "EngineError", "RoutingError", "SchedulerError"]
