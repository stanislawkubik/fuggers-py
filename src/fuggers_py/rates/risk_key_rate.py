"""Finite-difference key-rate helpers for rates products.

Key-rate outputs use the same sign convention as PV01: positive exposure means
the instrument gains value when the targeted tenor is bumped lower.
"""

from __future__ import annotations

from decimal import Decimal

from fuggers_py._core import Tenor

from ._curve_resolver import analytics_curves_with_key_rate_bump
from .basis_swap import BasisSwap
from .basis_swap_pricer import BasisSwapPricer
from .fixed_float_swap import FixedFloatSwap
from .fra import Fra
from .fra_pricer import FraPricer
from .ois import Ois
from .risk_bpv import _pv, _relevant_currency_and_indices
from .swap_pricer import SwapPricer


_DEFAULT_TENOR_GRID = (
    Tenor.parse("6M"),
    Tenor.parse("1Y"),
    Tenor.parse("2Y"),
    Tenor.parse("5Y"),
    Tenor.parse("10Y"),
    Tenor.parse("30Y"),
)


def _coerce_tenor_grid(tenor_grid: tuple[Tenor | str, ...] | list[Tenor | str] | None) -> tuple[Tenor, ...]:
    if tenor_grid is None:
        return _DEFAULT_TENOR_GRID
    resolved = tuple(item if isinstance(item, Tenor) else Tenor.parse(item) for item in tenor_grid)
    if not resolved:
        raise ValueError("key_rate_risk requires a non-empty tenor grid.")
    return resolved


def key_rate_risk(
    instrument,
    curves: object,
    *,
    tenor_grid: tuple[Tenor | str, ...] | list[Tenor | str] | None = None,
    bump: object = Decimal("0.0001"),
    pricer: object | None = None,
) -> dict[str, Decimal]:
    """Return a tenor-by-tenor key-rate risk profile.

    Parameters
    ----------
    instrument:
        Supported rates instrument to analyze.
    curves:
        Analytics curves used for valuation.
    tenor_grid:
        Tenor nodes to bump. If omitted, a standard 6M to 30Y grid is used.
    bump:
        Raw decimal curve bump applied at each tenor node.
    pricer:
        Optional pricer instance matching the instrument type.

    Returns
    -------
    dict[str, Decimal]
        Mapping from tenor label to finite-difference sensitivity in currency
        units per one basis point of bump, signed positive when the
        instrument gains value as the targeted tenor is bumped lower.
    """

    resolved_grid = _coerce_tenor_grid(tenor_grid)
    bump_decimal = Decimal(str(bump))
    scale = bump_decimal / Decimal("0.0001")
    if scale == Decimal(0):
        raise ValueError("key_rate_risk requires a non-zero bump size.")
    currency, indices = _relevant_currency_and_indices(instrument)
    exposures: dict[str, Decimal] = {}
    for key_tenor in resolved_grid:
        bumped_up = analytics_curves_with_key_rate_bump(
            curves,
            currency=currency,
            projection_indices=indices,
            tenor_grid=resolved_grid,
            key_tenor=key_tenor,
            bump=bump_decimal,
        )
        bumped_down = analytics_curves_with_key_rate_bump(
            curves,
            currency=currency,
            projection_indices=indices,
            tenor_grid=resolved_grid,
            key_tenor=key_tenor,
            bump=-bump_decimal,
        )
        exposures[str(key_tenor)] = (_pv(instrument, bumped_down, pricer) - _pv(instrument, bumped_up, pricer)) / (
            Decimal(2) * scale
        )
    return exposures


def swap_key_rate_risk(
    instrument: FixedFloatSwap | Ois,
    curves: object,
    *,
    tenor_grid: tuple[Tenor | str, ...] | list[Tenor | str] | None = None,
    bump: object = Decimal("0.0001"),
    pricer: SwapPricer | None = None,
) -> dict[str, Decimal]:
    """Return the key-rate risk profile for a swap."""

    return key_rate_risk(
        instrument,
        curves,
        tenor_grid=tenor_grid,
        bump=bump,
        pricer=pricer or SwapPricer(),
    )


def fra_key_rate_risk(
    instrument: Fra,
    curves: object,
    *,
    tenor_grid: tuple[Tenor | str, ...] | list[Tenor | str] | None = None,
    bump: object = Decimal("0.0001"),
    pricer: FraPricer | None = None,
) -> dict[str, Decimal]:
    """Return the key-rate risk profile for an FRA."""

    return key_rate_risk(
        instrument,
        curves,
        tenor_grid=tenor_grid,
        bump=bump,
        pricer=pricer or FraPricer(),
    )


def basis_swap_key_rate_risk(
    instrument: BasisSwap,
    curves: object,
    *,
    tenor_grid: tuple[Tenor | str, ...] | list[Tenor | str] | None = None,
    bump: object = Decimal("0.0001"),
    pricer: BasisSwapPricer | None = None,
) -> dict[str, Decimal]:
    """Return the key-rate risk profile for a basis swap."""

    return key_rate_risk(
        instrument,
        curves,
        tenor_grid=tenor_grid,
        bump=bump,
        pricer=pricer or BasisSwapPricer(),
    )


__all__ = [
    "basis_swap_key_rate_risk",
    "fra_key_rate_risk",
    "key_rate_risk",
    "swap_key_rate_risk",
]
