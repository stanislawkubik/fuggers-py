from __future__ import annotations

from decimal import Decimal

from fuggers_py.bonds.types import ASWType
from fuggers_py._runtime import (
    BenchmarkReference,
    BidAskSpreadConfig,
    PricingSpec,
    QuoteSide,
)
from fuggers_py._core import CurveId
from fuggers_py._runtime.state import AnalyticsCurves


def test_pricing_spec_components() -> None:
    assert QuoteSide.BID.value == "bid"
    symmetric = BidAskSpreadConfig.symmetric(Decimal("0.20"))
    assert symmetric.adjust(Decimal("100"), QuoteSide.BID) == Decimal("99.90")
    assert symmetric.adjust(Decimal("100"), QuoteSide.ASK) == Decimal("100.10")

    asymmetric = BidAskSpreadConfig.asymmetric(bid_adjustment=Decimal("-0.05"), ask_adjustment=Decimal("0.15"))
    assert asymmetric.adjust(Decimal("100"), QuoteSide.BID) == Decimal("99.95")
    assert asymmetric.adjust(Decimal("100"), QuoteSide.ASK) == Decimal("100.15")

    benchmark = BenchmarkReference.by_curve(CurveId("usd.gov"))
    tenor_reference = BenchmarkReference.by_tenor("5Y")
    assert benchmark.curve_id == CurveId("usd.gov")
    assert tenor_reference.tenor_object() is not None

    curves = AnalyticsCurves(
        discount_curve="discount",
        forward_curve="forward",
        benchmark_curve="swap",
        inflation_curve="inflation",
        inflation_curves={"CPURNSA": "cpi-curve"},
    )
    assert curves.get("discount") == "discount"
    assert curves.get("benchmark") == "swap"
    assert curves.get("inflation") == "inflation"
    assert curves.get("inflation:cpurnsa") == "cpi-curve"

    spec = PricingSpec()
    assert spec.quote_side is QuoteSide.MID
    assert spec.compute_spreads is True
    assert spec.asset_swap_type is ASWType.PAR_PAR
    assert spec.route_callable_with_oas is True
