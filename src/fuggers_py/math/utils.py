"""Validation and indexing helpers for :mod:`fuggers_py.math`.

These helpers centralize the input checks used by the numerical routines so
the solver and interpolation code can stay focused on the actual algorithms.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import ArrayLike, NDArray

from .errors import InsufficientData, InvalidInput


def assert_finite(x: Any, name: str = "x") -> float:
    """Return ``x`` as a finite ``float``.

    Parameters
    ----------
    x:
        Value to coerce.
    name:
        Name used in the error message when the value is invalid.

    Returns
    -------
    float
        Finite floating-point value.

    Raises
    ------
    InvalidInput
        If ``x`` cannot be converted to a finite float.
    """

    try:
        xf = float(x)
    except Exception as exc:  # pragma: no cover - defensive
        raise InvalidInput(f"{name} must be a real number.") from exc
    if not np.isfinite(xf):
        raise InvalidInput(f"{name} must be finite; got {x!r}.")
    return xf


def assert_finite_array(arr: ArrayLike, name: str = "arr") -> NDArray[np.float64]:
    """Return a finite floating-point array.

    Parameters
    ----------
    arr:
        Array-like input to validate.
    name:
        Name used in the error message when the value is invalid.

    Returns
    -------
    numpy.ndarray
        Array coerced to ``float`` with all values finite.

    Raises
    ------
    InvalidInput
        If the array is empty or contains non-finite values.
    """

    out = np.asarray(arr, dtype=float)
    if out.size == 0:
        raise InvalidInput(f"{name} must be non-empty.")
    if not np.all(np.isfinite(out)):
        raise InvalidInput(f"{name} must be finite.")
    return out


def assert_strictly_increasing(xs: ArrayLike, name: str = "xs") -> NDArray[np.float64]:
    """Return a 1D finite array that is strictly increasing.

    Parameters
    ----------
    xs:
        Array-like knot vector.
    name:
        Name used in the error message when the value is invalid.

    Returns
    -------
    numpy.ndarray
        One-dimensional, finite, strictly increasing array.

    Raises
    ------
    InvalidInput
        If the input is not one-dimensional, contains non-finite values, or
        is not strictly increasing.
    """

    out = assert_finite_array(xs, name=name)
    if out.ndim != 1:
        raise InvalidInput(f"{name} must be a 1D array; got shape {out.shape}.")
    if out.size >= 2 and not np.all(np.diff(out) > 0.0):
        raise InvalidInput(f"{name} must be strictly increasing.")
    return out.astype(float, copy=False)


def assert_same_length(
    a: ArrayLike,
    b: ArrayLike,
    a_name: str = "a",
    b_name: str = "b",
) -> None:
    """Validate that two one-dimensional arrays have the same length.

    Parameters
    ----------
    a, b:
        Array-like inputs to compare.
    a_name, b_name:
        Names used in the error message when the arrays are incompatible.

    Raises
    ------
    InvalidInput
        If either input is not one-dimensional or if the lengths differ.
    """

    a_arr = np.asarray(a)
    b_arr = np.asarray(b)
    if a_arr.ndim != 1 or b_arr.ndim != 1:
        raise InvalidInput(f"{a_name} and {b_name} must be 1D arrays.")
    if a_arr.shape[0] != b_arr.shape[0]:
        raise InvalidInput(
            f"{a_name} and {b_name} must have the same length; "
            f"got {a_arr.shape[0]} and {b_arr.shape[0]}."
        )


def assert_all_positive(ys: ArrayLike, name: str = "ys") -> NDArray[np.float64]:
    """Return a finite 1D array with strictly positive entries.

    Parameters
    ----------
    ys:
        Array-like values to validate.
    name:
        Name used in the error message when the value is invalid.

    Returns
    -------
    numpy.ndarray
        One-dimensional floating-point array with all entries greater than zero.

    Raises
    ------
    InvalidInput
        If the input is not one-dimensional, contains non-finite values, or
        includes non-positive entries.
    """

    out = assert_finite_array(ys, name=name)
    if out.ndim != 1:
        raise InvalidInput(f"{name} must be a 1D array; got shape {out.shape}.")
    if not np.all(out > 0.0):
        raise InvalidInput(f"{name} must be strictly positive.")
    return out.astype(float, copy=False)


def clamp(x: float, lo: float, hi: float) -> float:
    """Clamp ``x`` into the closed interval ``[lo, hi]``."""

    return float(min(max(x, lo), hi))


def bisect_segment(xs_sorted: NDArray[np.float64], x: float) -> int:
    """Return the left segment index for ``x`` inside a sorted knot vector.

    Parameters
    ----------
    xs_sorted:
        Sorted one-dimensional knot vector with at least two entries.
    x:
        Query point.

    Returns
    -------
    int
        Index of the segment whose left knot is less than or equal to ``x``.

    Raises
    ------
    InvalidInput
        If ``xs_sorted`` is not one-dimensional.
    InsufficientData
        If fewer than two knot points are supplied.
    """

    if xs_sorted.ndim != 1:
        raise InvalidInput(f"xs_sorted must be 1D; got shape {xs_sorted.shape}.")
    n = int(xs_sorted.size)
    if n < 2:
        raise InsufficientData(required=2, actual=n)
    i = int(np.searchsorted(xs_sorted, x, side="right") - 1)
    return int(np.clip(i, 0, n - 2))
