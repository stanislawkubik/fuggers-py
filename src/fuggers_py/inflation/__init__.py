"""Public inflation products, pricing, and reference helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import ClassVar, Protocol, runtime_checkable

from fuggers_py._core import CalendarId, PayReceive
from fuggers_py._core.calendars import BusinessDayConvention
from fuggers_py._core.daycounts import DayCountConvention
from fuggers_py._core.ids import InstrumentId
from fuggers_py._core.types import Currency, Date, Frequency
from fuggers_py.rates.products import AccrualPeriod, ScheduleDefinition

from .analytics import (
    LinkerSwapParityCheck,
    breakeven_inflation_rate,
    linker_swap_parity_check,
    nominal_real_yield_basis,
    nominal_real_yield_spread,
)
from .reference import (
    InflationConvention,
    InflationError,
    InflationIndexDefinition,
    InvalidObservationLag,
    MissingInflationFixing,
    TreasuryAuctionedTipsRow,
    USD_CPI_U_NSA,
    UnsupportedInflationInterpolation,
    load_monthly_cpi_fixings_csv,
    load_monthly_cpi_fixings_json,
    load_treasury_auctioned_tips_csv,
    load_treasury_auctioned_tips_json,
    parse_bls_cpi_json,
    parse_fred_cpi_csv,
    parse_monthly_cpi_fixings_csv,
    parse_monthly_cpi_fixings_json,
    parse_treasury_auctioned_tips_csv,
    parse_treasury_auctioned_tips_json,
    reference_cpi,
    reference_index_ratio,
    tips_bond_from_treasury_auction_row,
    treasury_cpi_source_from_fixings,
)


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _default_schedule_definition() -> ScheduleDefinition:
    return ScheduleDefinition(
        frequency=Frequency.SEMI_ANNUAL,
        calendar=CalendarId.sifma(),
        business_day_convention=BusinessDayConvention.MODIFIED_FOLLOWING,
    )


@dataclass(frozen=True, slots=True)
class ZeroCouponInflationSwap:
    """Single-payment zero-coupon inflation swap."""

    KIND: ClassVar[str] = "rates.swap.inflation.zero_coupon"

    trade_date: Date = field(default_factory=lambda: Date.from_ymd(1970, 1, 1))
    maturity_date: Date = field(default_factory=lambda: Date.from_ymd(1970, 1, 2))
    notional: Decimal = Decimal(100)
    fixed_rate: Decimal = Decimal(0)
    pay_receive: PayReceive | str = PayReceive.PAY
    inflation_convention: InflationConvention = USD_CPI_U_NSA
    effective_date: Date | None = None
    currency: Currency | str = Currency.USD
    payment_calendar: CalendarId | str = CalendarId.sifma()
    business_day_convention: BusinessDayConvention | str = BusinessDayConvention.MODIFIED_FOLLOWING
    instrument_id: InstrumentId | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "notional", _to_decimal(self.notional))
        object.__setattr__(self, "fixed_rate", _to_decimal(self.fixed_rate))
        object.__setattr__(self, "pay_receive", PayReceive.parse(self.pay_receive))
        if not isinstance(self.currency, Currency):
            object.__setattr__(self, "currency", Currency.from_code(str(self.currency)))
        if not isinstance(self.payment_calendar, CalendarId):
            object.__setattr__(self, "payment_calendar", CalendarId.new(str(self.payment_calendar)))
        if not isinstance(self.business_day_convention, BusinessDayConvention):
            normalized = str(self.business_day_convention).strip().upper().replace("-", "_").replace(" ", "_")
            object.__setattr__(self, "business_day_convention", BusinessDayConvention[normalized])
        if self.instrument_id is not None:
            object.__setattr__(self, "instrument_id", InstrumentId.parse(self.instrument_id))
        if self.effective_date is None:
            calendar = self.payment_calendar.to_calendar()
            object.__setattr__(self, "effective_date", calendar.settlement_date(self.trade_date, 2))
        if self.inflation_convention is None:
            raise ValueError("ZeroCouponInflationSwap requires an inflation_convention.")
        if self.maturity_date <= self.effective_date:
            raise ValueError("ZeroCouponInflationSwap requires maturity_date after effective_date.")
        if self.notional <= Decimal(0):
            raise ValueError("ZeroCouponInflationSwap notional must be positive.")
        if self.currency is not self.inflation_convention.currency:
            raise ValueError("ZeroCouponInflationSwap currency must match inflation_convention.currency.")

    @classmethod
    def new(
        cls,
        *,
        trade_date: Date,
        maturity_date: Date,
        notional: Decimal,
        fixed_rate: Decimal,
        pay_receive: PayReceive | str = PayReceive.PAY,
        inflation_convention: InflationIndexDefinition = USD_CPI_U_NSA,
        effective_date: Date | None = None,
        currency: Currency | str = Currency.USD,
        payment_calendar: CalendarId | str = CalendarId.sifma(),
        business_day_convention: BusinessDayConvention | str = BusinessDayConvention.MODIFIED_FOLLOWING,
        instrument_id: InstrumentId | None = None,
    ) -> "ZeroCouponInflationSwap":
        return cls(
            trade_date=trade_date,
            effective_date=effective_date,
            maturity_date=maturity_date,
            notional=notional,
            fixed_rate=fixed_rate,
            pay_receive=pay_receive,
            currency=currency,
            inflation_convention=inflation_convention,
            payment_calendar=payment_calendar,
            business_day_convention=business_day_convention,
            instrument_id=instrument_id,
        )

    def payment_date(self) -> Date:
        return self.payment_calendar.to_calendar().adjust(self.maturity_date, self.business_day_convention)

    @property
    def kind(self) -> str:
        return self.KIND

    def fixed_leg_sign(self) -> Decimal:
        return self.pay_receive.sign()

    def inflation_leg_sign(self) -> Decimal:
        return self.pay_receive.opposite().sign()

    def fixed_leg_year_fraction(self) -> Decimal:
        return Decimal(1)

    def index_initial_date(self) -> Date:
        return self.effective_date

    def index_final_date(self) -> Date:
        return self.maturity_date


@dataclass(frozen=True, slots=True)
class StandardCouponInflationSwap:
    """Schedule-driven standard coupon inflation swap."""

    KIND: ClassVar[str] = "rates.swap.inflation.standard_coupon"

    trade_date: Date = field(default_factory=lambda: Date.from_ymd(1970, 1, 1))
    maturity_date: Date = field(default_factory=lambda: Date.from_ymd(1970, 1, 2))
    notional: Decimal = Decimal(100)
    fixed_rate: Decimal = Decimal(0)
    pay_receive: PayReceive | str = PayReceive.PAY
    inflation_convention: InflationConvention = USD_CPI_U_NSA
    effective_date: Date | None = None
    currency: Currency | str = Currency.USD
    schedule: ScheduleDefinition = field(default_factory=_default_schedule_definition)
    inflation_schedule: ScheduleDefinition | None = None
    fixed_day_count_convention: DayCountConvention | str = DayCountConvention.ACT_365_FIXED
    normalize_effective_date_to_reference_month_start: bool = True
    fixed_periods_override: tuple[AccrualPeriod, ...] = ()
    inflation_periods_override: tuple[AccrualPeriod, ...] = ()
    instrument_id: InstrumentId | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "notional", _to_decimal(self.notional))
        object.__setattr__(self, "fixed_rate", _to_decimal(self.fixed_rate))
        object.__setattr__(self, "pay_receive", PayReceive.parse(self.pay_receive))
        if not isinstance(self.currency, Currency):
            object.__setattr__(self, "currency", Currency.from_code(str(self.currency)))
        if not isinstance(self.fixed_day_count_convention, DayCountConvention):
            normalized = str(self.fixed_day_count_convention).strip().upper().replace("/", "_")
            object.__setattr__(self, "fixed_day_count_convention", DayCountConvention[normalized])
        if self.instrument_id is not None:
            object.__setattr__(self, "instrument_id", InstrumentId.parse(self.instrument_id))

        resolved_effective = self.effective_date
        if resolved_effective is None:
            calendar = self.schedule.calendar.to_calendar()
            resolved_effective = calendar.settlement_date(self.trade_date, 2)
        if self.normalize_effective_date_to_reference_month_start:
            resolved_effective = self._normalize_to_reference_month_start(resolved_effective)
        object.__setattr__(self, "effective_date", resolved_effective)
        if self.inflation_schedule is None:
            object.__setattr__(self, "inflation_schedule", self.schedule)
        object.__setattr__(self, "fixed_periods_override", tuple(self.fixed_periods_override))
        object.__setattr__(self, "inflation_periods_override", tuple(self.inflation_periods_override))

        if self.inflation_convention is None:
            raise ValueError("StandardCouponInflationSwap requires an inflation_convention.")
        if self.maturity_date <= self.effective_date:
            raise ValueError("StandardCouponInflationSwap requires maturity_date after effective_date.")
        if self.notional <= Decimal(0):
            raise ValueError("StandardCouponInflationSwap notional must be positive.")
        if self.currency is not self.inflation_convention.currency:
            raise ValueError("StandardCouponInflationSwap currency must match inflation_convention.currency.")
        if self.currency is not Currency.USD or self.inflation_convention.index_source != "CPURNSA":
            raise ValueError("StandardCouponInflationSwap first release supports USD CPI-U / CPURNSA only.")
        if self.schedule.frequency.is_zero() or self.inflation_schedule.frequency.is_zero():
            raise ValueError("StandardCouponInflationSwap requires non-zero coupon frequency.")
        self._validate_periods()

    @classmethod
    def new(
        cls,
        *,
        trade_date: Date,
        maturity_date: Date,
        notional: Decimal,
        fixed_rate: Decimal,
        pay_receive: PayReceive | str = PayReceive.PAY,
        inflation_convention: InflationIndexDefinition = USD_CPI_U_NSA,
        effective_date: Date | None = None,
        currency: Currency | str = Currency.USD,
        schedule: ScheduleDefinition | None = None,
        inflation_schedule: ScheduleDefinition | None = None,
        fixed_day_count_convention: DayCountConvention | str = DayCountConvention.ACT_365_FIXED,
        normalize_effective_date_to_reference_month_start: bool = True,
        fixed_periods: tuple[AccrualPeriod, ...] | None = None,
        inflation_periods: tuple[AccrualPeriod, ...] | None = None,
        instrument_id: InstrumentId | None = None,
    ) -> "StandardCouponInflationSwap":
        return cls(
            trade_date=trade_date,
            maturity_date=maturity_date,
            notional=notional,
            fixed_rate=fixed_rate,
            pay_receive=pay_receive,
            inflation_convention=inflation_convention,
            effective_date=effective_date,
            currency=currency,
            schedule=_default_schedule_definition() if schedule is None else schedule,
            inflation_schedule=inflation_schedule,
            fixed_day_count_convention=fixed_day_count_convention,
            normalize_effective_date_to_reference_month_start=normalize_effective_date_to_reference_month_start,
            fixed_periods_override=() if fixed_periods is None else tuple(fixed_periods),
            inflation_periods_override=() if inflation_periods is None else tuple(inflation_periods),
            instrument_id=instrument_id,
        )

    def fixed_leg_sign(self) -> Decimal:
        return self.pay_receive.sign()

    def inflation_leg_sign(self) -> Decimal:
        return self.pay_receive.opposite().sign()

    def fixed_periods(self) -> tuple[AccrualPeriod, ...]:
        if self.fixed_periods_override:
            return self.fixed_periods_override
        return self.schedule.accrual_periods(
            self.effective_date,
            self.maturity_date,
            day_count_convention=self.fixed_day_count_convention,
        )

    def inflation_periods(self) -> tuple[AccrualPeriod, ...]:
        if self.inflation_periods_override:
            return self.inflation_periods_override
        return self.inflation_schedule.accrual_periods(
            self.effective_date,
            self.maturity_date,
            day_count_convention=DayCountConvention.ACT_365_FIXED,
        )

    def payment_dates(self) -> tuple[Date, ...]:
        return tuple(period.payment_date for period in self.fixed_periods())

    @property
    def kind(self) -> str:
        return self.KIND

    def _normalize_to_reference_month_start(self, date: Date) -> Date:
        calendar = self.schedule.calendar.to_calendar()
        reference_month_start = Date.from_ymd(date.year(), date.month(), 1)
        return calendar.adjust(reference_month_start, BusinessDayConvention.FOLLOWING)

    def _validate_periods(self) -> None:
        fixed_periods = self.fixed_periods()
        inflation_periods = self.inflation_periods()
        if len(fixed_periods) == 0 or len(inflation_periods) == 0:
            raise ValueError("StandardCouponInflationSwap requires at least one coupon period.")
        if len(fixed_periods) != len(inflation_periods):
            raise ValueError("StandardCouponInflationSwap requires matching fixed and inflation schedule lengths.")
        for fixed_period, inflation_period in zip(fixed_periods, inflation_periods, strict=True):
            if fixed_period.start_date >= fixed_period.end_date:
                raise ValueError("StandardCouponInflationSwap fixed schedule contains an invalid accrual period.")
            if inflation_period.start_date >= inflation_period.end_date:
                raise ValueError("StandardCouponInflationSwap inflation schedule contains an invalid accrual period.")
            if (
                fixed_period.start_date != inflation_period.start_date
                or fixed_period.end_date != inflation_period.end_date
                or fixed_period.payment_date != inflation_period.payment_date
            ):
                raise ValueError(
                    "StandardCouponInflationSwap requires aligned fixed and inflation schedules in the first release."
                )
        if fixed_periods[0].start_date != self.effective_date:
            raise ValueError("StandardCouponInflationSwap fixed schedule must start on effective_date.")
        if fixed_periods[-1].end_date != self.maturity_date:
            raise ValueError("StandardCouponInflationSwap fixed schedule must end on maturity_date.")


def _curve_reference_date(curve: object) -> Date:
    return getattr(curve, "reference_date")


def _tenor_from_curve_date(curve: object, date: Date) -> float:
    reference_date = _curve_reference_date(curve)
    if date < reference_date:
        raise ValueError("Curve date lookup requires date >= curve.reference_date.")
    if date == reference_date:
        return 0.0
    day_count_label = getattr(getattr(curve, "spec"), "day_count")
    normalized = str(day_count_label).strip().upper().replace(" ", "")
    aliases = {
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
    convention_name = aliases.get(normalized, normalized)
    day_count = DayCountConvention[convention_name].to_day_count()
    return float(day_count.year_fraction(reference_date, date))


def _discount_factor_at_date(curve: object, date: Date) -> Decimal:
    tenor = _tenor_from_curve_date(curve, date)
    if tenor <= 0.0:
        return Decimal(1)
    return _to_decimal(curve.discount_factor_at(tenor))


def _curve_supports_discounting(curve: object | None) -> bool:
    return curve is not None and hasattr(curve, "discount_factor_at") and hasattr(curve, "reference_date")


def _curve_supports_inflation_projection(curve: object | None) -> bool:
    return curve is not None and (
        hasattr(curve, "projected_reference_cpi")
        or hasattr(curve, "projected_index_ratio")
        or hasattr(curve, "reference_cpi")
        or hasattr(curve, "get_reference_cpi")
        or hasattr(curve, "get_inflation_fixing")
    )


def _inflation_projection_keys(convention: InflationConvention) -> tuple[str, ...]:
    normalized_name = convention.name.strip().upper().replace(" ", "_").replace("-", "_")
    family = convention.family.strip().upper()
    index_source = convention.index_source.strip().upper()
    currency = convention.currency.code()
    ordered: dict[str, None] = {}
    for key in (
        index_source,
        family,
        normalized_name,
        "INFLATION",
        "CPI",
        f"{currency}-{index_source}",
        f"{currency}-{family}",
        f"{currency}-INFLATION",
    ):
        if key:
            ordered[key] = None
    for alias in convention.lookup_names():
        normalized = alias.strip().upper().replace(" ", "_").replace("-", "_")
        if normalized:
            ordered[normalized] = None
            ordered[f"{currency}-{normalized}"] = None
    return tuple(ordered)


def _resolve_discount_curve(curves: object | None, currency: Currency) -> object:
    if curves is None:
        raise ValueError("Inflation swap pricing requires a nominal discount curve or curves bundle.")
    environment = getattr(curves, "multicurve_environment", None)
    if environment is not None and hasattr(environment, "discount_curve"):
        curve = environment.discount_curve(currency)
        if _curve_supports_discounting(curve):
            return curve
    for candidate in (
        getattr(curves, "discount_curve", None),
        getattr(curves, "collateral_curve", None),
    ):
        if _curve_supports_discounting(candidate):
            return candidate
    raise ValueError(f"Missing discount curve for currency {currency.code()}.")


def _resolve_inflation_projection(curves: object | None, *, convention: InflationConvention) -> object:
    if curves is None:
        raise ValueError("Inflation swap pricing requires an inflation projection or fixing source.")
    inflation_curve = getattr(curves, "inflation_curve", None)
    if _curve_supports_inflation_projection(inflation_curve):
        return inflation_curve
    inflation_curves = getattr(curves, "inflation_curves", {})
    for key in _inflation_projection_keys(convention):
        curve = inflation_curves.get(key)
        if curve is not None:
            return curve
        lowered = key.lower()
        for candidate_key, candidate_value in inflation_curves.items():
            if str(candidate_key).lower() == lowered:
                return candidate_value
    projection_curves = getattr(curves, "projection_curves", {})
    for key in _inflation_projection_keys(convention):
        curve = projection_curves.get(key)
        if curve is not None:
            return curve
        lowered = key.lower()
        for candidate_key, candidate_value in projection_curves.items():
            if str(candidate_key).lower() == lowered:
                return candidate_value
    forward_curve = getattr(curves, "forward_curve", None)
    if _curve_supports_inflation_projection(forward_curve):
        return forward_curve
    raise ValueError(
        f"Missing inflation projection for {convention.currency.code()} {convention.index_source}."
    )


@runtime_checkable
class InflationProjection(Protocol):
    """Shared interface for direct reference-index forecasts."""

    def reference_cpi(self, date: Date, convention) -> Decimal:
        ...


@dataclass(frozen=True, slots=True)
class ZeroCouponInflationSwapPricingResult:
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
        curves: object | None = None,
        *,
        discount_curve: object | None = None,
    ) -> Decimal:
        if isinstance(swap, StandardCouponInflationSwap):
            return self._standard_coupon_fixed_leg_pv(swap, curves, discount_curve=discount_curve)
        return self._zero_coupon_fixed_leg_pv(swap, curves, discount_curve=discount_curve)

    def inflation_leg_pv(
        self,
        swap: InflationSwapInstrument,
        curves: object | None = None,
        *,
        discount_curve: object | None = None,
        inflation_projection: object | None = None,
    ) -> Decimal:
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
        curves: object | None = None,
        *,
        discount_curve: object | None = None,
        inflation_projection: object | None = None,
    ) -> Decimal:
        return self.fixed_leg_pv(swap, curves, discount_curve=discount_curve) + self.inflation_leg_pv(
            swap,
            curves,
            discount_curve=discount_curve,
            inflation_projection=inflation_projection,
        )

    def par_fixed_rate(
        self,
        swap: InflationSwapInstrument,
        curves: object | None = None,
        *,
        discount_curve: object | None = None,
        inflation_projection: object | None = None,
    ) -> Decimal:
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
        curves: object | None = None,
        *,
        discount_curve: object | None = None,
        bump: object = Decimal("0.0001"),
    ) -> Decimal:
        return swap.fixed_leg_sign() * self.fixed_leg_annuity(
            swap,
            curves,
            discount_curve=discount_curve,
        ) * _to_decimal(bump)

    def fixed_leg_annuity(
        self,
        swap: InflationSwapInstrument,
        curves: object | None = None,
        *,
        discount_curve: object | None = None,
    ) -> Decimal:
        curve = discount_curve or _resolve_discount_curve(curves, swap.currency)
        if isinstance(swap, StandardCouponInflationSwap):
            total = Decimal(0)
            for period in swap.fixed_periods():
                total += swap.notional * period.year_fraction * _discount_factor_at_date(curve, period.payment_date)
            return total
        return swap.notional * swap.fixed_leg_year_fraction() * _discount_factor_at_date(curve, swap.payment_date())

    def reference_cpi(
        self,
        swap: InflationSwapInstrument,
        date: Date,
        *,
        curves: object | None = None,
        inflation_projection: object | None = None,
    ) -> Decimal:
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
        curves: object | None = None,
        *,
        discount_curve: object | None = None,
        inflation_projection: object | None = None,
    ) -> InflationSwapPricingResult:
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
        curves: object | None = None,
        *,
        discount_curve: object | None = None,
    ) -> Decimal:
        curve = discount_curve or _resolve_discount_curve(curves, swap.currency)
        return (
            swap.fixed_leg_sign()
            * swap.notional
            * swap.fixed_rate
            * swap.fixed_leg_year_fraction()
            * _discount_factor_at_date(curve, swap.payment_date())
        )

    def _zero_coupon_inflation_leg_pv(
        self,
        swap: ZeroCouponInflationSwap,
        curves: object | None = None,
        *,
        discount_curve: object | None = None,
        inflation_projection: object | None = None,
    ) -> Decimal:
        curve = discount_curve or _resolve_discount_curve(curves, swap.currency)
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
        return swap.inflation_leg_sign() * swap.notional * payoff * _discount_factor_at_date(curve, swap.payment_date())

    def _price_zero_coupon(
        self,
        swap: ZeroCouponInflationSwap,
        curves: object | None = None,
        *,
        discount_curve: object | None = None,
        inflation_projection: object | None = None,
    ) -> ZeroCouponInflationSwapPricingResult:
        curve = discount_curve or _resolve_discount_curve(curves, swap.currency)
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
            * _discount_factor_at_date(curve, swap.payment_date())
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
            discount_factor=_discount_factor_at_date(curve, swap.payment_date()),
            fixed_leg_annuity=fixed_leg_annuity,
        )

    def _standard_coupon_period_pricings(
        self,
        swap: StandardCouponInflationSwap,
        curves: object | None = None,
        *,
        discount_curve: object | None = None,
        inflation_projection: object | None = None,
    ) -> tuple[StandardCouponInflationSwapPeriodPricing, ...]:
        curve = discount_curve or _resolve_discount_curve(curves, swap.currency)
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
            discount_factor = _discount_factor_at_date(curve, fixed_period.payment_date)
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
        curves: object | None = None,
        *,
        discount_curve: object | None = None,
    ) -> Decimal:
        fixed_leg_annuity = self.fixed_leg_annuity(swap, curves, discount_curve=discount_curve)
        return swap.fixed_leg_sign() * fixed_leg_annuity * swap.fixed_rate

    def _standard_coupon_inflation_leg_pv(
        self,
        swap: StandardCouponInflationSwap,
        curves: object | None = None,
        *,
        discount_curve: object | None = None,
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
        curves: object | None = None,
        *,
        discount_curve: object | None = None,
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
    def _resolve_inflation_projection(
        swap: InflationSwapInstrument,
        *,
        curves: object | None,
        inflation_projection: object | None,
    ) -> object:
        if inflation_projection is not None:
            return inflation_projection
        return _resolve_inflation_projection(curves, convention=swap.inflation_convention)


__all__ = [
    "InflationConvention",
    "InflationError",
    "InflationIndexDefinition",
    "InflationProjection",
    "InflationSwapPricer",
    "InvalidObservationLag",
    "LinkerSwapParityCheck",
    "MissingInflationFixing",
    "StandardCouponInflationSwap",
    "StandardCouponInflationSwapPeriodPricing",
    "StandardCouponInflationSwapPricingResult",
    "TreasuryAuctionedTipsRow",
    "USD_CPI_U_NSA",
    "UnsupportedInflationInterpolation",
    "ZeroCouponInflationSwap",
    "ZeroCouponInflationSwapPricingResult",
    "breakeven_inflation_rate",
    "linker_swap_parity_check",
    "load_monthly_cpi_fixings_csv",
    "load_monthly_cpi_fixings_json",
    "load_treasury_auctioned_tips_csv",
    "load_treasury_auctioned_tips_json",
    "nominal_real_yield_basis",
    "nominal_real_yield_spread",
    "parse_bls_cpi_json",
    "parse_fred_cpi_csv",
    "parse_monthly_cpi_fixings_csv",
    "parse_monthly_cpi_fixings_json",
    "parse_treasury_auctioned_tips_csv",
    "parse_treasury_auctioned_tips_json",
    "reference_cpi",
    "reference_index_ratio",
    "tips_bond_from_treasury_auction_row",
    "treasury_cpi_source_from_fixings",
]
