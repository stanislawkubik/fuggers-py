"""Credit-default swap pricing helpers."""

from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal

from fuggers_py._core import Currency, Date, DayCountConvention

from .instruments import CreditDefaultSwap

_DAY_COUNT_ALIASES = {
    "ACT/360": "ACT_360",
    "ACT/365F": "ACT_365_FIXED",
    "ACT/365FIXED": "ACT_365_FIXED",
    "ACT/365L": "ACT_365_LEAP",
    "ACT/365LEAP": "ACT_365_LEAP",
    "ACT/ACT": "ACT_ACT_ISDA",
    "ACT/ACTISDA": "ACT_ACT_ISDA",
    "ACT/ACTICMA": "ACT_ACT_ICMA",
    "ACT/ACTAFB": "ACT_ACT_AFB",
    "30/360": "THIRTY_360_US",
    "30/360US": "THIRTY_360_US",
    "30E/360": "THIRTY_360_E",
    "30/360E": "THIRTY_360_E",
    "30E/360ISDA": "THIRTY_360_E_ISDA",
    "30/360GERMAN": "THIRTY_360_GERMAN",
}


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _curve_supports_discounting(curve: object | None) -> bool:
    return curve is not None and hasattr(curve, "discount_factor_at") and hasattr(curve, "reference_date")


def _curve_supports_credit(curve: object | None) -> bool:
    if curve is None:
        return False
    if hasattr(curve, "survival_probability"):
        return hasattr(curve, "reference_date")
    if hasattr(curve, "survival_probability_at_tenor"):
        return hasattr(curve, "reference_date")
    has_curve_space = hasattr(curve, "value_type") and (hasattr(curve, "value_at_tenor") or hasattr(curve, "value_at"))
    return has_curve_space and hasattr(curve, "reference_date")


def _curve_reference_date(curve: object) -> Date:
    reference_date = getattr(curve, "reference_date", None)
    if not isinstance(reference_date, Date):
        raise ValueError("Curve must expose reference_date.")
    return reference_date


def _curve_day_count(curve: object):
    spec = getattr(curve, "spec", None)
    day_count_label = getattr(spec, "day_count", None)
    if not isinstance(day_count_label, str):
        raise ValueError("Curve spec must expose day_count.")
    key = day_count_label.strip().upper().replace(" ", "")
    if key in DayCountConvention.__members__:
        return DayCountConvention[key].to_day_count()
    alias = _DAY_COUNT_ALIASES.get(key)
    if alias is not None:
        return DayCountConvention[alias].to_day_count()
    raise ValueError(f"Unsupported curve day-count label: {day_count_label}.")


def _curve_year_fraction(curve: object, start_date: Date, end_date: Date) -> Decimal:
    return _curve_day_count(curve).year_fraction(start_date, end_date)


def _tenor_from_curve_date(curve: object, date: Date) -> float:
    reference_date = _curve_reference_date(curve)
    if date < reference_date:
        raise ValueError("Curve date lookup requires date >= curve.reference_date.")
    if date == reference_date:
        return 0.0
    return float(_curve_year_fraction(curve, reference_date, date))


def _discount_factor_at_date(curve: object, date: Date) -> Decimal:
    tenor = _tenor_from_curve_date(curve, date)
    if tenor <= 0.0:
        return Decimal(1)
    return _to_decimal(getattr(curve, "discount_factor_at")(tenor))


def _credit_curve_date(curve: object) -> Date:
    return _curve_reference_date(curve)


def _credit_curve_years(curve: object, date: Date) -> float:
    reference_date = _credit_curve_date(curve)
    if date <= reference_date:
        return 0.0
    return max(reference_date.days_between(date), 0) / 365.0


def _credit_curve_value_type(curve: object):
    value_type = getattr(curve, "value_type")
    return value_type() if callable(value_type) else value_type


def _credit_curve_kind_name(curve: object) -> str:
    value_type = _credit_curve_value_type(curve)
    kind = getattr(value_type, "kind", value_type)
    name = getattr(kind, "name", str(kind))
    return str(name).upper()


def _credit_curve_value_at_tenor(curve: object, tenor: float) -> Decimal:
    if hasattr(curve, "value_at_tenor"):
        return _to_decimal(getattr(curve, "value_at_tenor")(tenor))
    if hasattr(curve, "value_at"):
        return _to_decimal(getattr(curve, "value_at")(tenor))
    raise ValueError("Credit curve must expose value_at_tenor(...) or value_at(...).")


def _hazard_to_survival(hazard_rate: float, tenor: float) -> Decimal:
    if tenor < 0.0:
        raise ValueError("Tenor must be non-negative.")
    if hazard_rate < 0.0:
        raise ValueError("hazard_rate must be non-negative.")
    return _to_decimal(math.exp(-hazard_rate * tenor))


def _credit_curve_survival_probability(curve: object, date: Date, recovery_rate: Decimal) -> Decimal:
    if hasattr(curve, "survival_probability"):
        return _to_decimal(getattr(curve, "survival_probability")(date))
    tenor = _credit_curve_years(curve, date)
    if tenor <= 0.0:
        return Decimal(1)
    if hasattr(curve, "survival_probability_at_tenor"):
        return _to_decimal(getattr(curve, "survival_probability_at_tenor")(tenor))
    value = _credit_curve_value_at_tenor(curve, tenor)
    kind_name = _credit_curve_kind_name(curve)
    if kind_name.endswith("SURVIVAL_PROBABILITY"):
        return value
    if kind_name.endswith("HAZARD_RATE"):
        return _hazard_to_survival(float(value), tenor)
    if kind_name.endswith("CREDIT_SPREAD"):
        loss_given_default = max(Decimal(1) - recovery_rate, Decimal("1e-12"))
        hazard = float(value / loss_given_default)
        return _hazard_to_survival(hazard, tenor)
    raise ValueError(f"Unsupported credit curve value type for CDS pricing: {kind_name}.")


def _resolve_discount_curve(curves: object, currency: Currency) -> object:
    environment = getattr(curves, "multicurve_environment", None)
    if environment is not None and hasattr(environment, "discount_curve"):
        curve = environment.discount_curve(currency)
        if _curve_supports_discounting(curve):
            return curve
    for attribute_name in ("discount_curve", "collateral_curve"):
        curve = getattr(curves, attribute_name, None)
        if _curve_supports_discounting(curve):
            return curve
    raise ValueError(f"Missing discount curve for currency {currency.code()}.")


def _resolve_credit_curve(curves: object) -> object:
    curve = getattr(curves, "credit_curve", None)
    if _curve_supports_credit(curve):
        return curve
    raise ValueError("Missing credit curve in AnalyticsCurves.credit_curve.")


@dataclass(frozen=True, slots=True)
class CdsPricingResult:
    premium_leg: Decimal
    accrued_on_default: Decimal
    protection_leg: Decimal
    par_spread: Decimal
    upfront: Decimal
    present_value: Decimal
    risky_pv01: Decimal
    cs01: Decimal


@dataclass(frozen=True, slots=True)
class CdsPricer:
    default_timing_fraction: Decimal = Decimal("0.5")
    cs01_bump: Decimal = Decimal("0.0001")

    def __post_init__(self) -> None:
        object.__setattr__(self, "default_timing_fraction", _to_decimal(self.default_timing_fraction))
        object.__setattr__(self, "cs01_bump", _to_decimal(self.cs01_bump))
        if self.default_timing_fraction < Decimal(0) or self.default_timing_fraction > Decimal(1):
            raise ValueError("default_timing_fraction must lie in [0, 1].")

    def _valuation_date(self, discount_curve: object, credit_curve: object) -> Date:
        valuation_date = _curve_reference_date(discount_curve)
        credit_reference = _credit_curve_date(credit_curve)
        if credit_reference > valuation_date:
            return credit_reference
        return valuation_date

    def _default_time(self, start_date: Date, end_date: Date) -> Date:
        days = start_date.days_between(end_date)
        offset = int(round(days * float(self.default_timing_fraction)))
        return start_date.add_days(offset)

    def _risky_leg_components(
        self,
        cds: CreditDefaultSwap,
        curves: object,
    ) -> tuple[Decimal, Decimal, Decimal]:
        discount_curve = _resolve_discount_curve(curves, cds.currency)
        credit_curve = _resolve_credit_curve(curves)
        valuation_date = self._valuation_date(discount_curve, credit_curve)
        coupon_annuity = Decimal(0)
        accrued_on_default_annuity = Decimal(0)
        protection_leg = Decimal(0)
        for period in cds.premium_periods():
            if period.end_date <= valuation_date:
                continue
            period_start = period.start_date if period.start_date >= valuation_date else valuation_date
            credit_reference = _credit_curve_date(credit_curve)
            survival_start = Decimal(1) if period_start <= credit_reference else _credit_curve_survival_probability(
                credit_curve,
                period_start,
                cds.recovery_rate,
            )
            survival_end = _credit_curve_survival_probability(credit_curve, period.end_date, cds.recovery_rate)
            default_probability = survival_start - survival_end
            if default_probability < Decimal(0):
                default_probability = Decimal(0)
            payment_discount = _discount_factor_at_date(discount_curve, period.payment_date)
            default_discount = _discount_factor_at_date(discount_curve, self._default_time(period_start, period.end_date))
            coupon_annuity += period.year_fraction * payment_discount * survival_end
            accrued_on_default_annuity += (
                period.year_fraction * cds.accrued_on_default_fraction * default_discount * default_probability
            )
            protection_leg += cds.loss_given_default() * default_discount * default_probability
        risky_pv01 = cds.notional * (coupon_annuity + accrued_on_default_annuity)
        return risky_pv01, cds.notional * accrued_on_default_annuity, cds.notional * protection_leg

    def risky_pv01(self, cds: CreditDefaultSwap, curves: object) -> Decimal:
        return self._risky_leg_components(cds, curves)[0]

    def accrued_on_default(self, cds: CreditDefaultSwap, curves: object) -> Decimal:
        return self._risky_leg_components(cds, curves)[1]

    def protection_leg(self, cds: CreditDefaultSwap, curves: object) -> Decimal:
        return self._risky_leg_components(cds, curves)[2]

    def premium_leg(self, cds: CreditDefaultSwap, curves: object) -> Decimal:
        return cds.running_spread * self.risky_pv01(cds, curves)

    def par_spread(self, cds: CreditDefaultSwap, curves: object) -> Decimal:
        risky_pv01 = self.risky_pv01(cds, curves)
        if risky_pv01 == Decimal(0):
            return Decimal(0)
        return self.protection_leg(cds, curves) / risky_pv01

    def upfront(self, cds: CreditDefaultSwap, curves: object) -> Decimal:
        raw_value = self.protection_leg(cds, curves) - self.premium_leg(cds, curves)
        return raw_value / cds.notional

    def pv(self, cds: CreditDefaultSwap, curves: object) -> Decimal:
        protection_leg = self.protection_leg(cds, curves)
        premium_leg = self.premium_leg(cds, curves)
        return cds.protection_side.sign() * (protection_leg - premium_leg - cds.upfront_amount())

    def cs01(self, cds: CreditDefaultSwap, curves: object) -> Decimal:
        return cds.protection_side.sign() * self.risky_pv01(cds, curves) * self.cs01_bump

    def price(self, cds: CreditDefaultSwap, curves: object) -> CdsPricingResult:
        risky_pv01, accrued_on_default, protection_leg = self._risky_leg_components(cds, curves)
        premium_leg = cds.running_spread * risky_pv01
        par_spread = Decimal(0) if risky_pv01 == Decimal(0) else protection_leg / risky_pv01
        upfront = (protection_leg - premium_leg) / cds.notional
        present_value = cds.protection_side.sign() * (protection_leg - premium_leg - cds.upfront_amount())
        return CdsPricingResult(
            premium_leg=premium_leg,
            accrued_on_default=accrued_on_default,
            protection_leg=protection_leg,
            par_spread=par_spread,
            upfront=upfront,
            present_value=present_value,
            risky_pv01=risky_pv01,
            cs01=cds.protection_side.sign() * risky_pv01 * self.cs01_bump,
        )


__all__ = [
    "CdsPricer",
    "CdsPricingResult",
]
