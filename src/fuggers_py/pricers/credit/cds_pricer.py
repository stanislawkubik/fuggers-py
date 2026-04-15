"""Credit-default swap pricing helpers.

The pricer reports positive leg magnitudes and signed PV/CS01 measures under
the protection-side convention documented by ``CreditDefaultSwap``.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from fuggers_py.market.curve_support import curve_reference_date, discount_factor_at_date
from fuggers_py.market.curves.conversion import ValueConverter
from fuggers_py.market.curves import DiscountingCurve
from fuggers_py.market.state import AnalyticsCurves
from fuggers_py.products.credit import CreditDefaultSwap
from fuggers_py.core.types import Currency, Date


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _curve_supports_discounting(curve: object | None) -> bool:
    return isinstance(curve, DiscountingCurve)


def _curve_supports_credit(curve: object | None) -> bool:
    if curve is None:
        return False
    if hasattr(curve, "survival_probability"):
        return hasattr(curve, "reference_date")
    if hasattr(curve, "survival_probability_at_tenor"):
        return hasattr(curve, "reference_date")
    has_curve_space = hasattr(curve, "value_type") and (hasattr(curve, "value_at_tenor") or hasattr(curve, "value_at"))
    return has_curve_space and hasattr(curve, "reference_date")


def _credit_curve_date(curve: object) -> Date:
    if hasattr(curve, "reference_date"):
        return getattr(curve, "reference_date")
    raise ValueError("Credit curve must expose reference_date.")


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
        return _to_decimal(ValueConverter.hazard_to_survival(float(value), tenor))
    if kind_name.endswith("CREDIT_SPREAD"):
        loss_given_default = max(Decimal(1) - recovery_rate, Decimal("1e-12"))
        hazard = float(value / loss_given_default)
        return _to_decimal(ValueConverter.hazard_to_survival(hazard, tenor))
    raise ValueError(f"Unsupported credit curve value type for CDS pricing: {kind_name}.")


def _resolve_discount_curve(curves: AnalyticsCurves, currency: Currency) -> DiscountingCurve:
    environment = curves.multicurve_environment
    if environment is not None and hasattr(environment, "discount_curve"):
        curve = environment.discount_curve(currency)
        if _curve_supports_discounting(curve):
            return curve
    if _curve_supports_discounting(curves.discount_curve):
        return curves.discount_curve
    if _curve_supports_discounting(curves.collateral_curve):
        return curves.collateral_curve
    raise ValueError(f"Missing discount curve for currency {currency.code()}.")


def _resolve_credit_curve(curves: AnalyticsCurves) -> object:
    if _curve_supports_credit(curves.credit_curve):
        return curves.credit_curve
    if curves.credit_curve is not None and hasattr(curves.credit_curve, "value_type"):
        curve = curves.credit_curve
        if hasattr(curve, "value_at_tenor") or hasattr(curve, "value_at"):
            if hasattr(curve, "reference_date"):
                return curve
    raise ValueError("Missing credit curve in AnalyticsCurves.credit_curve.")


@dataclass(frozen=True, slots=True)
class CdsPricingResult:
    """Snapshot of CDS leg, spread, and risk measures.

    All monetary outputs are in currency units. ``par_spread`` is a raw
    decimal, and signed PV/CS01 follow the protection-side convention.
    """

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
    """Price CDS contracts under a midpoint default-timing approximation.

    Notes
    -----
    - ``premium_leg`` and ``protection_leg`` are positive magnitudes.
    - ``upfront`` is the fair upfront fraction of notional paid by the
      protection buyer.
    - ``present_value`` and ``cs01`` are signed from the contract side:
      ``BUY`` protection is positive when spreads widen.
    """

    default_timing_fraction: Decimal = Decimal("0.5")
    cs01_bump: Decimal = Decimal("0.0001")

    def __post_init__(self) -> None:
        object.__setattr__(self, "default_timing_fraction", _to_decimal(self.default_timing_fraction))
        object.__setattr__(self, "cs01_bump", _to_decimal(self.cs01_bump))
        if self.default_timing_fraction < Decimal(0) or self.default_timing_fraction > Decimal(1):
            raise ValueError("default_timing_fraction must lie in [0, 1].")

    def _valuation_date(self, discount_curve: DiscountingCurve, credit_curve: object) -> Date:
        valuation_date = curve_reference_date(discount_curve)
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
        curves: AnalyticsCurves,
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

            payment_discount = discount_factor_at_date(discount_curve, period.payment_date)
            default_discount = discount_factor_at_date(discount_curve, self._default_time(period_start, period.end_date))

            coupon_annuity += period.year_fraction * payment_discount * survival_end
            accrued_on_default_annuity += (
                period.year_fraction * cds.accrued_on_default_fraction * default_discount * default_probability
            )
            protection_leg += cds.loss_given_default() * default_discount * default_probability

        risky_pv01 = cds.notional * (coupon_annuity + accrued_on_default_annuity)
        return risky_pv01, cds.notional * accrued_on_default_annuity, cds.notional * protection_leg

    def risky_pv01(self, cds: CreditDefaultSwap, curves: AnalyticsCurves) -> Decimal:
        """Return risky PV01 as the notional-weighted premium annuity.

        The result is in currency units and includes accrued-on-default under
        the model's midpoint timing convention.
        """

        return self._risky_leg_components(cds, curves)[0]

    def accrued_on_default(self, cds: CreditDefaultSwap, curves: AnalyticsCurves) -> Decimal:
        """Return accrued-on-default PV in currency units."""

        return self._risky_leg_components(cds, curves)[1]

    def protection_leg(self, cds: CreditDefaultSwap, curves: AnalyticsCurves) -> Decimal:
        """Return protection-leg PV in currency units."""

        return self._risky_leg_components(cds, curves)[2]

    def premium_leg(self, cds: CreditDefaultSwap, curves: AnalyticsCurves) -> Decimal:
        """Return premium-leg PV in currency units."""

        return cds.running_spread * self.risky_pv01(cds, curves)

    def par_spread(self, cds: CreditDefaultSwap, curves: AnalyticsCurves) -> Decimal:
        """Return the par spread as a raw decimal.

        The spread is the premium rate that sets the contract PV to zero under
        the configured curves and recovery rate.
        """

        risky_pv01 = self.risky_pv01(cds, curves)
        if risky_pv01 == Decimal(0):
            return Decimal(0)
        return self.protection_leg(cds, curves) / risky_pv01

    def upfront(self, cds: CreditDefaultSwap, curves: AnalyticsCurves) -> Decimal:
        """Return the fair upfront fraction of notional.

        The value is expressed as a fraction of notional, not currency units.
        """

        raw_value = self.protection_leg(cds, curves) - self.premium_leg(cds, curves)
        return raw_value / cds.notional

    def pv(self, cds: CreditDefaultSwap, curves: AnalyticsCurves) -> Decimal:
        """Return signed present value from the protection-side convention.

        Positive PV means the protection buyer benefits when the contract is
        marked to market at the supplied curves.
        """

        protection_leg = self.protection_leg(cds, curves)
        premium_leg = self.premium_leg(cds, curves)
        return cds.protection_side.sign() * (protection_leg - premium_leg - cds.upfront_amount())

    def cs01(self, cds: CreditDefaultSwap, curves: AnalyticsCurves) -> Decimal:
        """Return signed CS01 using the configured bump size.

        The sensitivity is positive when the contract PV rises as credit
        spreads widen by 1 bp.
        """

        return cds.protection_side.sign() * self.risky_pv01(cds, curves) * self.cs01_bump

    def price(self, cds: CreditDefaultSwap, curves: AnalyticsCurves) -> CdsPricingResult:
        """Price a CDS contract and return all leg and risk measures.

        The result bundles the premium leg, accrued-on-default, protection
        leg, par spread, upfront, PV, risky PV01, and CS01.
        """

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


__all__ = ["CdsPricer", "CdsPricingResult"]
