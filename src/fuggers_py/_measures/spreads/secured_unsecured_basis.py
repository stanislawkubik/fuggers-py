"""Secured-versus-unsecured overnight basis helpers.

The public basis helpers return raw decimal spreads. Positive values indicate
that unsecured overnight funding trades above secured overnight funding.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


class SecuredUnsecuredBasisModel(Protocol):
    """Protocol for secured-versus-unsecured overnight basis models."""

    def basis(
        self,
        *,
        loss_given_default: object,
        default_probability: object,
        discount_factor: object,
    ) -> Decimal:
        """Return the overnight basis as a raw decimal spread."""
        ...


@dataclass(frozen=True, slots=True)
class GQDSecuredUnsecuredBasisModel:
    """Basis approximation ``g * q * d`` in raw decimal form."""

    def basis(
        self,
        *,
        loss_given_default: object,
        default_probability: object,
        discount_factor: object,
    ) -> Decimal:
        """Return the overnight basis as a raw decimal spread."""
        lgd = _to_decimal(loss_given_default)
        default_prob = _to_decimal(default_probability)
        discount = _to_decimal(discount_factor)
        if lgd < Decimal(0) or lgd > Decimal(1):
            raise ValueError("loss_given_default must lie in [0, 1].")
        if default_prob < Decimal(0) or default_prob > Decimal(1):
            raise ValueError("default_probability must lie in [0, 1].")
        if discount < Decimal(0):
            raise ValueError("discount_factor must be non-negative.")
        return lgd * default_prob * discount


def secured_unsecured_overnight_basis(
    *,
    loss_given_default: object,
    default_probability: object,
    discount_factor: object,
    model: SecuredUnsecuredBasisModel | None = None,
) -> Decimal:
    """Return the secured-versus-unsecured overnight basis as a raw decimal."""
    resolved_model = model or GQDSecuredUnsecuredBasisModel()
    return resolved_model.basis(
        loss_given_default=loss_given_default,
        default_probability=default_probability,
        discount_factor=discount_factor,
    )


__all__ = [
    "GQDSecuredUnsecuredBasisModel",
    "SecuredUnsecuredBasisModel",
    "secured_unsecured_overnight_basis",
]
