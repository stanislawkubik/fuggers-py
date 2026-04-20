"""Current-yield helpers (`fuggers_py._measures.yields.current`).

Unsuffixed helpers return raw decimal current yields. Use the explicit
``*_pct`` wrappers for quoted percentage display values.
"""

from __future__ import annotations

from decimal import Decimal
from typing import NoReturn

from fuggers_py._core.errors import BondPricingError
from fuggers_py._measures.yields.bond import (
    current_yield as _current_yield,
    current_yield_pct as _current_yield_pct,
    current_yield_from_amount as _current_yield_from_amount,
    current_yield_from_amount_pct as _current_yield_from_amount_pct,
    current_yield_from_bond as _current_yield_from_bond,
    current_yield_from_bond_pct as _current_yield_from_bond_pct,
    current_yield_simple as _current_yield_simple,
    current_yield_simple_pct as _current_yield_simple_pct,
)
from ..errors import AnalyticsError


def _raise_invalid_input(exc: BondPricingError) -> NoReturn:
    raise AnalyticsError.invalid_input(exc.reason) from exc


def current_yield(coupon_rate: object, clean_price: object) -> Decimal:
    """Return current yield as a raw decimal.

    Parameters
    ----------
    coupon_rate : object
        Annual coupon rate as a raw decimal or Decimal-like value.
    clean_price : object
        Clean price in percent of par.

    Returns
    -------
    Decimal
        Current yield as a raw decimal rate.
    """

    try:
        return _current_yield(coupon_rate, clean_price)
    except BondPricingError as exc:
        _raise_invalid_input(exc)


def current_yield_pct(coupon_rate: object, clean_price: object) -> Decimal:
    """Return current yield as quoted percentage points."""

    try:
        return _current_yield_pct(coupon_rate, clean_price)
    except BondPricingError as exc:
        _raise_invalid_input(exc)


def current_yield_from_amount(coupon_amount: object, clean_price: object) -> Decimal:
    """Return current yield as a raw decimal.

    Parameters
    ----------
    coupon_amount : object
        Annual coupon payment in currency units per 100 face.
    clean_price : object
        Clean price in percent of par.

    Returns
    -------
    Decimal
        Current yield as a raw decimal rate.
    """

    try:
        return _current_yield_from_amount(coupon_amount, clean_price)
    except BondPricingError as exc:
        _raise_invalid_input(exc)


def current_yield_from_amount_pct(coupon_amount: object, clean_price: object) -> Decimal:
    """Return current yield as quoted percentage points."""

    try:
        return _current_yield_from_amount_pct(coupon_amount, clean_price)
    except BondPricingError as exc:
        _raise_invalid_input(exc)


def current_yield_from_bond(bond: object, clean_price: object) -> Decimal:
    """Return raw-decimal current yield from a bond-like object.

    The bond must expose ``coupon_rate`` either as a method or attribute. The
    result is always normalized to coupon-per-100-face.
    """

    try:
        return _current_yield_from_bond(bond, clean_price)
    except BondPricingError as exc:
        _raise_invalid_input(exc)


def current_yield_from_bond_pct(bond: object, clean_price: object) -> Decimal:
    """Return quoted current yield from a bond-like object."""

    try:
        return _current_yield_from_bond_pct(bond, clean_price)
    except BondPricingError as exc:
        _raise_invalid_input(exc)


def current_yield_simple(coupon_rate: float, clean_price: float) -> float:
    """Return current yield as a raw decimal using float arithmetic."""

    try:
        return _current_yield_simple(coupon_rate, clean_price)
    except BondPricingError as exc:
        _raise_invalid_input(exc)


def current_yield_simple_pct(coupon_rate: float, clean_price: float) -> float:
    """Return current yield as quoted percentage points using float arithmetic."""

    try:
        return _current_yield_simple_pct(coupon_rate, clean_price)
    except BondPricingError as exc:
        _raise_invalid_input(exc)


__all__ = [
    "current_yield",
    "current_yield_pct",
    "current_yield_from_amount",
    "current_yield_from_amount_pct",
    "current_yield_from_bond",
    "current_yield_from_bond_pct",
    "current_yield_simple",
    "current_yield_simple_pct",
]
