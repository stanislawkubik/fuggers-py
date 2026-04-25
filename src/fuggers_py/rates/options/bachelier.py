"""Bachelier option pricing for rates options.

This pricer treats the underlying as an additive forward process and expects
normal-volatility quotes. Outputs are currency-valued present values with
greeks scaled to the contract multiplier or swap annuity.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from math import exp, log, sqrt

from fuggers_py._core import OptionType
from fuggers_py.vol_surfaces import VolQuoteType, VolatilitySurface

from ._pricing_common import (
    CapFloorPricingResult,
    CapFloorletPricingResult,
    FuturesOptionPricingResult,
    OptionFormulaResult,
    OptionGreeks,
    SwaptionPricingResult,
    _normal_cdf,
    _normal_pdf,
    _resolve_surface_volatility,
    _scale_greeks,
    _sum_greeks,
    _time_to_expiry,
    _to_decimal,
    cap_floor_context,
    futures_option_context,
    swaption_context,
    swaption_option_type,
)
from .cap_floor import CapFloor
from .futures_option import FuturesOption
from .swaption import Swaption


def _intrinsic_value(forward: Decimal, strike: Decimal, option_type: OptionType) -> Decimal:
    """Return the intrinsic value in forward-rate units."""
    if option_type is OptionType.CALL:
        return max(forward - strike, Decimal(0))
    return max(strike - forward, Decimal(0))


def _bachelier_price(
    *,
    forward: float,
    strike: float,
    volatility: float,
    expiry_years: float,
    option_type: OptionType,
    discount_factor: float,
) -> float:
    """Return the discounted Bachelier price in floating-point arithmetic."""
    if expiry_years <= 0.0 or volatility <= 0.0:
        intrinsic = max(forward - strike, 0.0) if option_type is OptionType.CALL else max(strike - forward, 0.0)
        return discount_factor * intrinsic
    standard_deviation = volatility * sqrt(expiry_years)
    d = (forward - strike) / standard_deviation
    sign = 1.0 if option_type is OptionType.CALL else -1.0
    return discount_factor * (sign * (forward - strike) * _normal_cdf(sign * d) + standard_deviation * _normal_pdf(d))


def bachelier_formula(
    *,
    forward: object,
    strike: object,
    volatility: object,
    expiry_years: object,
    option_type: OptionType | str,
    discount_factor: object = Decimal(1),
) -> OptionFormulaResult:
    """Price a call or put with the Bachelier formula.

    Parameters
    ----------
    forward, strike
        Forward and strike in the same additive units.
    volatility
        Raw-decimal normal volatility, for example ``0.01`` for 1% absolute
        rate volatility.
    expiry_years
        Time to expiry in ACT/365 years.
    discount_factor
        Discount factor to valuation.

    Returns
    -------
    OptionFormulaResult
        Discounted option value, intrinsic value, time value, and greeks in
        the Bachelier convention.

    Raises
    ------
    ValueError
        If the discount factor is non-positive or the volatility is negative.
    """
    resolved_option_type = OptionType.parse(option_type)
    resolved_forward = _to_decimal(forward)
    resolved_strike = _to_decimal(strike)
    resolved_volatility = _to_decimal(volatility)
    resolved_expiry_years = _to_decimal(expiry_years)
    resolved_discount_factor = _to_decimal(discount_factor)

    if resolved_discount_factor <= Decimal(0):
        raise ValueError("bachelier_formula requires a positive discount_factor.")
    if resolved_volatility < Decimal(0):
        raise ValueError("bachelier_formula requires a non-negative volatility.")

    intrinsic = resolved_discount_factor * _intrinsic_value(resolved_forward, resolved_strike, resolved_option_type)
    if resolved_expiry_years == Decimal(0) or resolved_volatility == Decimal(0):
        delta = resolved_discount_factor if intrinsic > Decimal(0) and resolved_option_type is OptionType.CALL else Decimal(0)
        if intrinsic > Decimal(0) and resolved_option_type is OptionType.PUT:
            delta = -resolved_discount_factor
        return OptionFormulaResult(
            option_type=resolved_option_type,
            forward=resolved_forward,
            strike=resolved_strike,
            volatility=resolved_volatility,
            expiry_years=resolved_expiry_years,
            discount_factor=resolved_discount_factor,
            present_value=intrinsic,
            intrinsic_value=intrinsic,
            time_value=Decimal(0),
            greeks=OptionGreeks(delta=delta),
        )

    forward_float = float(resolved_forward)
    strike_float = float(resolved_strike)
    volatility_float = float(resolved_volatility)
    expiry_float = float(resolved_expiry_years)
    discount_float = float(resolved_discount_factor)
    standard_deviation = volatility_float * sqrt(expiry_float)
    d = (forward_float - strike_float) / standard_deviation
    pdf_d = _normal_pdf(d)
    price = _bachelier_price(
        forward=forward_float,
        strike=strike_float,
        volatility=volatility_float,
        expiry_years=expiry_float,
        option_type=resolved_option_type,
        discount_factor=discount_float,
    )
    if resolved_option_type is OptionType.CALL:
        delta = discount_float * _normal_cdf(d)
    else:
        delta = -discount_float * _normal_cdf(-d)
    gamma = discount_float * pdf_d / standard_deviation
    vega = discount_float * sqrt(expiry_float) * pdf_d

    time_bump = min(expiry_float / 2.0, 1.0 / 365.0) or 1.0 / 365.0
    shorter_time = max(expiry_float - time_bump, 0.0)
    longer_time = expiry_float + time_bump
    theta = -(
        _bachelier_price(
            forward=forward_float,
            strike=strike_float,
            volatility=volatility_float,
            expiry_years=longer_time,
            option_type=resolved_option_type,
            discount_factor=discount_float,
        )
        - _bachelier_price(
            forward=forward_float,
            strike=strike_float,
            volatility=volatility_float,
            expiry_years=shorter_time,
            option_type=resolved_option_type,
            discount_factor=discount_float,
        )
    ) / (longer_time - shorter_time)
    rate = -log(discount_float) / expiry_float
    rate_bump = 0.0001
    bumped_discount = exp(-(rate + rate_bump) * expiry_float)
    bumped_price = _bachelier_price(
        forward=forward_float,
        strike=strike_float,
        volatility=volatility_float,
        expiry_years=expiry_float,
        option_type=resolved_option_type,
        discount_factor=bumped_discount,
    )
    rho = (bumped_price - price) / rate_bump

    present_value = Decimal(str(price))
    return OptionFormulaResult(
        option_type=resolved_option_type,
        forward=resolved_forward,
        strike=resolved_strike,
        volatility=resolved_volatility,
        expiry_years=resolved_expiry_years,
        discount_factor=resolved_discount_factor,
        present_value=present_value,
        intrinsic_value=intrinsic,
        time_value=present_value - intrinsic,
        greeks=OptionGreeks(
            delta=Decimal(str(delta)),
            gamma=Decimal(str(gamma)),
            vega=Decimal(str(vega)),
            theta=Decimal(str(theta)),
            rho=Decimal(str(rho)),
        ),
    )


@dataclass(frozen=True, slots=True)
class BachelierPricer:
    """Bachelier pricer for rates options.

    The pricer assumes additive forward dynamics and uses normal volatility
    quotes for swaption, cap/floor, and futures-option valuation.
    """

    def formula(
        self,
        *,
        forward: object,
        strike: object,
        volatility: object,
        expiry_years: object,
        option_type: OptionType | str,
        discount_factor: object = Decimal(1),
    ) -> OptionFormulaResult:
        """Proxy to :func:`bachelier_formula`.

        The formula works in additive units and returns a currency-scaled
        present value plus greeks in the same scaling.
        """
        return bachelier_formula(
            forward=forward,
            strike=strike,
            volatility=volatility,
            expiry_years=expiry_years,
            option_type=option_type,
            discount_factor=discount_factor,
        )

    def swaption(
        self,
        swaption: Swaption,
        curves: object,
        *,
        volatility: object | None = None,
        vol_surface: VolatilitySurface | None = None,
        valuation_date=None,
        swap_pricer=None,
    ) -> SwaptionPricingResult:
        """Price a swaption using normal-volatility quotes.

        The result is scaled by the swap annuity and uses either an explicit
        volatility quote or the matched surface quote.
        """
        forward_rate, annuity, resolved_valuation_date = swaption_context(
            swaption,
            curves,
            valuation_date=valuation_date,
            swap_pricer=swap_pricer,
        )
        expiry_years = _time_to_expiry(swaption.expiry_date, resolved_valuation_date)
        resolved_volatility = _resolve_surface_volatility(
            curves,
            expiry_date=swaption.expiry_date,
            tenor_date=swaption.underlying_swap.maturity_date,
            strike=swaption.strike,
            quote_type=VolQuoteType.NORMAL,
            vol_surface=vol_surface,
            explicit_volatility=volatility,
        )
        formula = self.formula(
            forward=forward_rate,
            strike=swaption.strike,
            volatility=resolved_volatility,
            expiry_years=expiry_years,
            option_type=swaption_option_type(swaption),
        )
        return SwaptionPricingResult(
            forward_rate=forward_rate,
            strike=swaption.strike,
            annuity=annuity,
            volatility=resolved_volatility,
            expiry_years=expiry_years,
            present_value=annuity * formula.present_value,
            greeks=_scale_greeks(formula.greeks, annuity),
        )

    def cap_floor(
        self,
        cap_floor: CapFloor,
        curves: object,
        *,
        volatility: object | None = None,
        vol_surface: VolatilitySurface | None = None,
        valuation_date=None,
    ) -> CapFloorPricingResult:
        """Price a cap or floor by summing Bachelier optionlets."""
        optionlet_inputs, _ = cap_floor_context(cap_floor, curves, valuation_date=valuation_date)
        optionlets: list[CapFloorletPricingResult] = []
        greeks: list[OptionGreeks] = []
        present_value = Decimal(0)
        for optionlet_input in optionlet_inputs:
            resolved_volatility = _resolve_surface_volatility(
                curves,
                expiry_date=optionlet_input.start_date,
                tenor_date=optionlet_input.end_date,
                strike=cap_floor.strike,
                quote_type=VolQuoteType.NORMAL,
                vol_surface=vol_surface,
                explicit_volatility=volatility,
            )
            formula = self.formula(
                forward=optionlet_input.forward_rate,
                strike=cap_floor.strike,
                volatility=resolved_volatility,
                expiry_years=optionlet_input.expiry_years,
                option_type=cap_floor.option_type(),
                discount_factor=optionlet_input.discount_factor,
            )
            scale = cap_floor.floating_leg.notional * optionlet_input.accrual_factor
            optionlet_result = CapFloorletPricingResult(
                start_date=optionlet_input.start_date,
                end_date=optionlet_input.end_date,
                payment_date=optionlet_input.payment_date,
                forward_rate=optionlet_input.forward_rate,
                strike=cap_floor.strike,
                volatility=resolved_volatility,
                expiry_years=optionlet_input.expiry_years,
                accrual_factor=optionlet_input.accrual_factor,
                discount_factor=optionlet_input.discount_factor,
                present_value=scale * formula.present_value,
                greeks=_scale_greeks(formula.greeks, scale),
            )
            optionlets.append(optionlet_result)
            greeks.append(optionlet_result.greeks)
            present_value += optionlet_result.present_value
        return CapFloorPricingResult(
            present_value=present_value,
            optionlets=tuple(optionlets),
            greeks=_sum_greeks(greeks),
        )

    def futures_option(
        self,
        option: FuturesOption,
        *,
        curves: object | None = None,
        futures_price: object | None = None,
        basket=None,
        delivery_option_model=None,
        volatility: object | None = None,
        vol_surface: VolatilitySurface | None = None,
        valuation_date=None,
    ) -> FuturesOptionPricingResult:
        """Price a futures option using the futures quote as the forward."""
        resolved_futures_price, delivery_adjustment, discount_factor, resolved_valuation_date = futures_option_context(
            option,
            curves=curves,
            valuation_date=valuation_date,
            futures_price=futures_price,
            basket=basket,
            delivery_option_model=delivery_option_model,
        )
        expiry_years = _time_to_expiry(option.expiry_date, resolved_valuation_date)
        resolved_volatility = _resolve_surface_volatility(
            curves,
            expiry_date=option.expiry_date,
            tenor_date=option.underlying_future.resolved_delivery_date(),
            strike=option.strike,
            quote_type=VolQuoteType.NORMAL,
            vol_surface=vol_surface,
            explicit_volatility=volatility,
        )
        formula = self.formula(
            forward=resolved_futures_price,
            strike=option.strike,
            volatility=resolved_volatility,
            expiry_years=expiry_years,
            option_type=option.option_type,
            discount_factor=discount_factor,
        )
        contract_multiplier = option.contract_multiplier()
        return FuturesOptionPricingResult(
            futures_price=resolved_futures_price,
            strike=option.strike,
            volatility=resolved_volatility,
            expiry_years=expiry_years,
            contract_multiplier=contract_multiplier,
            discount_factor=discount_factor,
            delivery_option_adjustment=delivery_adjustment,
            present_value=contract_multiplier * formula.present_value,
            greeks=_scale_greeks(formula.greeks, contract_multiplier),
        )


__all__ = ["BachelierPricer", "bachelier_formula"]
