"""Black-76 option pricing for rates options.

This pricer treats the underlying as a strictly positive forward and expects
lognormal volatility quotes. It returns currency-valued present values and
greeks scaled to the relevant contract multiplier or swap annuity.
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
    """Return the intrinsic value in forward-price units."""
    if option_type is OptionType.CALL:
        return max(forward - strike, Decimal(0))
    return max(strike - forward, Decimal(0))


def _black76_price(
    *,
    forward: float,
    strike: float,
    volatility: float,
    expiry_years: float,
    option_type: OptionType,
    discount_factor: float,
) -> float:
    """Return the discounted Black-76 price in floating-point arithmetic."""
    if expiry_years <= 0.0 or volatility <= 0.0:
        intrinsic = max(forward - strike, 0.0) if option_type is OptionType.CALL else max(strike - forward, 0.0)
        return discount_factor * intrinsic
    volatility_time = volatility * sqrt(expiry_years)
    d1 = (log(forward / strike) + 0.5 * volatility * volatility * expiry_years) / volatility_time
    d2 = d1 - volatility_time
    if option_type is OptionType.CALL:
        return discount_factor * (forward * _normal_cdf(d1) - strike * _normal_cdf(d2))
    return discount_factor * (strike * _normal_cdf(-d2) - forward * _normal_cdf(-d1))


def black76_formula(
    *,
    forward: object,
    strike: object,
    volatility: object,
    expiry_years: object,
    option_type: OptionType | str,
    discount_factor: object = Decimal(1),
) -> OptionFormulaResult:
    """Price a call or put with the Black-76 formula.

    Parameters
    ----------
    forward, strike
        Positive forward and strike levels in the same units.
    volatility
        Raw-decimal lognormal volatility, for example ``0.20`` for 20%.
    expiry_years
        Time to expiry in ACT/365 years.
    discount_factor
        Discount factor to valuation.

    Returns
    -------
    OptionFormulaResult
        Discounted option value, intrinsic value, time value, and greeks in
        the Black-76 convention.

    Raises
    ------
    ValueError
        If the forward, strike, discount factor, or volatility is outside the
        model's domain.
    """
    resolved_option_type = OptionType.parse(option_type)
    resolved_forward = _to_decimal(forward)
    resolved_strike = _to_decimal(strike)
    resolved_volatility = _to_decimal(volatility)
    resolved_expiry_years = _to_decimal(expiry_years)
    resolved_discount_factor = _to_decimal(discount_factor)

    if resolved_forward <= Decimal(0):
        raise ValueError("black76_formula requires a positive forward.")
    if resolved_strike <= Decimal(0):
        raise ValueError("black76_formula requires a positive strike.")
    if resolved_discount_factor <= Decimal(0):
        raise ValueError("black76_formula requires a positive discount_factor.")
    if resolved_volatility < Decimal(0):
        raise ValueError("black76_formula requires a non-negative volatility.")

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
    volatility_time = volatility_float * sqrt(expiry_float)
    d1 = (log(forward_float / strike_float) + 0.5 * volatility_float * volatility_float * expiry_float) / volatility_time
    d2 = d1 - volatility_time
    pdf_d1 = _normal_pdf(d1)
    if resolved_option_type is OptionType.CALL:
        price = _black76_price(
            forward=forward_float,
            strike=strike_float,
            volatility=volatility_float,
            expiry_years=expiry_float,
            option_type=resolved_option_type,
            discount_factor=discount_float,
        )
        delta = discount_float * _normal_cdf(d1)
    else:
        price = _black76_price(
            forward=forward_float,
            strike=strike_float,
            volatility=volatility_float,
            expiry_years=expiry_float,
            option_type=resolved_option_type,
            discount_factor=discount_float,
        )
        delta = -discount_float * _normal_cdf(-d1)
    gamma = discount_float * pdf_d1 / (forward_float * volatility_time)
    vega = discount_float * forward_float * pdf_d1 * sqrt(expiry_float)

    if expiry_float > 0.0:
        time_bump = min(expiry_float / 2.0, 1.0 / 365.0) or 1.0 / 365.0
        shorter_time = max(expiry_float - time_bump, 0.0)
        longer_time = expiry_float + time_bump
        theta = -(
            _black76_price(
                forward=forward_float,
                strike=strike_float,
                volatility=volatility_float,
                expiry_years=longer_time,
                option_type=resolved_option_type,
                discount_factor=discount_float,
            )
            - _black76_price(
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
        base_price = price
        bumped_price = _black76_price(
            forward=forward_float,
            strike=strike_float,
            volatility=volatility_float,
            expiry_years=expiry_float,
            option_type=resolved_option_type,
            discount_factor=bumped_discount,
        )
        rho = (bumped_price - base_price) / rate_bump
    else:  # pragma: no cover - exercised through zero-expiry branch above
        theta = 0.0
        rho = 0.0

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
class Black76Pricer:
    """Black-76 pricer for rates options.

    The pricer assumes lognormal forward dynamics and uses the Black-76
    closed form for swaps, caps/floors, and futures options.
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
        """Proxy to :func:`black76_formula`.

        The formula works on a strictly positive forward, strike, and discount
        factor, with lognormal volatility quoted in raw decimal form.
        """
        return black76_formula(
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
        """Price a swaption using lognormal volatility.

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
            quote_type=VolQuoteType.LOGNORMAL,
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
        """Price a cap or floor by summing Black-76 optionlets."""
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
                quote_type=VolQuoteType.LOGNORMAL,
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
            quote_type=VolQuoteType.LOGNORMAL,
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


__all__ = ["Black76Pricer", "black76_formula"]
