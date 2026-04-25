from __future__ import annotations

from decimal import Decimal

from fuggers_py.bonds.spreads import DiscountMarginCalculator, OASCalculator
from fuggers_py.bonds.options import HullWhiteModel
from fuggers_py._core import Date
from fuggers_py.portfolio import (
    Holding,
    PortfolioBenchmark,
    PortfolioBuilder,
    aggregate_key_rate_profile,
    calculate_portfolio_analytics,
    run_stress_scenarios,
    standard_scenarios,
)

from tests.helpers._portfolio_helpers import make_benchmark, make_callable_puttable, make_curve, make_fixed_bond, make_frn


def test_research_workflow_end_to_end() -> None:
    ref = Date.from_ymd(2024, 1, 10)
    discount_curve = make_curve(ref)
    projection_curve = make_curve(ref, shift=Decimal("0.0025"))
    frn, _ = make_frn(ref)
    callable_bond = make_callable_puttable(ref)
    plain_bond = make_fixed_bond(ref, years=4, coupon="0.045")

    dm = DiscountMarginCalculator(forward_curve=projection_curve, discount_curve=discount_curve).calculate(
        frn,
        Decimal("100.0"),
        ref,
    )
    model = HullWhiteModel(mean_reversion=Decimal("0.03"), volatility=Decimal("0.01"), term_structure=discount_curve)
    oas = OASCalculator(model=model).calculate(callable_bond, Decimal("100.0"), ref)

    portfolio = (
        PortfolioBuilder()
        .with_currency(plain_bond.currency())
        .add_holding(Holding(instrument=frn, quantity=Decimal("100"), clean_price=Decimal("100"), label="frn"))
        .add_holding(Holding(instrument=callable_bond, quantity=Decimal("100"), clean_price=Decimal("101"), label="callable"))
        .add_holding(Holding(instrument=plain_bond, quantity=Decimal("100"), clean_price=Decimal("99.5"), label="plain"))
        .build()
    )

    summary = calculate_portfolio_analytics(portfolio, curve=discount_curve, settlement_date=ref)
    key_rates = aggregate_key_rate_profile(portfolio, curve=discount_curve, settlement_date=ref)
    benchmark = PortfolioBenchmark(portfolio, make_benchmark(ref))
    stress = run_stress_scenarios(portfolio, curve=discount_curve, settlement_date=ref, scenarios=standard_scenarios())

    assert dm.is_finite()
    assert oas.is_finite()
    assert summary.duration > 0
    assert key_rates
    assert abs(sum(summary.weights.values()) - Decimal("1")) < Decimal("0.000001")
    assert benchmark.compare(discount_curve, ref).active_duration.is_finite()
    assert stress["+10bps parallel"].actual_change < 0
