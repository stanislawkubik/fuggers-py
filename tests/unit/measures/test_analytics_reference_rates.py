from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

import pytest

from fuggers_py.bonds.spreads import (
    GQDSecuredUnsecuredBasisModel,
    SecuredUnsecuredBasisModel,
    adjusted_term_rate,
    compounding_convexity_breakdown,
    reference_rate_decomposition,
    secured_unsecured_overnight_basis,
)


def test_reference_rate_decomposition_uses_explicit_ladder_sign_convention() -> None:
    breakdown = reference_rate_decomposition(
        repo_rate=Decimal("0.0310"),
        general_collateral_rate=Decimal("0.0320"),
        unsecured_overnight_rate=Decimal("0.0340"),
        term_rate=Decimal("0.0370"),
        convexity_adjustment=Decimal("0.0002"),
    )

    assert breakdown.repo_vs_gc == Decimal("0.0010")
    assert breakdown.gc_vs_unsecured_overnight == Decimal("0.0020")
    assert breakdown.unsecured_overnight_vs_term == Decimal("0.0032")
    assert breakdown.total_funding_basis == Decimal("0.0062")
    assert breakdown.adjusted_term_rate == Decimal("0.0372")


def test_compounding_convexity_breakdown_and_adjusted_term_rate_are_consistent() -> None:
    breakdown = compounding_convexity_breakdown(
        simple_rate=Decimal("0.0500"),
        year_fraction=Decimal("0.50"),
        convexity_adjustment=Decimal("0.0001"),
    )

    assert breakdown.compounded_equivalent_rate > breakdown.simple_rate
    assert breakdown.compounding_adjustment == breakdown.compounded_equivalent_rate - breakdown.simple_rate
    assert breakdown.adjusted_term_rate == adjusted_term_rate(
        simple_rate=Decimal("0.0500"),
        year_fraction=Decimal("0.50"),
        convexity_adjustment=Decimal("0.0001"),
    )


def test_secured_unsecured_overnight_basis_defaults_to_gqd_model() -> None:
    basis = secured_unsecured_overnight_basis(
        loss_given_default=Decimal("0.60"),
        default_probability=Decimal("0.02"),
        discount_factor=Decimal("0.99"),
    )

    assert basis == GQDSecuredUnsecuredBasisModel().basis(
        loss_given_default=Decimal("0.60"),
        default_probability=Decimal("0.02"),
        discount_factor=Decimal("0.99"),
    )
    assert basis == Decimal("0.011880")


def test_secured_unsecured_overnight_basis_accepts_custom_model() -> None:
    @dataclass(frozen=True, slots=True)
    class FlatBasisModel(SecuredUnsecuredBasisModel):
        value: Decimal

        def basis(
            self,
            *,
            loss_given_default: object,
            default_probability: object,
            discount_factor: object,
        ) -> Decimal:
            return self.value

    basis = secured_unsecured_overnight_basis(
        loss_given_default=Decimal("0.60"),
        default_probability=Decimal("0.02"),
        discount_factor=Decimal("0.99"),
        model=FlatBasisModel(Decimal("0.0015")),
    )

    assert basis == Decimal("0.0015")


def test_secured_unsecured_basis_validates_gqd_inputs() -> None:
    with pytest.raises(ValueError, match="loss_given_default"):
        secured_unsecured_overnight_basis(
            loss_given_default=Decimal("1.10"),
            default_probability=Decimal("0.02"),
            discount_factor=Decimal("0.99"),
        )
