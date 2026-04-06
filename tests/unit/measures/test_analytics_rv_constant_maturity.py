from __future__ import annotations

from decimal import Decimal

import pytest

from fuggers_py.measures.rv import estimate_new_issue_fair_value, generate_constant_maturity_benchmark
from fuggers_py.measures.rv.new_issue import NewIssueRequest

from tests.helpers._fitted_bond_helpers import REFERENCE_DATE, exponential_model, fit_result


def test_constant_maturity_benchmark_uses_benchmark_metadata_and_returns_a_fair_value() -> None:
    result = fit_result(curve_model=exponential_model(), regression_coefficient=Decimal("0.25"))
    benchmark = generate_constant_maturity_benchmark(result, Decimal("6.0"), component_count=3)

    assert all(component.benchmark_flag for component in benchmark.benchmark.components)
    assert float(benchmark.benchmark.weighted_maturity_years) == pytest.approx(6.0, abs=1.0)
    assert benchmark.fair_value_clean_price > Decimal(0)
    assert benchmark.fair_value_yield > Decimal(0)


def test_new_issue_fair_value_reports_positive_concession_for_a_cheap_marketed_price() -> None:
    result = fit_result(curve_model=exponential_model(), regression_coefficient=Decimal("0.25"))
    benchmark = generate_constant_maturity_benchmark(result, Decimal("7.0"), component_count=3)
    estimate = estimate_new_issue_fair_value(
        result,
        NewIssueRequest(
            issue_date=REFERENCE_DATE,
            maturity_date=REFERENCE_DATE.add_years(7),
            coupon_rate=Decimal("0.0325"),
            marketed_clean_price=benchmark.fair_value_clean_price - Decimal("0.25"),
            regression_exposures={"liquidity": Decimal("0")},
        ),
    )

    assert estimate.concession_price is not None
    assert estimate.concession_bps is not None
    assert estimate.concession_price > Decimal(0)
    assert estimate.concession_bps > Decimal(0)
