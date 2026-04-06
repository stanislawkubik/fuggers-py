"""Transparent Hull-White style approximations for rates options.

The implementation is intentionally lightweight: it converts externally
supplied mean reversion and volatility parameters into an approximate normal
volatility before delegating to the Bachelier pricer. It is not a calibration
or tree engine.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from math import exp, sqrt

from fuggers_py.market.state import AnalyticsCurves
from fuggers_py.pricers.rates._curve_resolver import resolve_discount_curve

from fuggers_py.products.rates.options import CapFloor, Swaption
from ._common import CapFloorPricingResult, OptionGreeks, SwaptionPricingResult, _time_to_expiry, _to_decimal
from .bachelier import BachelierPricer


def hull_white_normal_volatility(
    *,
    mean_reversion: object,
    volatility: object,
    expiry_years: object,
    underlying_tenor_years: object,
) -> Decimal:
    """Convert Hull-White parameters into an approximate normal volatility.

    The proxy maps mean reversion and model volatility into an equivalent
    normal-volatility quote for the supplied option expiry and underlying tenor.
    """
    resolved_mean_reversion = _to_decimal(mean_reversion)
    resolved_volatility = _to_decimal(volatility)
    resolved_expiry_years = _to_decimal(expiry_years)
    resolved_underlying_tenor_years = _to_decimal(underlying_tenor_years)
    if resolved_mean_reversion < Decimal(0):
        raise ValueError("Hull-White mean_reversion must be non-negative.")
    if resolved_volatility < Decimal(0):
        raise ValueError("Hull-White volatility must be non-negative.")
    if resolved_expiry_years == Decimal(0) or resolved_volatility == Decimal(0):
        return Decimal(0)

    a = float(resolved_mean_reversion)
    sigma = float(resolved_volatility)
    expiry = float(resolved_expiry_years)
    underlying_tenor = max(float(resolved_underlying_tenor_years), 1e-12)
    if a == 0.0:
        return Decimal(str(sigma * sqrt(expiry)))

    time_factor = sqrt((1.0 - exp(-2.0 * a * expiry)) / (2.0 * a))
    tenor_factor = (1.0 - exp(-a * underlying_tenor)) / (a * underlying_tenor)
    return Decimal(str(sigma * time_factor * tenor_factor))


@dataclass(frozen=True, slots=True)
class HullWhiteRateOptionModel:
    """Mean-reversion and volatility parameters for the Hull-White proxy.

    The model does not calibrate itself; it only stores the proxy parameters
    used to derive an approximate normal volatility.
    """

    mean_reversion: Decimal
    volatility: Decimal

    def __post_init__(self) -> None:
        object.__setattr__(self, "mean_reversion", _to_decimal(self.mean_reversion))
        object.__setattr__(self, "volatility", _to_decimal(self.volatility))
        if self.mean_reversion < Decimal(0):
            raise ValueError("HullWhiteRateOptionModel mean_reversion must be non-negative.")
        if self.volatility < Decimal(0):
            raise ValueError("HullWhiteRateOptionModel volatility must be non-negative.")

    def normal_volatility(self, *, expiry_years: object, underlying_tenor_years: object) -> Decimal:
        """Return the approximate normal volatility for the supplied tenor."""
        return hull_white_normal_volatility(
            mean_reversion=self.mean_reversion,
            volatility=self.volatility,
            expiry_years=expiry_years,
            underlying_tenor_years=underlying_tenor_years,
        )


@dataclass(frozen=True, slots=True)
class HullWhiteOptionPricer:
    """Hull-White style pricer that delegates to the Bachelier engine.

    The class converts Hull-White proxy parameters into a normal-volatility
    quote and then prices through the Bachelier pricer.
    """

    model: HullWhiteRateOptionModel
    bachelier_pricer: BachelierPricer = BachelierPricer()

    def swaption(
        self,
        swaption: Swaption,
        curves: AnalyticsCurves,
        *,
        valuation_date=None,
        swap_pricer=None,
    ) -> SwaptionPricingResult:
        """Price a swaption using the Hull-White normal-volatility proxy."""
        resolved_valuation_date = valuation_date or resolve_discount_curve(curves, swaption.currency()).reference_date()
        expiry_years = _time_to_expiry(swaption.expiry_date, resolved_valuation_date)
        underlying_tenor_years = _time_to_expiry(
            swaption.underlying_swap.effective_date,
            swaption.underlying_swap.maturity_date,
        )
        normal_volatility = self.model.normal_volatility(
            expiry_years=expiry_years,
            underlying_tenor_years=underlying_tenor_years,
        )
        return self.bachelier_pricer.swaption(
            swaption,
            curves,
            volatility=normal_volatility,
            valuation_date=resolved_valuation_date,
            swap_pricer=swap_pricer,
        )

    def cap_floor(
        self,
        cap_floor: CapFloor,
        curves: AnalyticsCurves,
        *,
        valuation_date=None,
    ) -> CapFloorPricingResult:
        """Price a cap or floor using the Hull-White normal-volatility proxy."""
        resolved_valuation_date = valuation_date or resolve_discount_curve(curves, cap_floor.currency()).reference_date()
        optionlets = []
        for period in cap_floor.optionlet_periods():
            expiry_years = _time_to_expiry(period.start_date, resolved_valuation_date)
            optionlets.append(
                self.model.normal_volatility(
                    expiry_years=expiry_years,
                    underlying_tenor_years=period.year_fraction,
                )
            )
        if not optionlets:
            return CapFloorPricingResult(present_value=Decimal(0), optionlets=(), greeks=OptionGreeks())
        average_volatility = sum(optionlets, start=Decimal(0)) / Decimal(len(optionlets))
        return self.bachelier_pricer.cap_floor(
            cap_floor,
            curves,
            volatility=average_volatility,
            valuation_date=resolved_valuation_date,
        )


__all__ = ["HullWhiteOptionPricer", "HullWhiteRateOptionModel", "hull_white_normal_volatility"]
