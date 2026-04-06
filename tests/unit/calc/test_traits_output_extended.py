from __future__ import annotations

from decimal import Decimal

from fuggers_py.core import Date
from fuggers_py.calc import (
    AnalyticsOutput,
    BasisSwapQuoteOutput,
    CdsQuoteOutput,
    FutureQuoteOutput,
    RepoPricingResult,
    RoutedFraPricingResult,
    RvSignalOutput,
    SwapQuoteOutput,
    PortfolioAnalyticsOutput,
)
from fuggers_py.core import InstrumentId


def test_extended_quote_outputs_coerce_decimals_and_ids() -> None:
    swap_output = SwapQuoteOutput(
        instrument_id="usd-swap-5y",
        pricing_path=" vanilla_swap ",
        par_rate="0.0380",
        present_value="125000.50",
        fixed_leg_pv="-62500.25",
        floating_leg_pv="187500.75",
        annuity="4.55",
        dv01="1250.0",
        warnings=["stubbed"],
        notes=["desk mark"],
    )
    basis_output = BasisSwapQuoteOutput(
        instrument_id="usd-basis-5y",
        pricing_path=" basis_swap ",
        basis_spread="0.0012",
        present_value="5000",
        pay_leg_pv="-1000",
        receive_leg_pv="6000",
        dv01="75.0",
    )
    future_output = FutureQuoteOutput(
        instrument_id="ust-mar26",
        pricing_path=" bond_future ",
        futures_price="112.5",
        fair_value="112.35",
        implied_repo_rate="0.0405",
        net_basis="-0.12",
        gross_basis="0.08",
        conversion_factor="0.8125",
        dv01="85.0",
        ctd_instrument_id="US91282CKH3",
        settlement_date=Date.from_ymd(2026, 3, 13),
    )
    cds_output = CdsQuoteOutput(
        instrument_id="acme-cds-5y",
        pricing_path=" cds_curve ",
        par_spread="0.0125",
        upfront="-0.01",
        present_value="25000",
        cs01="1200",
        pv01="75",
        risky_duration="4.1",
        recovery_rate="0.4",
    )
    rv_signal = RvSignalOutput(
        instrument_id="acme-cds-5y",
        signal_name=" basis_richness ",
        score="1.5",
        z_score="-2.1",
        direction=" rich ",
        bucket=" 5Y ",
        horizon=" 1m ",
        notes=["cross-market"],
    )

    assert swap_output.instrument_id == InstrumentId("usd-swap-5y")
    assert swap_output.pricing_path == "vanilla_swap"
    assert swap_output.par_rate == Decimal("0.0380")
    assert swap_output.pv01 == Decimal("1250.0")
    assert swap_output.warnings == ("stubbed",)
    assert swap_output.notes == ("desk mark",)

    assert basis_output.basis_spread == Decimal("0.0012")
    assert basis_output.pv01 == Decimal("75.0")

    assert future_output.ctd_instrument_id == InstrumentId("US91282CKH3")
    assert future_output.futures_price == Decimal("112.5")
    assert future_output.conversion_factor == Decimal("0.8125")
    assert future_output.pv01 == Decimal("85.0")

    assert cds_output.par_spread == Decimal("0.0125")
    assert cds_output.recovery_rate == Decimal("0.4")
    assert cds_output.cs01 == Decimal("1200")

    assert rv_signal.signal_name == "basis_richness"
    assert rv_signal.score == Decimal("1.5")
    assert rv_signal.z_score == Decimal("-2.1")
    assert rv_signal.direction == "rich"
    assert rv_signal.bucket == "5Y"
    assert rv_signal.horizon == "1m"
    assert rv_signal.notes == ("cross-market",)


def test_analytics_output_union_accepts_new_output_records() -> None:
    future: AnalyticsOutput = FutureQuoteOutput(instrument_id="ust-jun26", futures_price="110.25")
    fra: AnalyticsOutput = RoutedFraPricingResult(
        instrument_id="fra-1",
        forward_rate="0.04",
        present_value="1250",
        year_fraction="0.25",
        discount_factor="0.99",
        dv01="12.5",
    )
    repo: AnalyticsOutput = RepoPricingResult(
        collateral_value="1000000",
        haircut_amount="20000",
        cash_lent="980000",
        year_fraction="0.0833333333",
        interest_amount="2450",
        repurchase_amount="982450",
        curve_zero_rate="0.04",
        forward_rate="0.0401",
        funding_spread="-0.01",
    )

    assert isinstance(future, FutureQuoteOutput)
    assert future.instrument_id == InstrumentId("ust-jun26")
    assert isinstance(fra, RoutedFraPricingResult)
    assert fra.dv01 == Decimal("12.5")
    assert fra.pv01 == Decimal("12.5")
    assert isinstance(repo, RepoPricingResult)
    assert repo.forward_rate == Decimal("0.0401")


def test_portfolio_output_backfills_aggregate_dv01_from_pv01() -> None:
    analytics = PortfolioAnalyticsOutput(pv01="25.0")

    assert analytics.aggregate_dv01 == Decimal("25.0")
    assert analytics.pv01 == Decimal("25.0")
