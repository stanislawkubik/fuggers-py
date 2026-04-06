"""Regression helpers for fitted bond curves.

Regression overlays are supplied as named exposure columns aligned to the
observation order passed into the fitter.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Mapping, Sequence

import numpy as np
from numpy.typing import NDArray


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _normalize_name(name: str) -> str:
    normalized = name.strip().lower().replace("-", "_").replace(" ", "_")
    if not normalized:
        raise ValueError("Regression exposure names must be non-empty.")
    return normalized


def _normalized_exposure_map(
    regression_exposures: Mapping[str, object] | None,
) -> dict[str, Decimal]:
    if not regression_exposures:
        return {}
    normalized: dict[str, Decimal] = {}
    for raw_name, value in regression_exposures.items():
        name = _normalize_name(raw_name)
        if name in normalized:
            raise ValueError(f"Duplicate regression exposure name: {name}.")
        normalized[name] = _to_decimal(value)
    return normalized


def build_regression_matrix(
    observation_count: int,
    *,
    regression_exposures: Mapping[str, Sequence[object]] | None,
) -> tuple[tuple[str, ...], NDArray[np.float64]]:
    """Return normalized exposure names and the dense regression matrix."""

    if not regression_exposures:
        return (), np.zeros((observation_count, 0), dtype=float)

    variable_names: list[str] = []
    columns: list[list[float]] = []
    seen_names: set[str] = set()
    for raw_name, raw_values in regression_exposures.items():
        name = _normalize_name(raw_name)
        if name in seen_names:
            raise ValueError(f"Duplicate regression exposure name: {name}.")
        values = tuple(_to_decimal(value) for value in raw_values)
        if len(values) != observation_count:
            raise ValueError(f"Regression exposure '{name}' must have {observation_count} values.")
        seen_names.add(name)
        variable_names.append(name)
        columns.append([float(value) for value in values])

    matrix = np.column_stack(columns).astype(float, copy=False) if columns else np.zeros((observation_count, 0), dtype=float)
    return tuple(variable_names), matrix


def evaluate_regression_adjustment(
    regression_exposures: Mapping[str, object] | None,
    *,
    coefficients: Mapping[str, Decimal],
) -> Decimal:
    """Evaluate the fitted regression overlay for one bond."""

    if not coefficients:
        return Decimal(0)
    normalized_exposures = _normalized_exposure_map(regression_exposures)
    missing_names = [name for name in coefficients if name not in normalized_exposures]
    if missing_names:
        missing = ", ".join(sorted(missing_names))
        raise ValueError(f"Regression exposures are missing values for: {missing}.")
    total = Decimal(0)
    for name, coefficient in coefficients.items():
        total += _to_decimal(coefficient) * normalized_exposures[name]
    return total


__all__ = [
    "build_regression_matrix",
    "evaluate_regression_adjustment",
]
