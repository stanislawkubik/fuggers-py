"""Bootstrap CDS-implied credit curves.

The bootstrap converts CDS quotes into survival probabilities and hazard rates
using raw decimal par spreads or upfront fractions of notional, and returns a
credit-curve wrapper plus the calibrated point-by-point diagnostics.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING

from fuggers_py.reference.bonds.types import CalendarId, Tenor
from fuggers_py.core.calendars import BusinessDayConvention
from fuggers_py.core.daycounts import DayCountConvention
from fuggers_py.core.types import Currency, Date, Frequency
from fuggers_py.market.state import AnalyticsCurves
from fuggers_py.core import InstrumentId
from fuggers_py.market.quotes import CdsQuote
from fuggers_py.reference import CdsReferenceData

from ..discrete import DiscreteCurve, ExtrapolationMethod, InterpolationMethod
from ..value_type import ValueType
from ..wrappers import CreditCurve

if TYPE_CHECKING:
    from fuggers_py.products.credit import CreditDefaultSwap


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _coerce_currency(value: Currency | str) -> Currency:
    if isinstance(value, Currency):
        return value
    return Currency.from_code(str(value))


def _coerce_frequency(value: Frequency | str) -> Frequency:
    if isinstance(value, Frequency):
        return value
    normalized = value.strip().upper().replace("-", "_").replace(" ", "_")
    aliases = {
        "ANNUAL": Frequency.ANNUAL,
        "YEARLY": Frequency.ANNUAL,
        "SEMIANNUAL": Frequency.SEMI_ANNUAL,
        "SEMI_ANNUAL": Frequency.SEMI_ANNUAL,
        "SEMI": Frequency.SEMI_ANNUAL,
        "QUARTERLY": Frequency.QUARTERLY,
        "QUARTER": Frequency.QUARTERLY,
        "MONTHLY": Frequency.MONTHLY,
        "MONTH": Frequency.MONTHLY,
    }
    if normalized in aliases:
        return aliases[normalized]
    return Frequency[normalized]


def _coerce_day_count(value: DayCountConvention | str) -> DayCountConvention:
    if isinstance(value, DayCountConvention):
        return value
    normalized = value.strip().upper().replace("/", "_")
    aliases = {
        "ACT360": DayCountConvention.ACT_360,
        "ACT_360": DayCountConvention.ACT_360,
        "ACT365F": DayCountConvention.ACT_365_FIXED,
        "ACT_365_FIXED": DayCountConvention.ACT_365_FIXED,
        "ACT365L": DayCountConvention.ACT_365_LEAP,
        "ACT_365_LEAP": DayCountConvention.ACT_365_LEAP,
    }
    if normalized in aliases:
        return aliases[normalized]
    return DayCountConvention[normalized]


def _coerce_calendar(value: CalendarId | str) -> CalendarId:
    if isinstance(value, CalendarId):
        return value
    return CalendarId.new(value)


def _coerce_business_day_convention(value: BusinessDayConvention | str) -> BusinessDayConvention:
    if isinstance(value, BusinessDayConvention):
        return value
    normalized = value.strip().upper().replace("-", "_").replace(" ", "_")
    return BusinessDayConvention[normalized]


def _instrument_key(value: InstrumentId | str) -> str:
    return str(InstrumentId.parse(value))


@dataclass(frozen=True, slots=True)
class CdsBootstrapPoint:
    """Single calibrated point on a bootstrapped CDS credit curve.

    Attributes
    ----------
    instrument_id
        CDS instrument identifier.
    maturity_date
        Contract maturity date.
    maturity_tenor
        Maturity expressed as a year-fraction tenor.
    survival_probability
        Survival probability at the maturity point.
    hazard_rate
        Piecewise-constant hazard rate implied by the interval.
    market_par_spread
        Market par-spread quote when the quote was a running-spread quote.
    market_upfront
        Market upfront quote when the quote was an upfront quote.
    fitted_par_spread
        Model par spread from the calibrated curve.
    fitted_upfront
        Model upfront fraction from the calibrated curve.
    running_spread
        Fixed running coupon used in the bootstrap contract.
    recovery_rate
        Recovery-rate assumption used for calibration.
    """

    instrument_id: InstrumentId
    maturity_date: Date
    maturity_tenor: Decimal
    survival_probability: Decimal
    hazard_rate: Decimal
    market_par_spread: Decimal | None = None
    market_upfront: Decimal | None = None
    fitted_par_spread: Decimal | None = None
    fitted_upfront: Decimal | None = None
    running_spread: Decimal | None = None
    recovery_rate: Decimal | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "instrument_id", InstrumentId.parse(self.instrument_id))
        for field_name in (
            "maturity_tenor",
            "survival_probability",
            "hazard_rate",
            "market_par_spread",
            "market_upfront",
            "fitted_par_spread",
            "fitted_upfront",
            "running_spread",
            "recovery_rate",
        ):
            value = getattr(self, field_name)
            if value is not None:
                object.__setattr__(self, field_name, _to_decimal(value))


@dataclass(frozen=True, slots=True)
class CdsBootstrapResult:
    """Bootstrapping result containing the curve and solved calibration points.

    The result keeps the calibrated credit curve together with the point-level
    survival probabilities and hazard rates used to fit it.
    """

    credit_curve: CreditCurve
    points: tuple[CdsBootstrapPoint, ...]
    recovery_rate: Decimal

    def __post_init__(self) -> None:
        object.__setattr__(self, "points", tuple(self.points))
        object.__setattr__(self, "recovery_rate", _to_decimal(self.recovery_rate))


@dataclass(frozen=True, slots=True)
class _BootstrapInstrument:
    quote: CdsQuote
    contract: CreditDefaultSwap
    maturity_tenor: Decimal


def _lookup_reference_data(
    reference_data: Mapping[InstrumentId | str, CdsReferenceData] | None,
    instrument_id: InstrumentId,
) -> CdsReferenceData | None:
    if reference_data is None:
        return None
    keyed = {_instrument_key(key): value for key, value in reference_data.items()}
    return keyed.get(str(instrument_id))


def _build_credit_curve(
    valuation_date: Date,
    maturity_tenors: Sequence[Decimal],
    survival_probabilities: Sequence[Decimal],
    recovery_rate: Decimal,
) -> CreditCurve:
    if not maturity_tenors:
        raise ValueError("bootstrap_credit_curve requires at least one maturity.")
    first_tenor = float(maturity_tenors[0])
    epsilon = min(1e-8, max(first_tenor * 0.5, 1e-12))
    if epsilon >= first_tenor:
        epsilon = max(first_tenor * 0.5, 1e-12)
    curve = DiscreteCurve(
        valuation_date,
        tenors=[epsilon, *[float(value) for value in maturity_tenors]],
        values=[1.0, *[float(value) for value in survival_probabilities]],
        value_type=ValueType.survival_probability(),
        interpolation_method=InterpolationMethod.LOG_LINEAR,
        extrapolation_method=ExtrapolationMethod.FLAT,
    )
    return CreditCurve(curve, recovery_rate=recovery_rate)


def _resolve_tenor(quote: CdsQuote, reference: CdsReferenceData | None) -> Tenor:
    tenor_text = quote.tenor if quote.tenor is not None else None if reference is None else reference.tenor
    if tenor_text is None:
        raise ValueError(f"Missing tenor for CDS quote {quote.instrument_id}.")
    return Tenor.parse(tenor_text)


def _resolve_recovery_rate(
    quote: CdsQuote,
    reference: CdsReferenceData | None,
    default_recovery_rate: Decimal | None,
) -> Decimal:
    if quote.recovery_rate is not None:
        return quote.recovery_rate
    if reference is not None and reference.recovery_rate is not None:
        return reference.recovery_rate
    if default_recovery_rate is not None:
        return default_recovery_rate
    return Decimal("0.4")


def _build_bootstrap_instruments(
    quotes: Sequence[CdsQuote],
    *,
    valuation_date: Date,
    reference_data: Mapping[InstrumentId | str, CdsReferenceData] | None,
    recovery_rate: Decimal | None,
    payment_frequency: Frequency,
    day_count_convention: DayCountConvention,
    default_currency: Currency,
    calendar: CalendarId,
    business_day_convention: BusinessDayConvention,
    end_of_month: bool,
    accrued_on_default_fraction: Decimal,
    notional: Decimal,
) -> tuple[_BootstrapInstrument, ...]:
    from fuggers_py.products.credit import CreditDefaultSwap, ProtectionSide

    instruments: list[_BootstrapInstrument] = []
    for quote in quotes:
        reference = _lookup_reference_data(reference_data, quote.instrument_id)
        tenor = _resolve_tenor(quote, reference)
        maturity_date = tenor.add_to(valuation_date)
        running_spread = quote.par_spread
        upfront = Decimal(0)
        if running_spread is None:
            if reference is None or reference.coupon is None:
                raise ValueError(
                    f"CDS upfront quote {quote.instrument_id} requires CdsReferenceData.coupon for calibration."
                )
            running_spread = reference.coupon
            upfront = quote.upfront if quote.upfront is not None else Decimal(0)
        resolved_currency = (
            quote.currency
            if quote.currency is not None
            else default_currency if reference is None else reference.currency
        )
        contract = CreditDefaultSwap(
            effective_date=valuation_date,
            maturity_date=maturity_date,
            running_spread=running_spread,
            notional=notional,
            protection_side=ProtectionSide.BUY,
            recovery_rate=_resolve_recovery_rate(quote, reference, recovery_rate),
            currency=resolved_currency,
            payment_frequency=payment_frequency,
            day_count_convention=day_count_convention,
            calendar=calendar,
            business_day_convention=business_day_convention,
            end_of_month=end_of_month,
            accrued_on_default_fraction=accrued_on_default_fraction,
            upfront=upfront,
            reference_entity=quote.reference_entity if quote.reference_entity is not None else None if reference is None else reference.reference_entity,
            instrument_id=quote.instrument_id,
        )
        maturity_tenor = DayCountConvention.ACT_365_FIXED.to_day_count().year_fraction(valuation_date, maturity_date)
        instruments.append(
            _BootstrapInstrument(
                quote=quote,
                contract=contract,
                maturity_tenor=maturity_tenor,
            )
        )
    instruments.sort(key=lambda item: (item.maturity_tenor, str(item.quote.instrument_id)))
    return tuple(instruments)


def bootstrap_credit_curve(
    quotes: Sequence[CdsQuote],
    *,
    valuation_date: Date,
    discount_curve: object,
    reference_data: Mapping[InstrumentId | str, CdsReferenceData] | None = None,
    recovery_rate: object | None = None,
    payment_frequency: Frequency | str = Frequency.QUARTERLY,
    day_count_convention: DayCountConvention | str = DayCountConvention.ACT_360,
    currency: Currency | str = Currency.USD,
    calendar: CalendarId | str = CalendarId.weekend_only(),
    business_day_convention: BusinessDayConvention | str = BusinessDayConvention.MODIFIED_FOLLOWING,
    end_of_month: bool = True,
    accrued_on_default_fraction: object = Decimal("0.5"),
    default_timing_fraction: object = Decimal("0.5"),
    notional: object = Decimal(1),
    max_iterations: int = 128,
    tolerance: object = Decimal("1e-10"),
) -> CdsBootstrapResult:
    """Bootstrap a survival curve from CDS quotes.

    Quotes are interpreted as par-spread quotes when ``CdsQuote.par_spread``
    is present and as upfront quotes when ``CdsQuote.upfront`` is present.
    Upfront calibration uses ``CdsReferenceData.coupon`` as the fixed running
    coupon. The bootstrap solves survival probabilities tenor by tenor and
    returns a log-linear survival curve with flat extrapolation.

    Parameters
    ----------
    quotes
        CDS market quotes to calibrate.
    valuation_date
        Curve valuation date.
    discount_curve
        Discount curve used for CDS pricing.
    reference_data
        Optional per-instrument reference metadata such as coupon and tenor.
    recovery_rate
        Optional global recovery-rate override.
    payment_frequency
        CDS premium payment frequency.
    day_count_convention
        Day-count convention for premium accrual.
    currency
        Default currency used when the quote omits one.
    calendar
        Calendar used to build the CDS schedule.
    business_day_convention
        Business-day adjustment rule for premium dates.
    end_of_month
        Whether to preserve end-of-month scheduling.
    accrued_on_default_fraction
        Fraction of the premium period accrued on default.
    default_timing_fraction
        Fraction of the premium period used to place default timing.
    notional
        Calibration notional.
    max_iterations
        Maximum bisection iterations per bootstrap point.
    tolerance
        Absolute PV tolerance used to stop the bootstrap.

    Returns
    -------
    CdsBootstrapResult
        Bootstrapped credit curve and calibration points.
    """

    if not quotes:
        raise ValueError("bootstrap_credit_curve requires at least one CDS quote.")

    resolved_frequency = _coerce_frequency(payment_frequency)
    resolved_day_count = _coerce_day_count(day_count_convention)
    resolved_currency = _coerce_currency(currency)
    resolved_calendar = _coerce_calendar(calendar)
    resolved_business_day_convention = _coerce_business_day_convention(business_day_convention)
    resolved_recovery_rate = None if recovery_rate is None else _to_decimal(recovery_rate)
    resolved_accrued = _to_decimal(accrued_on_default_fraction)
    resolved_notional = _to_decimal(notional)
    tolerance_value = _to_decimal(tolerance)

    instruments = _build_bootstrap_instruments(
        quotes,
        valuation_date=valuation_date,
        reference_data=reference_data,
        recovery_rate=resolved_recovery_rate,
        payment_frequency=resolved_frequency,
        day_count_convention=resolved_day_count,
        default_currency=resolved_currency,
        calendar=resolved_calendar,
        business_day_convention=resolved_business_day_convention,
        end_of_month=end_of_month,
        accrued_on_default_fraction=resolved_accrued,
        notional=resolved_notional,
    )
    curve_recovery = resolved_recovery_rate if resolved_recovery_rate is not None else instruments[0].contract.recovery_rate
    from fuggers_py.pricers.credit import CdsPricer

    pricer = CdsPricer(default_timing_fraction=_to_decimal(default_timing_fraction))

    maturity_tenors: list[Decimal] = []
    survival_probabilities: list[Decimal] = []
    points: list[CdsBootstrapPoint] = []

    for instrument in instruments:
        previous_survival = survival_probabilities[-1] if survival_probabilities else Decimal(1)
        lower = Decimal("1e-12")
        upper = previous_survival

        def pv_for(candidate_survival: Decimal) -> Decimal:
            candidate_curve = _build_credit_curve(
                valuation_date,
                [*maturity_tenors, instrument.maturity_tenor],
                [*survival_probabilities, candidate_survival],
                curve_recovery,
            )
            return pricer.pv(
                instrument.contract,
                AnalyticsCurves(discount_curve=discount_curve, credit_curve=candidate_curve),
            )

        f_upper = pv_for(upper)
        if abs(f_upper) <= tolerance_value:
            solved_survival = upper
        else:
            f_lower = pv_for(lower)
            if abs(f_lower) <= tolerance_value:
                solved_survival = lower
            elif f_lower * f_upper > Decimal(0):
                raise ValueError(
                    f"Could not bracket CDS bootstrap root for {instrument.quote.instrument_id}: "
                    f"pv(lower)={f_lower}, pv(upper)={f_upper}."
                )
            else:
                solved_survival = upper
                left = lower
                right = upper
                left_value = f_lower
                for _ in range(max_iterations):
                    midpoint = (left + right) / Decimal(2)
                    mid_value = pv_for(midpoint)
                    solved_survival = midpoint
                    if abs(mid_value) <= tolerance_value or abs(right - left) <= tolerance_value:
                        break
                    if left_value * mid_value <= Decimal(0):
                        right = midpoint
                    else:
                        left = midpoint
                        left_value = mid_value

        maturity_tenors.append(instrument.maturity_tenor)
        survival_probabilities.append(solved_survival)
        calibrated_curve = _build_credit_curve(valuation_date, maturity_tenors, survival_probabilities, curve_recovery)
        pricing = pricer.price(
            instrument.contract,
            AnalyticsCurves(discount_curve=discount_curve, credit_curve=calibrated_curve),
        )
        previous_tenor = maturity_tenors[-2] if len(maturity_tenors) > 1 else Decimal(0)
        previous_survival = survival_probabilities[-2] if len(survival_probabilities) > 1 else Decimal(1)
        interval = instrument.maturity_tenor - previous_tenor
        if interval == Decimal(0):
            hazard_rate = Decimal(0)
        else:
            hazard_rate = Decimal(
                str(-math.log(float(solved_survival / previous_survival)) / float(interval))
            )
        points.append(
            CdsBootstrapPoint(
                instrument_id=instrument.quote.instrument_id,
                maturity_date=instrument.contract.maturity_date,
                maturity_tenor=instrument.maturity_tenor,
                survival_probability=solved_survival,
                hazard_rate=hazard_rate,
                market_par_spread=instrument.quote.par_spread,
                market_upfront=instrument.quote.upfront,
                fitted_par_spread=pricing.par_spread,
                fitted_upfront=pricing.upfront,
                running_spread=instrument.contract.running_spread,
                recovery_rate=instrument.contract.recovery_rate,
            )
        )

    return CdsBootstrapResult(
        credit_curve=_build_credit_curve(valuation_date, maturity_tenors, survival_probabilities, curve_recovery),
        points=tuple(points),
        recovery_rate=curve_recovery,
    )


__all__ = [
    "CdsBootstrapPoint",
    "CdsBootstrapResult",
    "bootstrap_credit_curve",
]
