"""Cross-currency basis-swap pricing helpers.

PVs are reported in the chosen valuation currency. The par spread is a raw
decimal and FX conversions follow the swap's pay and receive currencies.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from fuggers_py._core import PayReceive
from fuggers_py._core.types import Currency, Date
from fuggers_py._core.ids import CurrencyPair
from fuggers_py.curves.date_support import discount_factor_at_date

from ._curve_resolver import forward_rate_from_curve, resolve_discount_curve, resolve_projection_curve
from .common import FloatingLegSpec
from .cross_currency_basis import CrossCurrencyBasisSwap


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _pair(base: Currency, quote: Currency) -> CurrencyPair:
    return CurrencyPair(base=base, quote=quote)


def _curve_value_at_date(candidate: object, date: Date) -> Decimal | None:
    if hasattr(candidate, "value_at_date"):
        return _to_decimal(candidate.value_at_date(date))
    if hasattr(candidate, "date_to_tenor") and hasattr(candidate, "value_at_tenor"):
        tenor = candidate.date_to_tenor(date)
        return _to_decimal(candidate.value_at_tenor(tenor))
    return None


def _call_fx_method(curve: object, pair: CurrencyPair, date: Date) -> Decimal | None:
    for method_name in ("forward_rate", "fx_forward_rate", "forward_fx_rate", "rate", "get_forward_rate"):
        method = getattr(curve, method_name, None)
        if method is None:
            continue
        attempts = (
            lambda: method(pair, date),
            lambda: method(pair.as_str(), date),
            lambda: method(currency_pair=pair, date=date),
            lambda: method(currency_pair=pair.as_str(), date=date),
        )
        for attempt in attempts:
            try:
                value = attempt()
            except TypeError:
                continue
            except Exception:
                continue
            if value is not None:
                return _to_decimal(value)
    return None


def _forward_rate_from_explicit_curve(curves: object, pair: CurrencyPair, date: Date) -> Decimal | None:
    curve = curves.fx_forward_curve
    if curve is None:
        return None
    direct = _call_fx_method(curve, pair, date)
    if direct is not None:
        return direct

    inverse_pair = _pair(pair.quote, pair.base)
    inverse = _call_fx_method(curve, inverse_pair, date)
    if inverse is not None:
        if inverse == Decimal(0):
            raise ValueError("FX forward curve returned a zero inverse forward rate.")
        return Decimal(1) / inverse

    if isinstance(curve, dict) or hasattr(curve, "get"):
        getter = curve.get if hasattr(curve, "get") else curve.__getitem__
        for candidate_pair, invert in ((pair, False), (inverse_pair, True)):
            keys = (candidate_pair, candidate_pair.as_str(), candidate_pair.as_str().lower(), candidate_pair.as_str().upper())
            for key in keys:
                try:
                    candidate = getter(key)
                except Exception:
                    continue
                if candidate is None:
                    continue
                if isinstance(candidate, (Decimal, int, float, str)):
                    value = _to_decimal(candidate)
                else:
                    value = _call_fx_method(candidate, candidate_pair, date)
                    if value is None:
                        value = _curve_value_at_date(candidate, date)
                if value is None:
                    continue
                if invert:
                    if value == Decimal(0):
                        raise ValueError("FX forward sub-curve returned a zero inverse forward rate.")
                    return Decimal(1) / value
                return value
    explicit_value = _curve_value_at_date(curve, date)
    if explicit_value is not None:
        return explicit_value
    return None


@dataclass(frozen=True, slots=True)
class CrossCurrencyBasisSwapPricingResult:
    """Cross-currency basis-swap pricing output.

    All PV fields are expressed in ``valuation_currency`` and the quoted
    spread is a raw decimal.
    """

    valuation_currency: Currency
    par_spread: Decimal
    present_value: Decimal
    pay_leg_pv: Decimal
    receive_leg_pv: Decimal
    principal_exchange_pv: Decimal
    spread_annuity: Decimal


@dataclass(frozen=True, slots=True)
class CrossCurrencyBasisSwapPricer:
    """Price cross-currency basis swaps.

    The pricer values each leg in a chosen valuation currency and converts
    cash flows using either explicit FX forwards or discount-curve parity.
    """

    def _valuation_currency(
        self,
        swap: CrossCurrencyBasisSwap,
        valuation_currency: Currency | None,
    ) -> Currency:
        resolved = valuation_currency or swap.pay_leg.currency
        if resolved not in {swap.pay_leg.currency, swap.receive_leg.currency}:
            raise ValueError("valuation_currency must be one of the swap leg currencies.")
        return resolved

    def _pair_forward_rate(self, swap: CrossCurrencyBasisSwap, curves: object, date: Date) -> Decimal:
        pair = swap.currency_pair()
        explicit = _forward_rate_from_explicit_curve(curves, pair, date)
        if explicit is not None:
            return explicit
        pay_discount_curve = resolve_discount_curve(curves, swap.pay_leg.currency)
        receive_discount_curve = resolve_discount_curve(curves, swap.receive_leg.currency)
        return (
            swap.spot_fx_rate
            * discount_factor_at_date(pay_discount_curve, date)
            / discount_factor_at_date(receive_discount_curve, date)
        )

    def _fx_conversion_rate(
        self,
        swap: CrossCurrencyBasisSwap,
        curves: object,
        *,
        source_currency: Currency,
        target_currency: Currency,
        date: Date,
    ) -> Decimal:
        if source_currency is target_currency:
            return Decimal(1)
        forward = self._pair_forward_rate(swap, curves, date)
        if source_currency is swap.pay_leg.currency and target_currency is swap.receive_leg.currency:
            return forward
        if source_currency is swap.receive_leg.currency and target_currency is swap.pay_leg.currency:
            if forward == Decimal(0):
                raise ValueError("CrossCurrencyBasisSwap requires a non-zero FX forward rate.")
            return Decimal(1) / forward
        raise ValueError("FX conversion only supports the swap's two leg currencies.")

    def _leg_pv(
        self,
        swap: CrossCurrencyBasisSwap,
        leg: FloatingLegSpec,
        periods,
        curves: object,
        *,
        valuation_currency: Currency,
        include_spread: bool,
    ) -> Decimal:
        projection_curve = resolve_projection_curve(
            curves,
            currency=leg.currency,
            index_name=leg.index_name,
            index_tenor=leg.index_tenor,
        )
        discount_curve = resolve_discount_curve(curves, valuation_currency)
        spread = leg.spread if include_spread else Decimal(0)
        present_value = Decimal(0)
        sign = leg.pay_receive.sign()
        for period in periods:
            forward = forward_rate_from_curve(
                projection_curve,
                period.start_date,
                period.end_date,
                day_count_convention=leg.day_count_convention,
            )
            coupon = leg.notional * (forward + spread) * period.year_fraction
            fx_conversion = self._fx_conversion_rate(
                swap,
                curves,
                source_currency=leg.currency,
                target_currency=valuation_currency,
                date=period.payment_date,
            )
            present_value += sign * coupon * fx_conversion * discount_factor_at_date(discount_curve, period.payment_date)
        return present_value

    def _principal_exchange_pv(
        self,
        swap: CrossCurrencyBasisSwap,
        curves: object,
        *,
        valuation_currency: Currency,
    ) -> Decimal:
        discount_curve = resolve_discount_curve(curves, valuation_currency)
        present_value = Decimal(0)
        if swap.initial_exchange:
            for leg in (swap.pay_leg, swap.receive_leg):
                fx_conversion = self._fx_conversion_rate(
                    swap,
                    curves,
                    source_currency=leg.currency,
                    target_currency=valuation_currency,
                    date=swap.effective_date,
                )
                present_value += leg.pay_receive.sign() * leg.notional * fx_conversion * discount_factor_at_date(
                    discount_curve,
                    swap.effective_date,
                )
        if swap.final_exchange:
            for leg in (swap.pay_leg, swap.receive_leg):
                fx_conversion = self._fx_conversion_rate(
                    swap,
                    curves,
                    source_currency=leg.currency,
                    target_currency=valuation_currency,
                    date=swap.maturity_date,
                )
                present_value -= leg.pay_receive.sign() * leg.notional * fx_conversion * discount_factor_at_date(
                    discount_curve,
                    swap.maturity_date,
                )
        return present_value

    def _annuity(
        self,
        swap: CrossCurrencyBasisSwap,
        leg: FloatingLegSpec,
        periods,
        curves: object,
        *,
        valuation_currency: Currency,
    ) -> Decimal:
        discount_curve = resolve_discount_curve(curves, valuation_currency)
        annuity = Decimal(0)
        for period in periods:
            fx_conversion = self._fx_conversion_rate(
                swap,
                curves,
                source_currency=leg.currency,
                target_currency=valuation_currency,
                date=period.payment_date,
            )
            annuity += leg.notional * period.year_fraction * fx_conversion * discount_factor_at_date(
                discount_curve,
                period.payment_date,
            )
        if annuity == Decimal(0):
            raise ValueError("CrossCurrencyBasisSwap par spread requires a non-zero quoted-leg annuity.")
        return annuity

    def pay_leg_pv(
        self,
        swap: CrossCurrencyBasisSwap,
        curves: object,
        *,
        valuation_currency: Currency | None = None,
    ) -> Decimal:
        """Return the discounted PV of the pay leg in the valuation currency."""

        resolved_currency = self._valuation_currency(swap, valuation_currency)
        return self._leg_pv(
            swap,
            swap.pay_leg,
            swap.pay_periods(),
            curves,
            valuation_currency=resolved_currency,
            include_spread=True,
        )

    def receive_leg_pv(
        self,
        swap: CrossCurrencyBasisSwap,
        curves: object,
        *,
        valuation_currency: Currency | None = None,
    ) -> Decimal:
        """Return the discounted PV of the receive leg in the valuation currency."""

        resolved_currency = self._valuation_currency(swap, valuation_currency)
        return self._leg_pv(
            swap,
            swap.receive_leg,
            swap.receive_periods(),
            curves,
            valuation_currency=resolved_currency,
            include_spread=True,
        )

    def principal_exchange_pv(
        self,
        swap: CrossCurrencyBasisSwap,
        curves: object,
        *,
        valuation_currency: Currency | None = None,
    ) -> Decimal:
        """Return the PV of the principal exchanges."""

        return self._principal_exchange_pv(
            swap,
            curves,
            valuation_currency=self._valuation_currency(swap, valuation_currency),
        )

    def pv(
        self,
        swap: CrossCurrencyBasisSwap,
        curves: object,
        *,
        valuation_currency: Currency | None = None,
    ) -> Decimal:
        """Return the total present value in the valuation currency."""

        resolved_currency = self._valuation_currency(swap, valuation_currency)
        return (
            self.pay_leg_pv(swap, curves, valuation_currency=resolved_currency)
            + self.receive_leg_pv(swap, curves, valuation_currency=resolved_currency)
            + self._principal_exchange_pv(swap, curves, valuation_currency=resolved_currency)
        )

    def par_spread(
        self,
        swap: CrossCurrencyBasisSwap,
        curves: object,
        *,
        valuation_currency: Currency | None = None,
    ) -> Decimal:
        """Return the par spread on the quoted leg as a raw decimal.

        The spread is solved so that the total PV in the valuation currency is
        zero.
        """

        resolved_currency = self._valuation_currency(swap, valuation_currency)
        principal_exchange_pv = self._principal_exchange_pv(swap, curves, valuation_currency=resolved_currency)
        if swap.quoted_leg is PayReceive.RECEIVE:
            quoted_leg = swap.receive_leg
            quoted_periods = swap.receive_periods()
            other_leg_pv = self._leg_pv(
                swap,
                swap.pay_leg,
                swap.pay_periods(),
                curves,
                valuation_currency=resolved_currency,
                include_spread=True,
            )
        else:
            quoted_leg = swap.pay_leg
            quoted_periods = swap.pay_periods()
            other_leg_pv = self._leg_pv(
                swap,
                swap.receive_leg,
                swap.receive_periods(),
                curves,
                valuation_currency=resolved_currency,
                include_spread=True,
            )
        quoted_leg_pv_without_spread = self._leg_pv(
            swap,
            quoted_leg,
            quoted_periods,
            curves,
            valuation_currency=resolved_currency,
            include_spread=False,
        )
        annuity = self._annuity(
            swap,
            quoted_leg,
            quoted_periods,
            curves,
            valuation_currency=resolved_currency,
        )
        return -(other_leg_pv + quoted_leg_pv_without_spread + principal_exchange_pv) / (
            quoted_leg.pay_receive.sign() * annuity
        )

    def price(
        self,
        swap: CrossCurrencyBasisSwap,
        curves: object,
        *,
        valuation_currency: Currency | None = None,
    ) -> CrossCurrencyBasisSwapPricingResult:
        """Return the full cross-currency basis-swap pricing result.

        The result includes the chosen valuation currency, total PV, leg PVs,
        the principal-exchange PV, and the quoted-leg annuity.
        """

        resolved_currency = self._valuation_currency(swap, valuation_currency)
        pay_leg_pv = self.pay_leg_pv(swap, curves, valuation_currency=resolved_currency)
        receive_leg_pv = self.receive_leg_pv(swap, curves, valuation_currency=resolved_currency)
        principal_exchange_pv = self._principal_exchange_pv(swap, curves, valuation_currency=resolved_currency)
        if swap.quoted_leg is PayReceive.RECEIVE:
            quoted_leg = swap.receive_leg
            quoted_periods = swap.receive_periods()
        else:
            quoted_leg = swap.pay_leg
            quoted_periods = swap.pay_periods()
        spread_annuity = self._annuity(
            swap,
            quoted_leg,
            quoted_periods,
            curves,
            valuation_currency=resolved_currency,
        )
        par_spread = self.par_spread(swap, curves, valuation_currency=resolved_currency)
        return CrossCurrencyBasisSwapPricingResult(
            valuation_currency=resolved_currency,
            par_spread=par_spread,
            present_value=pay_leg_pv + receive_leg_pv + principal_exchange_pv,
            pay_leg_pv=pay_leg_pv,
            receive_leg_pv=receive_leg_pv,
            principal_exchange_pv=principal_exchange_pv,
            spread_annuity=spread_annuity,
        )


__all__ = ["CrossCurrencyBasisSwapPricer", "CrossCurrencyBasisSwapPricingResult"]
