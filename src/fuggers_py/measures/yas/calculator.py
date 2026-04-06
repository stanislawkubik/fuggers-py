"""YAS calculator (`fuggers_py.measures.yas.calculator`).

This calculator assembles display fields for the YAS screen. Yields are
presented as quoted percentages, spreads as basis points, and settlement
invoices as percent-of-par inputs plus currency amounts.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from fuggers_py.products.bonds.traits import Bond
from fuggers_py.core.traits import YieldCurve
from fuggers_py.core.types import Date, Price

from ..errors import AnalyticsError
from ..pricing import BondPricer
from ..risk import BondRiskCalculator
from ..spreads import BenchmarkKind, BenchmarkSpec, GovernmentCurve, g_spread_with_benchmark_bps, z_spread
from ..yields import current_yield_from_bond_pct, simple_yield, true_yield
from .analysis import BloombergReference, ValidationFailure, YasAnalysis, YasAnalysisBuilder
from .invoice import SettlementInvoiceBuilder


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, Price):
        return value.as_percentage()
    return Decimal(str(value))


@dataclass(frozen=True, slots=True)
class YASCalculator:
    """Build a complete YAS analysis for a bond.

    Parameters
    ----------
    curve:
        Curve used for z-spread calculation.
    government_curve:
        Optional government curve used for g-spread calculation.
    benchmark:
        Optional benchmark selection for the g-spread view.
    """

    curve: YieldCurve
    government_curve: GovernmentCurve | None = None
    benchmark: BenchmarkSpec | None = None

    def calculate(self, bond: Bond, clean_price: Price | Decimal, settlement_date: Date) -> YasAnalysis:
        """Return YAS display fields, risk metrics, and settlement invoice."""

        pricer = BondPricer()
        price_obj = clean_price if isinstance(clean_price, Price) else Price.new(clean_price, bond.currency())
        ytm = pricer.yield_to_maturity(bond, price_obj, settlement_date)

        ytm_pct = ytm.as_percentage()
        street = ytm_pct
        true = true_yield(street, Decimal(0))
        current = current_yield_from_bond_pct(bond, price_obj.as_percentage())
        coupon_amount = bond.coupon_rate() * Decimal(100)
        years = max(1e-8, float(settlement_date.days_between(bond.maturity_date())) / 365.0)
        simple = simple_yield(coupon_amount, price_obj.as_percentage(), Decimal(100), Decimal(str(years)))

        g_spread_bps = None
        z_spread_bps = None
        benchmark_spread_bps = None
        benchmark_tenor = None
        if self.government_curve is not None:
            maturity = bond.maturity_date()
            g_spread_bps = g_spread_with_benchmark_bps(
                ytm.value(),
                self.government_curve,
                maturity,
                benchmark=BenchmarkSpec.interpolated(),
            )
            benchmark_spec = self.benchmark or BenchmarkSpec.nearest()
            benchmark_spread_bps = g_spread_with_benchmark_bps(
                ytm.value(),
                self.government_curve,
                maturity,
                benchmark=benchmark_spec,
            )
            if benchmark_spec.kind is BenchmarkKind.TENOR:
                benchmark_tenor = benchmark_spec.tenor
            elif benchmark_spec.kind is BenchmarkKind.NEAREST:
                years = float(self.government_curve.reference_date.days_between(maturity)) / 365.0
                benchmark_tenor = self.government_curve.nearest_benchmark(years).tenor

        z_spread_bps = z_spread(bond, price_obj, self.curve, settlement_date) * Decimal(10_000)

        risk = BondRiskCalculator(bond=bond, ytm=ytm, settlement_date=settlement_date).all_metrics()

        invoice = SettlementInvoiceBuilder(
            settlement_date=settlement_date,
            clean_price=price_obj.as_percentage(),
            accrued_interest=bond.accrued_interest(settlement_date),
            face_value=bond.notional(),
            accrued_days=0,
        ).build()

        builder = YasAnalysisBuilder(
            ytm=ytm_pct,
            street_yield=street,
            true_yield=true,
            current_yield=current,
            simple_yield=simple,
            money_market_yield=None,
            g_spread_bps=g_spread_bps,
            z_spread_bps=z_spread_bps,
            benchmark_spread_bps=benchmark_spread_bps,
            benchmark_tenor=benchmark_tenor,
            risk=risk,
            invoice=invoice,
        )
        return builder.build()

    def validate_bloomberg(
        self,
        bond: Bond,
        clean_price: Price | Decimal,
        settlement_date: Date,
        reference: BloombergReference | None = None,
        *,
        tolerance: Decimal = Decimal("1.0"),
    ) -> list[ValidationFailure]:
        """Compare the calculated YAS output against a reference snapshot.

        Returns
        -------
        list[ValidationFailure]
            Field-level mismatches against the supplied reference values.
        """

        ref = reference or BloombergReference.boeing_2025()
        analysis = self.calculate(bond, clean_price, settlement_date)
        failures: list[ValidationFailure] = []

        def _check(field: str, expected: Decimal, actual: Decimal) -> None:
            if (actual - expected).copy_abs() > tolerance:
                failures.append(
                    ValidationFailure(
                        field=field,
                        expected=expected,
                        actual=actual,
                        tolerance=tolerance,
                    )
                )

        _check("ytm", ref.ytm, analysis.ytm)
        if analysis.g_spread_bps is not None:
            _check("g_spread_bps", ref.g_spread_bps, analysis.g_spread_bps)
        if analysis.z_spread_bps is not None:
            _check("z_spread_bps", ref.z_spread_bps, analysis.z_spread_bps)
        _check("modified_duration", ref.modified_duration, analysis.modified_duration())
        _check("convexity", ref.convexity, analysis.convexity())

        return failures


@dataclass(frozen=True, slots=True)
class BatchYASCalculator:
    """Apply a single YAS calculator across many bonds.

    Parameters
    ----------
    calculator:
        Shared calculator instance used for each bond-price pair.
    """

    calculator: YASCalculator

    def calculate_many(
        self,
        bonds: list[Bond],
        clean_prices: list[Price | Decimal],
        settlement_date: Date,
    ) -> list[YasAnalysis]:
        """Return YAS analyses for each bond-price pair in order."""

        if len(bonds) != len(clean_prices):
            raise AnalyticsError.invalid_input("bonds and clean_prices length mismatch.")
        return [
            self.calculator.calculate(bond, price, settlement_date)
            for bond, price in zip(bonds, clean_prices, strict=True)
        ]


__all__ = ["YASCalculator", "BatchYASCalculator"]
