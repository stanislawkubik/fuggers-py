"""Invoice-price helpers for government bond futures.

Invoice helpers convert a futures quote in percent of par into the delivery
invoice clean price, invoice dirty price, and the corresponding currency cash
amount for a given contract size.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


@dataclass(frozen=True, slots=True)
class InvoiceBreakdown:
    """Break out the futures invoice calculation.

    Attributes
    ----------
    futures_price
        Futures quote in percent of par.
    conversion_factor
        Unitless conversion factor applied to the futures quote.
    accrued_interest
        Accrued interest added to the invoice price, in percent of par.
    invoice_clean_price
        Clean invoice price in percent of par.
    invoice_dirty_price
        Dirty invoice price in percent of par.
    invoice_amount
        Delivery cash amount in currency units.
    """

    futures_price: Decimal
    conversion_factor: Decimal
    accrued_interest: Decimal
    invoice_clean_price: Decimal
    invoice_dirty_price: Decimal
    invoice_amount: Decimal


def invoice_clean_price(futures_price: object, conversion_factor: object) -> Decimal:
    """Return the invoice clean price in percent of par."""
    return _to_decimal(futures_price) * _to_decimal(conversion_factor)


def invoice_price(futures_price: object, conversion_factor: object, accrued_interest: object = Decimal(0)) -> Decimal:
    """Return the invoice dirty price in percent of par."""
    return invoice_clean_price(futures_price, conversion_factor) + _to_decimal(accrued_interest)


def invoice_amount(
    contract_size: object,
    futures_price: object,
    conversion_factor: object,
    accrued_interest: object = Decimal(0),
) -> Decimal:
    """Return the delivery cash amount in currency units."""
    return _to_decimal(contract_size) * invoice_price(futures_price, conversion_factor, accrued_interest) / Decimal(100)


def invoice_breakdown(
    contract_size: object,
    futures_price: object,
    conversion_factor: object,
    accrued_interest: object = Decimal(0),
) -> InvoiceBreakdown:
    """Return all invoice components in one record."""
    clean = invoice_clean_price(futures_price, conversion_factor)
    dirty = invoice_price(futures_price, conversion_factor, accrued_interest)
    return InvoiceBreakdown(
        futures_price=_to_decimal(futures_price),
        conversion_factor=_to_decimal(conversion_factor),
        accrued_interest=_to_decimal(accrued_interest),
        invoice_clean_price=clean,
        invoice_dirty_price=dirty,
        invoice_amount=invoice_amount(contract_size, futures_price, conversion_factor, accrued_interest),
    )


__all__ = ["InvoiceBreakdown", "invoice_amount", "invoice_breakdown", "invoice_clean_price", "invoice_price"]
