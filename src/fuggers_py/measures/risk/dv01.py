"""DV01 helpers (`fuggers_py.measures.risk.dv01`).

DV01 values use the shared signed convention: positive when price rises as
yield falls by 1 bp. The ``*_per_100_face`` helper normalizes the result to a
100 face amount.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from ..errors import AnalyticsError


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


@dataclass(frozen=True, slots=True)
class DV01:
    """Wrapper for a signed DV01 value.

    Parameters
    ----------
    value:
        Signed DV01 amount in currency units. Positive values mean PV rises
        when yield falls by 1 bp.
    """

    value: Decimal

    def as_decimal(self) -> Decimal:
        """Return the DV01 value as a Decimal."""

        return self.value


def dv01_from_duration(modified_duration: object, dirty_price: object, face: object) -> Decimal:
    """Return signed DV01 from modified duration, price, and face amount.

    Parameters
    ----------
    modified_duration:
        Modified duration in years.
    dirty_price:
        Dirty price in percent of par.
    face:
        Face notional in currency units.

    Returns
    -------
    Decimal
        Signed DV01 in currency units.
    """

    md = _to_decimal(modified_duration)
    price = _to_decimal(dirty_price)
    fv = _to_decimal(face)
    return md * (price / Decimal(100)) * fv * Decimal("0.0001")


def dv01_from_prices(price_down: object, price_up: object) -> Decimal:
    """Return signed DV01 from down- and up-shocked prices.

    Returns
    -------
    Decimal
        Half the price difference between the down-shock and up-shock prices.
    """

    pd = _to_decimal(price_down)
    pu = _to_decimal(price_up)
    return (pd - pu) / Decimal(2)


def dv01_per_100_face(modified_duration: object, dirty_price: object) -> Decimal:
    """Return signed DV01 normalized to 100 face.

    Returns
    -------
    Decimal
        DV01 per 100 face in currency units.
    """

    return dv01_from_duration(modified_duration, dirty_price, Decimal(100))


def notional_from_dv01(target_dv01: object, modified_duration: object, dirty_price: object) -> Decimal:
    """Return face notional needed to target a signed DV01.

    The notional is solved from the DV01 identity and retains the sign implied
    by ``target_dv01``.
    """

    md = _to_decimal(modified_duration)
    price = _to_decimal(dirty_price)
    if md == 0 or price == 0:
        raise AnalyticsError.invalid_input("Modified duration and price must be positive for notional calculation.")
    target = _to_decimal(target_dv01)
    return target / (md * (price / Decimal(100)) * Decimal("0.0001"))


__all__ = [
    "DV01",
    "dv01_from_duration",
    "dv01_from_prices",
    "dv01_per_100_face",
    "notional_from_dv01",
]
