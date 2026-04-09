"""Inflation swap pricing helpers."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol, runtime_checkable

from fuggers_py.core.types import Date
from fuggers_py.market.curves.term_structure import TermStructure
from fuggers_py.market.state import AnalyticsCurves
from fuggers_py.reference.inflation.reference_index import reference_cpi
from fuggers_py.products.rates import StandardCouponInflationSwap, ZeroCouponInflationSwap

from ._curve_resolver import resolve_discount_curve, resolve_inflation_projection


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


@runtime_checkable
class InflationProjection(Protocol):
    """Shared interface for direct reference-index forecasts."""

    def reference_cpi(self, date: Date, convention) -> Decimal:
        """Return the projected daily reference CPI for ``date``."""
        ...


@dataclass(frozen=True, slots=True)
class ZeroCouponInflationSwapPricingResult:
    """Pricing decomposition for a zero-coupon inflation swap."""

    par_fixed_rate: Decimal
    present_value: Decimal
    fixed_leg_pv: Decimal
    inflation_leg_pv: Decimal
    pv01: Decimal
    index_initial: Decimal
    index_final: Decimal
    payment_date: Date
    discount_factor: Decimal
    fixed_leg_annuity: Decimal


@dataclass(frozen=True, slots=True)
class StandardCouponInflationSwapPeriodPricing:
    """Per-period pricing breakdown for a standard coupon inflation swap."""

    start_date: Date
    end_date: Date
    payment_date: Date
    year_fraction: Decimal
    index_initial: Decimal
    index_final: Decimal
    inflation_rate: Decimal
    fixed_cashflow: Decimal
    inflation_cashflow: Decimal
    discount_factor: Decimal
    fixed_leg_pv: Decimal
    inflation_leg_pv: Decimal

    def __post_init__(self) -> None:
        for field_name in (
            "year_fraction",
            "index_initial",
            "index_final",
            "inflation_rate",
            "fixed_cashflow",
            "inflation_cashflow",
            "discount_factor",
            "fixed_leg_pv",
            "inflation_leg_pv",
        ):
            object.__setattr__(self, field_name, _to_decimal(getattr(self, field_name)))


@dataclass(frozen=True, slots=True)
class StandardCouponInflationSwapPricingResult:
    """Pricing decomposition for a standard coupon inflation swap."""

    par_fixed_rate: Decimal
    present_value: Decimal
    fixed_leg_pv: Decimal
    inflation_leg_pv: Decimal
    pv01: Decimal
    fixed_leg_annuity: Decimal
    periods: tuple[StandardCouponInflationSwapPeriodPricing, ...]

    def __post_init__(self) -> None:
        for field_name in (
            "par_fixed_rate",
            "present_value",
            "fixed_leg_pv",
            "inflation_leg_pv",
            "pv01",
            "fixed_leg_annuity",
        ):
            object.__setattr__(self, field_name, _to_decimal(getattr(self, field_name)))
        object.__setattr__(self, "periods", tuple(self.periods))


InflationSwapPricingResult = ZeroCouponInflationSwapPricingResult | StandardCouponInflationSwapPricingResult
InflationSwapInstrument = ZeroCouponInflationSwap | StandardCouponInflationSwap


@dataclass(frozen=True, slots=True)
class InflationSwapPricer:
    """Price zero-coupon and standard coupon inflation swaps."""

    def fixed_leg_pv(
        self,
        swap: InflationSwapInstrument,
        curves: AnalyticsCurves | None = None,
        *,
        discount_curve: TermStructure | None = None,
    ) -> Decimal:
        """Return the discounted PV of the fixed leg."""

        if isinstance(swap, StandardCouponInflationSwap):
            return self._standard_coupon_fixed_leg_pv(swap, curves, discount_curve=discount_curve)
        return self._zero_coupon_fixed_leg_pv(swap, curves, discount_curve=discount_curve)

    def inflation_leg_pv(
        self,
        swap: InflationSwapInstrument,
        curves: AnalyticsCurves | None = None,
        *,
        discount_curve: TermStructure | None = None,
        inflation_projection: object | None = None,
    ) -> Decimal:
        """Return the discounted PV of the inflation leg."""

        if isinstance(swap, StandardCouponInflationSwap):
            return self._standard_coupon_inflation_leg_pv(
                swap,
                curves,
                discount_curve=discount_curve,
                inflation_projection=inflation_projection,
            )
        return self._zero_coupon_inflation_leg_pv(
            swap,
            curves,
            discount_curve=discount_curve,
            inflation_projection=inflation_projection,
        )

    def pv(
        self,
        swap: InflationSwapInstrument,
        curves: AnalyticsCurves | None = None,
        *,
        discount_curve: TermStructure | None = None,
        inflation_projection: object | None = None,
    ) -> Decimal:
        """Return the total present value of the swap."""

        return self.fixed_leg_pv(
            swap,
            curves,
            discount_curve=discount_curve,
        ) + self.inflation_leg_pv(
            swap,
            curves,
            discount_curve=discount_curve,
            inflation_projection=inflation_projection,
        )

    def par_fixed_rate(
        self,
        swap: InflationSwapInstrument,
        curves: AnalyticsCurves | None = None,
        *,
        discount_curve: TermStructure | None = None,
        inflation_projection: object | None = None,
    ) -> Decimal:
        """Return the fixed rate that zeros the swap PV."""

        annuity = self.fixed_leg_annuity(swap, curves, discount_curve=discount_curve)
        inflation_leg_pv = self.inflation_leg_pv(
            swap,
            curves,
            discount_curve=discount_curve,
            inflation_projection=inflation_projection,
        )
        return -inflation_leg_pv / (swap.fixed_leg_sign() * annuity)

    def pv01(
        self,
        swap: InflationSwapInstrument,
        curves: AnalyticsCurves | None = None,
        *,
        discount_curve: TermStructure | None = None,
        bump: object = Decimal("0.0001"),
    ) -> Decimal:
        """Return the fixed-rate PV change per one basis point."""

        return swap.fixed_leg_sign() * self.fixed_leg_annuity(
            swap,
            curves,
            discount_curve=discount_curve,
        ) * _to_decimal(bump)

    def fixed_leg_annuity(
        self,
        swap: InflationSwapInstrument,
        curves: AnalyticsCurves | None = None,
        *,
        discount_curve: TermStructure | None = None,
    ) -> Decimal:
        """Return the discounted fixed-leg accrual amount per unit rate."""

        if isinstance(swap, StandardCouponInflationSwap):
            curve = self._resolve_discount_curve(swap, curves, discount_curve)
            total = Decimal(0)
            for period in swap.fixed_periods():
                total += swap.notional * period.year_fraction * curve.discount_factor(period.payment_date)
            return total
        curve = self._resolve_discount_curve(swap, curves, discount_curve)
        return swap.notional * swap.fixed_leg_year_fraction() * curve.discount_factor(swap.payment_date())

    def reference_cpi(
        self,
        swap: InflationSwapInstrument,
        date: Date,
        *,
        curves: AnalyticsCurves | None = None,
        inflation_projection: object | None = None,
    ) -> Decimal:
        """Return the projected daily reference CPI for ``date``."""

        projection = self._resolve_inflation_projection(
            swap,
            curves=curves,
            inflation_projection=inflation_projection,
        )
        if hasattr(projection, "projected_reference_cpi"):
            return _to_decimal(projection.projected_reference_cpi(date))
        if hasattr(projection, "reference_cpi"):
            return _to_decimal(projection.reference_cpi(date, swap.inflation_convention))
        if hasattr(projection, "get_reference_cpi"):
            return _to_decimal(projection.get_reference_cpi(date, swap.inflation_convention))
        return reference_cpi(date, swap.inflation_convention, projection)

    def price(
        self,
        swap: InflationSwapInstrument,
        curves: AnalyticsCurves | None = None,
        *,
        discount_curve: TermStructure | None = None,
        inflation_projection: object | None = None,
    ) -> InflationSwapPricingResult:
        """Return the full pricing decomposition."""

        if isinstance(swap, StandardCouponInflationSwap):
            return self._price_standard_coupon(
                swap,
                curves,
                discount_curve=discount_curve,
                inflation_projection=inflation_projection,
            )
        return self._price_zero_coupon(
            swap,
            curves,
            discount_curve=discount_curve,
            inflation_projection=inflation_projection,
        )

    def _zero_coupon_fixed_leg_pv(
        self,
        swap: ZeroCouponInflationSwap,
        curves: AnalyticsCurves | None = None,
        *,
        discount_curve: TermStructure | None = None,
    ) -> Decimal:
        curve = self._resolve_discount_curve(swap, curves, discount_curve)
        return (
            swap.fixed_leg_sign()
            * swap.notional
            * swap.fixed_rate
            * swap.fixed_leg_year_fraction()
            * curve.discount_factor(swap.payment_date())
        )

    def _zero_coupon_inflation_leg_pv(
        self,
        swap: ZeroCouponInflationSwap,
        curves: AnalyticsCurves | None = None,
        *,
        discount_curve: TermStructure | None = None,
        inflation_projection: object | None = None,
    ) -> Decimal:
        curve = self._resolve_discount_curve(swap, curves, discount_curve)
        index_initial = self.reference_cpi(
            swap,
            swap.index_initial_date(),
            curves=curves,
            inflation_projection=inflation_projection,
        )
        index_final = self.reference_cpi(
            swap,
            swap.index_final_date(),
            curves=curves,
            inflation_projection=inflation_projection,
        )
        payoff = (index_final / index_initial) - Decimal(1)
        return swap.inflation_leg_sign() * swap.notional * payoff * curve.discount_factor(swap.payment_date())

    def _price_zero_coupon(
        self,
        swap: ZeroCouponInflationSwap,
        curves: AnalyticsCurves | None = None,
        *,
        discount_curve: TermStructure | None = None,
        inflation_projection: object | None = None,
    ) -> ZeroCouponInflationSwapPricingResult:
        curve = self._resolve_discount_curve(swap, curves, discount_curve)
        index_initial = self.reference_cpi(
            swap,
            swap.index_initial_date(),
            curves=curves,
            inflation_projection=inflation_projection,
        )
        index_final = self.reference_cpi(
            swap,
            swap.index_final_date(),
            curves=curves,
            inflation_projection=inflation_projection,
        )
        fixed_leg_annuity = self.fixed_leg_annuity(swap, curves, discount_curve=curve)
        fixed_leg_pv = swap.fixed_leg_sign() * fixed_leg_annuity * swap.fixed_rate
        inflation_leg_pv = (
            swap.inflation_leg_sign()
            * swap.notional
            * ((index_final / index_initial) - Decimal(1))
            * curve.discount_factor(swap.payment_date())
        )
        return ZeroCouponInflationSwapPricingResult(
            par_fixed_rate=-inflation_leg_pv / (swap.fixed_leg_sign() * fixed_leg_annuity),
            present_value=fixed_leg_pv + inflation_leg_pv,
            fixed_leg_pv=fixed_leg_pv,
            inflation_leg_pv=inflation_leg_pv,
            pv01=swap.fixed_leg_sign() * fixed_leg_annuity * Decimal("0.0001"),
            index_initial=index_initial,
            index_final=index_final,
            payment_date=swap.payment_date(),
            discount_factor=curve.discount_factor(swap.payment_date()),
            fixed_leg_annuity=fixed_leg_annuity,
        )

    def _standard_coupon_period_pricings(
        self,
        swap: StandardCouponInflationSwap,
        curves: AnalyticsCurves | None = None,
        *,
        discount_curve: TermStructure | None = None,
        inflation_projection: object | None = None,
    ) -> tuple[StandardCouponInflationSwapPeriodPricing, ...]:
        curve = self._resolve_discount_curve(swap, curves, discount_curve)
        periods: list[StandardCouponInflationSwapPeriodPricing] = []
        for fixed_period, inflation_period in zip(swap.fixed_periods(), swap.inflation_periods(), strict=True):
            index_initial = self.reference_cpi(
                swap,
                inflation_period.start_date,
                curves=curves,
                inflation_projection=inflation_projection,
            )
            index_final = self.reference_cpi(
                swap,
                inflation_period.end_date,
                curves=curves,
                inflation_projection=inflation_projection,
            )
            inflation_rate = (index_final / index_initial) - Decimal(1)
            fixed_cashflow = swap.notional * swap.fixed_rate * fixed_period.year_fraction
            inflation_cashflow = swap.notional * inflation_rate
            discount_factor = curve.discount_factor(fixed_period.payment_date)
            periods.append(
                StandardCouponInflationSwapPeriodPricing(
                    start_date=fixed_period.start_date,
                    end_date=fixed_period.end_date,
                    payment_date=fixed_period.payment_date,
                    year_fraction=fixed_period.year_fraction,
                    index_initial=index_initial,
                    index_final=index_final,
                    inflation_rate=inflation_rate,
                    fixed_cashflow=fixed_cashflow,
                    inflation_cashflow=inflation_cashflow,
                    discount_factor=discount_factor,
                    fixed_leg_pv=swap.fixed_leg_sign() * fixed_cashflow * discount_factor,
                    inflation_leg_pv=swap.inflation_leg_sign() * inflation_cashflow * discount_factor,
                )
            )
        return tuple(periods)

    def _standard_coupon_fixed_leg_pv(
        self,
        swap: StandardCouponInflationSwap,
        curves: AnalyticsCurves | None = None,
        *,
        discount_curve: TermStructure | None = None,
    ) -> Decimal:
        fixed_leg_annuity = self.fixed_leg_annuity(swap, curves, discount_curve=discount_curve)
        return swap.fixed_leg_sign() * fixed_leg_annuity * swap.fixed_rate

    def _standard_coupon_inflation_leg_pv(
        self,
        swap: StandardCouponInflationSwap,
        curves: AnalyticsCurves | None = None,
        *,
        discount_curve: TermStructure | None = None,
        inflation_projection: object | None = None,
    ) -> Decimal:
        return sum(
            period.inflation_leg_pv
            for period in self._standard_coupon_period_pricings(
                swap,
                curves,
                discount_curve=discount_curve,
                inflation_projection=inflation_projection,
            )
        )

    def _price_standard_coupon(
        self,
        swap: StandardCouponInflationSwap,
        curves: AnalyticsCurves | None = None,
        *,
        discount_curve: TermStructure | None = None,
        inflation_projection: object | None = None,
    ) -> StandardCouponInflationSwapPricingResult:
        periods = self._standard_coupon_period_pricings(
            swap,
            curves,
            discount_curve=discount_curve,
            inflation_projection=inflation_projection,
        )
        fixed_leg_annuity = self.fixed_leg_annuity(swap, curves, discount_curve=discount_curve)
        fixed_leg_pv = swap.fixed_leg_sign() * fixed_leg_annuity * swap.fixed_rate
        inflation_leg_pv = sum(period.inflation_leg_pv for period in periods)
        return StandardCouponInflationSwapPricingResult(
            par_fixed_rate=-inflation_leg_pv / (swap.fixed_leg_sign() * fixed_leg_annuity),
            present_value=fixed_leg_pv + inflation_leg_pv,
            fixed_leg_pv=fixed_leg_pv,
            inflation_leg_pv=inflation_leg_pv,
            pv01=swap.fixed_leg_sign() * fixed_leg_annuity * Decimal("0.0001"),
            fixed_leg_annuity=fixed_leg_annuity,
            periods=periods,
        )

    @staticmethod
    def _resolve_discount_curve(
        swap: InflationSwapInstrument,
        curves: AnalyticsCurves | None,
        discount_curve: TermStructure | None,
    ) -> TermStructure:
        if discount_curve is not None:
            return discount_curve
        if curves is None:
            raise ValueError("Inflation swap pricing requires a nominal discount curve or AnalyticsCurves bundle.")
        return resolve_discount_curve(curves, swap.currency)

    @staticmethod
    def _resolve_inflation_projection(
        swap: InflationSwapInstrument,
        *,
        curves: AnalyticsCurves | None,
        inflation_projection: object | None,
    ) -> object:
        if inflation_projection is not None:
            return inflation_projection
        if curves is None:
            raise ValueError("Inflation swap pricing requires an inflation projection or fixing source.")
        return resolve_inflation_projection(curves, convention=swap.inflation_convention)


__all__ = [
    "InflationProjection",
    "InflationSwapInstrument",
    "InflationSwapPricer",
    "InflationSwapPricingResult",
    "StandardCouponInflationSwapPeriodPricing",
    "StandardCouponInflationSwapPricingResult",
    "ZeroCouponInflationSwapPricingResult",
]
