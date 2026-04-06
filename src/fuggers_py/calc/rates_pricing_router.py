"""Rates-specific pricing router for calc-layer dispatch.

The router keeps rates products on their own pricing path so the engine can
reuse multicurve environments, DV01 helpers, and product-specific output
records without routing them through the bond router. It produces the routed
swap, FRA, basis-swap, and inflation-swap output records used by the calc
layer.
"""

from __future__ import annotations

from dataclasses import dataclass

from fuggers_py.calc.output import BasisSwapQuoteOutput, RoutedFraPricingResult, SwapQuoteOutput
from fuggers_py.calc.pricing_specs import AnalyticsCurves
from fuggers_py.products.rates import BasisSwap, FixedFloatSwap, Fra, Ois, StandardCouponInflationSwap, ZeroCouponInflationSwap
from fuggers_py.pricers.rates import BasisSwapPricer, FraPricer, InflationSwapPricer, StandardCouponInflationSwapPricingResult, SwapPricer
from fuggers_py.pricers.rates.risk import basis_swap_dv01, fra_dv01, swap_dv01


@dataclass(frozen=True, slots=True)
class RatesPricingRouter:
    """Price swaps, FRAs, basis swaps, and OIS instruments.

    All methods expect an already-assembled :class:`AnalyticsCurves` bundle and
    return typed output records with signed DV01 fields. ``pv01`` remains a
    compatibility alias on some output types.
    """

    def price_swap(self, instrument: FixedFloatSwap | Ois, *, curves: AnalyticsCurves) -> SwapQuoteOutput:
        """Price a swap-style instrument and attach signed DV01.

        The returned record keeps the par rate and leg PV split consistent with
        the shared swap pricer while adding the routed pricing-path label.
        """
        result = SwapPricer().price(instrument, curves)
        dv01 = swap_dv01(instrument, curves)
        return SwapQuoteOutput(
            instrument_id=instrument.instrument_id,
            pricing_path="ois" if isinstance(instrument, Ois) else "swap",
            par_rate=result.par_rate,
            present_value=result.present_value,
            fixed_leg_pv=result.fixed_leg_pv,
            floating_leg_pv=result.floating_leg_pv,
            annuity=result.annuity,
            dv01=dv01,
            pv01=dv01,
        )

    def price_fra(self, instrument: Fra, *, curves: AnalyticsCurves) -> RoutedFraPricingResult:
        """Price an FRA and return the routed FRA result record.

        The returned record keeps the forward rate, year fraction, discount
        factor, and sensitivity aliases aligned with the FRA pricer.
        """
        result = FraPricer().price(instrument, curves)
        dv01 = fra_dv01(instrument, curves)
        return RoutedFraPricingResult(
            instrument_id=instrument.instrument_id,
            pricing_path="fra",
            forward_rate=result.forward_rate,
            present_value=result.present_value,
            year_fraction=result.year_fraction,
            discount_factor=result.discount_factor,
            dv01=dv01,
            pv01=dv01,
        )

    def price_basis_swap(self, instrument: BasisSwap, *, curves: AnalyticsCurves) -> BasisSwapQuoteOutput:
        """Price a basis swap and attach signed DV01.

        The returned output carries the quoted basis spread together with the
        pay-leg and receive-leg PVs so callers can inspect the leg split.
        """
        result = BasisSwapPricer().price(instrument, curves)
        dv01 = basis_swap_dv01(instrument, curves)
        return BasisSwapQuoteOutput(
            instrument_id=instrument.instrument_id,
            pricing_path="basis_swap",
            basis_spread=result.par_spread,
            present_value=result.present_value,
            pay_leg_pv=result.pay_leg_pv,
            receive_leg_pv=result.receive_leg_pv,
            dv01=dv01,
            pv01=dv01,
        )

    def price_zero_coupon_inflation_swap(
        self,
        instrument: ZeroCouponInflationSwap,
        *,
        curves: AnalyticsCurves,
    ) -> SwapQuoteOutput:
        """Price a zero-coupon inflation swap.

        The inflation leg PV is preserved in the `floating_leg_pv` field and
        called out in the notes so the output remains readable downstream.
        """

        result = InflationSwapPricer().price(instrument, curves)
        return SwapQuoteOutput(
            instrument_id=instrument.instrument_id,
            pricing_path="zero_coupon_inflation_swap",
            par_rate=result.par_fixed_rate,
            present_value=result.present_value,
            fixed_leg_pv=result.fixed_leg_pv,
            floating_leg_pv=result.inflation_leg_pv,
            annuity=result.fixed_leg_annuity,
            dv01=result.pv01,
            pv01=result.pv01,
            notes=("floating_leg_pv is inflation leg PV",),
        )

    def price_standard_coupon_inflation_swap(
        self,
        instrument: StandardCouponInflationSwap,
        *,
        curves: AnalyticsCurves,
    ) -> SwapQuoteOutput:
        """Price a standard coupon inflation swap.

        The method expects the standard-coupon inflation result type and keeps
        the routed output aligned with the zero-coupon inflation path.
        """

        result = InflationSwapPricer().price(instrument, curves)
        if not isinstance(result, StandardCouponInflationSwapPricingResult):
            raise TypeError("Expected StandardCouponInflationSwapPricingResult for a standard coupon inflation swap.")
        return SwapQuoteOutput(
            instrument_id=instrument.instrument_id,
            pricing_path="standard_coupon_inflation_swap",
            par_rate=result.par_fixed_rate,
            present_value=result.present_value,
            fixed_leg_pv=result.fixed_leg_pv,
            floating_leg_pv=result.inflation_leg_pv,
            annuity=result.fixed_leg_annuity,
            dv01=result.pv01,
            pv01=result.pv01,
            notes=("floating_leg_pv is inflation leg PV",),
        )

    def price(self, instrument, *, curves: AnalyticsCurves):
        """Dispatch a rates instrument to the appropriate pricer.

        Unsupported instrument types raise :class:`TypeError` so callers can
        separate routing problems from pricing failures.
        """
        if isinstance(instrument, (FixedFloatSwap, Ois)):
            return self.price_swap(instrument, curves=curves)
        if isinstance(instrument, Fra):
            return self.price_fra(instrument, curves=curves)
        if isinstance(instrument, BasisSwap):
            return self.price_basis_swap(instrument, curves=curves)
        if isinstance(instrument, ZeroCouponInflationSwap):
            return self.price_zero_coupon_inflation_swap(instrument, curves=curves)
        if isinstance(instrument, StandardCouponInflationSwap):
            return self.price_standard_coupon_inflation_swap(instrument, curves=curves)
        raise TypeError(f"Unsupported rates instrument type: {type(instrument).__name__}.")

    def price_batch(self, instruments: list[object] | tuple[object, ...], *, curves: AnalyticsCurves) -> tuple[object, ...]:
        """Price a batch of rates instruments using a shared curve bundle.

        Every instrument sees the same curve bundle so batch pricing remains
        deterministic across the routed rates products.
        """
        return tuple(self.price(instrument, curves=curves) for instrument in instruments)


__all__ = ["RatesPricingRouter", "RoutedFraPricingResult"]
