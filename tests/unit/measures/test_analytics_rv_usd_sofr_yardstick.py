from __future__ import annotations

from decimal import Decimal

import pytest

from fuggers_py.measures.rv import (
    CommonCurrencyFloatingBondView,
    decompose_asw_basis_cds_links,
    decompose_floating_view_links,
    usd_sofr_adjusted_rv_from_links,
    usd_sofr_adjusted_rv_measure,
)
from fuggers_py.reference.bonds.types import Tenor
from fuggers_py.core import Currency, Date


def _floating_view(*, target_currency: Currency = Currency.USD, target_index_name: str = "SOFR") -> CommonCurrencyFloatingBondView:
    return CommonCurrencyFloatingBondView(
        instrument_id=None,
        maturity_date=Date.from_ymd(2031, 1, 15),
        source_currency=Currency.EUR,
        target_currency=target_currency,
        source_index_name="EURIBOR",
        source_index_tenor=Tenor.parse("6M"),
        target_index_name=target_index_name,
        target_index_tenor=Tenor.parse("3M"),
        asset_swap_spread=Decimal("0.0100"),
        same_currency_basis=Decimal("0.0015"),
        cross_currency_basis=Decimal("0.0025"),
        common_currency_floating_spread=Decimal("0.0140"),
        asset_swap_result=object(),
    )


def test_usd_sofr_adjusted_rv_measure_reuses_asw_basis_cds_decomposition() -> None:
    floating_view = _floating_view()
    link_breakdown = decompose_floating_view_links(
        floating_view,
        adjusted_cds_spread=Decimal("0.0120"),
    )
    direct_breakdown = decompose_asw_basis_cds_links(
        asset_swap_spread=Decimal("0.0100"),
        same_currency_basis=Decimal("0.0015"),
        cross_currency_basis=Decimal("0.0025"),
        adjusted_cds_spread=Decimal("0.0120"),
    )
    measure = usd_sofr_adjusted_rv_measure(
        floating_view,
        yardstick_spread=Decimal("0.0130"),
        adjusted_cds_spread=Decimal("0.0120"),
    )

    assert direct_breakdown == link_breakdown
    assert link_breakdown.funding_basis_total == Decimal("0.0040")
    assert link_breakdown.common_currency_floating_spread == Decimal("0.0140")
    assert link_breakdown.residual_to_adjusted_cds == Decimal("0.0020")
    assert measure == usd_sofr_adjusted_rv_from_links(
        link_breakdown,
        yardstick_spread=Decimal("0.0130"),
    )
    assert measure.residual_to_yardstick == Decimal("0.0010")
    assert measure.residual_to_adjusted_cds == Decimal("0.0020")


def test_usd_sofr_adjusted_rv_measure_validates_target_currency_and_index() -> None:
    with pytest.raises(ValueError, match="USD SOFR"):
        usd_sofr_adjusted_rv_measure(
            _floating_view(target_currency=Currency.EUR, target_index_name="ESTR"),
            yardstick_spread=Decimal("0.0130"),
        )
