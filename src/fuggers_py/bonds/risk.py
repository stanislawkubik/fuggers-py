"""Bond risk analytics owned by the public bonds package."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from math import ceil, exp, floor, isfinite, log
from statistics import NormalDist, mean, stdev
from typing import Protocol

from fuggers_py._core import ActActIcma, Compounding, Date, Tenor, Yield
from fuggers_py.curves import DiscountingCurve, RateSpace

from .pricing import BondPricer

DEFAULT_BUMP_SIZE = 1e-4
SMALL_BUMP_SIZE = 1e-5
STANDARD_KEY_RATE_TENORS: tuple[Tenor, ...] = (
    Tenor.parse("6M"),
    Tenor.parse("1Y"),
    Tenor.parse("2Y"),
    Tenor.parse("3Y"),
    Tenor.parse("5Y"),
    Tenor.parse("7Y"),
    Tenor.parse("10Y"),
    Tenor.parse("20Y"),
    Tenor.parse("30Y"),
)


class _CashFlowLike(Protocol):
    date: Date
    accrual_start: Date | None
    accrual_end: Date | None

    def factored_amount(self) -> Decimal:
        ...


class _BondLike(Protocol):
    def rules(self):
        ...

    def cash_flows(self) -> list[_CashFlowLike]:
        ...


def _to_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _compounding_kind_name(method: object) -> str:
    kind = getattr(method, "kind", None)
    value = getattr(kind, "value", kind)
    if not isinstance(value, str):
        raise ValueError("Unsupported compounding method.")
    return value


def _core_compounding_for(method: object) -> Compounding:
    kind_name = _compounding_kind_name(method)
    if kind_name == "CONTINUOUS":
        return Compounding.CONTINUOUS
    if kind_name in {"SIMPLE", "DISCOUNT"}:
        return Compounding.SIMPLE

    frequency = getattr(method, "frequency", None)
    if frequency == 1:
        return Compounding.ANNUAL
    if frequency == 2:
        return Compounding.SEMI_ANNUAL
    if frequency == 4:
        return Compounding.QUARTERLY
    if frequency == 12:
        return Compounding.MONTHLY
    return Compounding.ANNUAL


def _yield_to_engine_rate(ytm: Yield, *, rules: object) -> float:
    compounding = getattr(rules, "compounding")
    target_compounding = _core_compounding_for(compounding)
    return float(ytm.convert_to(target_compounding).value())


@dataclass(frozen=True, slots=True)
class _CashFlowData:
    years: float
    amount: float


def _prepare_cashflows(
    cashflows: Sequence[_CashFlowLike],
    *,
    settlement_date: Date,
    rules: object,
) -> list[_CashFlowData]:
    day_count = rules.accrual_day_count_obj()
    future = [cashflow for cashflow in cashflows if cashflow.date > settlement_date]
    future.sort(key=lambda cashflow: cashflow.date)

    if isinstance(day_count, ActActIcma) and all(
        cashflow.accrual_start is not None and cashflow.accrual_end is not None for cashflow in future
    ):
        times: list[float] = []
        cumulative = 0.0
        for index, cashflow in enumerate(future):
            accrual_start = cashflow.accrual_start
            accrual_end = cashflow.accrual_end
            if accrual_start is None or accrual_end is None:  # pragma: no cover - defensive
                break

            if index == 0 and settlement_date > accrual_start:
                period = day_count.year_fraction_with_period(
                    settlement_date,
                    accrual_end,
                    accrual_start,
                    accrual_end,
                )
            else:
                period = day_count.year_fraction_with_period(
                    accrual_start,
                    accrual_end,
                    accrual_start,
                    accrual_end,
                )
            cumulative += float(period)
            times.append(cumulative)

        return [
            _CashFlowData(years=years, amount=float(cashflow.factored_amount()))
            for years, cashflow in zip(times, future, strict=True)
        ]

    return [
        _CashFlowData(
            years=float(day_count.year_fraction(settlement_date, cashflow.date)),
            amount=float(cashflow.factored_amount()),
        )
        for cashflow in future
    ]


def _discount_factor_second_derivative(
    yield_rate: float,
    years: float,
    *,
    rules: object,
) -> float:
    compounding = getattr(rules, "compounding")
    kind_name = _compounding_kind_name(compounding)
    if years == 0.0:
        return 0.0

    if kind_name in {"PERIODIC", "ACTUAL_PERIOD"}:
        frequency = getattr(compounding, "frequency", None)
        if frequency is None:
            raise ValueError("Periodic compounding requires a frequency.")
        base = 1.0 + yield_rate / float(frequency)
        if base <= 0.0:
            raise ValueError("Yield is outside the valid periodic-compounding domain.")
        discount_factor = float(compounding.discount_factor(yield_rate, years))
        return years * (years + 1.0 / float(frequency)) * discount_factor / (base * base)

    if kind_name == "CONTINUOUS":
        discount_factor = float(compounding.discount_factor(yield_rate, years))
        return years * years * discount_factor

    if kind_name in {"SIMPLE", "DISCOUNT"}:
        base = 1.0 + yield_rate * years
        if base <= 0.0:
            raise ValueError("Yield is outside the valid simple-compounding domain.")
        return 2.0 * years * years / (base * base * base)

    raise ValueError(f"Unsupported compounding kind: {kind_name}.")


@dataclass(frozen=True, slots=True)
class _AnalyticalRiskComponents:
    dirty_price: float
    modified_duration: float
    macaulay_duration: float
    convexity: float
    dv01: float


def _analytical_risk_components(
    bond: _BondLike,
    ytm: Yield,
    settlement_date: Date,
) -> _AnalyticalRiskComponents:
    rules = bond.rules()
    yield_rate = _yield_to_engine_rate(ytm, rules=rules)
    cashflows = _prepare_cashflows(bond.cash_flows(), settlement_date=settlement_date, rules=rules)
    if not cashflows:
        return _AnalyticalRiskComponents(
            dirty_price=0.0,
            modified_duration=0.0,
            macaulay_duration=0.0,
            convexity=0.0,
            dv01=0.0,
        )

    compounding = rules.compounding
    dirty_price = 0.0
    first_derivative = 0.0
    second_derivative = 0.0
    macaulay_numerator = 0.0

    for cashflow in cashflows:
        discount_factor = float(compounding.discount_factor(yield_rate, cashflow.years))
        present_value = cashflow.amount * discount_factor
        dirty_price += present_value
        first_derivative += cashflow.amount * float(compounding.discount_factor_derivative(yield_rate, cashflow.years))
        second_derivative += cashflow.amount * _discount_factor_second_derivative(
            yield_rate,
            cashflow.years,
            rules=rules,
        )
        macaulay_numerator += cashflow.years * present_value

    if dirty_price == 0.0:
        return _AnalyticalRiskComponents(
            dirty_price=0.0,
            modified_duration=0.0,
            macaulay_duration=0.0,
            convexity=0.0,
            dv01=0.0,
        )

    modified_duration_value = -(first_derivative / dirty_price)
    macaulay_duration_value = macaulay_numerator / dirty_price
    convexity_value = second_derivative / dirty_price
    dv01_value = -first_derivative * DEFAULT_BUMP_SIZE
    return _AnalyticalRiskComponents(
        dirty_price=dirty_price,
        modified_duration=modified_duration_value,
        macaulay_duration=macaulay_duration_value,
        convexity=convexity_value,
        dv01=dv01_value,
    )


def _price_at_yield(bond: _BondLike, ytm: Yield, settlement_date: Date) -> float:
    pricer = BondPricer()
    rules = bond.rules()
    return float(
        pricer.engine.dirty_price_from_yield(
            bond.cash_flows(),
            yield_rate=_yield_to_engine_rate(ytm, rules=rules),
            settlement_date=settlement_date,
            rules=rules,
        )
    )


def _tenor_years(value: Tenor | float | int | Decimal) -> float:
    if isinstance(value, Tenor):
        return float(value.to_years_approx())
    return float(value)


class _ShiftedDiscountingCurve(DiscountingCurve):
    __slots__ = ("_base_curve", "_shifted_zero_rate")

    def __init__(self, base_curve: DiscountingCurve, shifted_zero_rate) -> None:
        super().__init__(base_curve.spec)
        self._base_curve = base_curve
        self._shifted_zero_rate = shifted_zero_rate

    @property
    def rate_space(self) -> RateSpace:
        return RateSpace.ZERO

    def max_t(self) -> float:
        return self._base_curve.max_t()

    def rate_at(self, tenor: float) -> float:
        checked_tenor = float(tenor)
        if checked_tenor <= 0.0:
            return 0.0
        return self._base_curve.zero_rate_at(checked_tenor) + float(self._shifted_zero_rate(checked_tenor))

    def discount_factor_at(self, tenor: float) -> float:
        checked_tenor = float(tenor)
        if checked_tenor <= 0.0:
            return 1.0
        shifted_zero_rate = self.rate_at(checked_tenor)
        return exp(-shifted_zero_rate * checked_tenor)


def _parallel_bumped_curve(curve: DiscountingCurve, bump: float) -> DiscountingCurve:
    return _ShiftedDiscountingCurve(curve, lambda tenor: float(bump))


def _key_rate_bumped_curve(
    curve: DiscountingCurve,
    *,
    tenor_grid: Sequence[Tenor | float | int | Decimal],
    key_tenor: Tenor | float | int | Decimal,
    bump: float,
) -> DiscountingCurve:
    grid = sorted({_tenor_years(tenor) for tenor in tenor_grid})
    if not grid:
        raise ValueError("key_rate_bumped_curve requires a non-empty tenor grid.")

    key_years = _tenor_years(key_tenor)
    if key_years not in grid:
        grid.append(key_years)
        grid.sort()

    key_index = grid.index(key_years)
    left = None if key_index == 0 else grid[key_index - 1]
    right = None if key_index == len(grid) - 1 else grid[key_index + 1]

    def shift_at(tenor: float) -> float:
        checked_tenor = float(tenor)
        if left is None and right is None:
            return float(bump)
        if left is None:
            if checked_tenor <= key_years:
                return float(bump)
            if checked_tenor >= right:
                return 0.0
            return float(bump) * (right - checked_tenor) / (right - key_years)
        if right is None:
            if checked_tenor >= key_years:
                return float(bump)
            if checked_tenor <= left:
                return 0.0
            return float(bump) * (checked_tenor - left) / (key_years - left)
        if checked_tenor <= left or checked_tenor >= right:
            return 0.0
        if checked_tenor <= key_years:
            return float(bump) * (checked_tenor - left) / (key_years - left)
        return float(bump) * (right - checked_tenor) / (right - key_years)

    return _ShiftedDiscountingCurve(curve, shift_at)


@dataclass(frozen=True, slots=True)
class BondRiskMetrics:
    modified_duration: Decimal
    macaulay_duration: Decimal
    convexity: Decimal
    dv01: Decimal


@dataclass(frozen=True, slots=True)
class EffectiveDurationCalculator:
    bump: float = DEFAULT_BUMP_SIZE

    def calculate(self, bond: _BondLike, ytm: Yield, settlement_date: Date) -> Decimal:
        return effective_duration(bond, ytm, settlement_date, bump=self.bump)


@dataclass(frozen=True, slots=True)
class BondRiskCalculator:
    bond: _BondLike
    ytm: Yield
    settlement_date: Date
    bump: float = DEFAULT_BUMP_SIZE

    def modified_duration(self) -> Decimal:
        return modified_duration(self.bond, self.ytm, self.settlement_date)

    def macaulay_duration(self) -> Decimal:
        return macaulay_duration(self.bond, self.ytm, self.settlement_date)

    def convexity(self) -> Decimal:
        return analytical_convexity(self.bond, self.ytm, self.settlement_date)

    def dv01(self) -> Decimal:
        return dv01_per_100_face(self.modified_duration(), Decimal(str(_price_at_yield(self.bond, self.ytm, self.settlement_date))))

    def all_metrics(self) -> BondRiskMetrics:
        return BondRiskMetrics(
            modified_duration=self.modified_duration(),
            macaulay_duration=self.macaulay_duration(),
            convexity=self.convexity(),
            dv01=self.dv01(),
        )


@dataclass(frozen=True, slots=True)
class Convexity:
    value: Decimal

    def as_decimal(self) -> Decimal:
        return self.value


@dataclass(frozen=True, slots=True)
class Duration:
    value: Decimal

    def as_decimal(self) -> Decimal:
        return self.value


@dataclass(frozen=True, slots=True)
class DV01:
    value: Decimal

    def as_decimal(self) -> Decimal:
        return self.value


def modified_duration(bond: _BondLike, ytm: Yield, settlement_date: Date) -> Decimal:
    components = _analytical_risk_components(bond, ytm, settlement_date)
    return Decimal(str(components.modified_duration))


def macaulay_duration(bond: _BondLike, ytm: Yield, settlement_date: Date) -> Decimal:
    components = _analytical_risk_components(bond, ytm, settlement_date)
    return Decimal(str(components.macaulay_duration))


def effective_duration(
    bond: _BondLike,
    ytm: Yield,
    settlement_date: Date,
    *,
    bump: float = DEFAULT_BUMP_SIZE,
) -> Decimal:
    pricer = BondPricer()
    rules = bond.rules()
    yield_rate = _yield_to_engine_rate(ytm, rules=rules)
    cashflows = bond.cash_flows()
    base_price = float(
        pricer.engine.dirty_price_from_yield(
            cashflows,
            yield_rate=yield_rate,
            settlement_date=settlement_date,
            rules=rules,
        )
    )
    if base_price == 0.0:
        return Decimal(0)
    price_up = float(
        pricer.engine.dirty_price_from_yield(
            cashflows,
            yield_rate=yield_rate + bump,
            settlement_date=settlement_date,
            rules=rules,
        )
    )
    price_down = float(
        pricer.engine.dirty_price_from_yield(
            cashflows,
            yield_rate=yield_rate - bump,
            settlement_date=settlement_date,
            rules=rules,
        )
    )
    return Decimal(str((price_down - price_up) / (2.0 * base_price * bump)))


def analytical_convexity(bond: _BondLike, ytm: Yield, settlement_date: Date) -> Decimal:
    try:
        components = _analytical_risk_components(bond, ytm, settlement_date)
        return Decimal(str(components.convexity))
    except (ArithmeticError, OverflowError, ValueError):
        return effective_convexity(bond, ytm, settlement_date)


def effective_convexity(
    bond: _BondLike,
    ytm: Yield,
    settlement_date: Date,
    *,
    bump: float = DEFAULT_BUMP_SIZE,
) -> Decimal:
    pricer = BondPricer()
    rules = bond.rules()
    yield_rate = _yield_to_engine_rate(ytm, rules=rules)
    cashflows = bond.cash_flows()
    base_price = float(
        pricer.engine.dirty_price_from_yield(
            cashflows,
            yield_rate=yield_rate,
            settlement_date=settlement_date,
            rules=rules,
        )
    )
    if base_price == 0.0:
        return Decimal(0)
    price_up = float(
        pricer.engine.dirty_price_from_yield(
            cashflows,
            yield_rate=yield_rate + bump,
            settlement_date=settlement_date,
            rules=rules,
        )
    )
    price_down = float(
        pricer.engine.dirty_price_from_yield(
            cashflows,
            yield_rate=yield_rate - bump,
            settlement_date=settlement_date,
            rules=rules,
        )
    )
    return Decimal(str((price_up + price_down - (2.0 * base_price)) / (base_price * bump * bump)))


def price_change_with_convexity(
    modified_duration: object,
    convexity: object,
    price: object,
    yield_change: object,
) -> Decimal:
    modified_duration_value = _to_decimal(modified_duration)
    convexity_value = _to_decimal(convexity)
    price_value = _to_decimal(price)
    yield_change_value = _to_decimal(yield_change)
    return (
        -modified_duration_value * price_value * yield_change_value
        + Decimal("0.5") * convexity_value * price_value * yield_change_value * yield_change_value
    )


def dv01_from_duration(modified_duration: object, dirty_price: object, face: object) -> Decimal:
    modified_duration_value = _to_decimal(modified_duration)
    dirty_price_value = _to_decimal(dirty_price)
    face_value = _to_decimal(face)
    return modified_duration_value * (dirty_price_value / Decimal(100)) * face_value * Decimal("0.0001")


def dv01_from_prices(price_down: object, price_up: object) -> Decimal:
    price_down_value = _to_decimal(price_down)
    price_up_value = _to_decimal(price_up)
    return (price_down_value - price_up_value) / Decimal(2)


def dv01_per_100_face(modified_duration: object, dirty_price: object) -> Decimal:
    return dv01_from_duration(modified_duration, dirty_price, Decimal(100))


def notional_from_dv01(target_dv01: object, modified_duration: object, dirty_price: object) -> Decimal:
    modified_duration_value = _to_decimal(modified_duration)
    dirty_price_value = _to_decimal(dirty_price)
    if modified_duration_value == 0 or dirty_price_value == 0:
        raise ValueError("Modified duration and price must be positive for notional calculation.")
    target_dv01_value = _to_decimal(target_dv01)
    return target_dv01_value / (modified_duration_value * (dirty_price_value / Decimal(100)) * Decimal("0.0001"))


def modified_from_macaulay(macaulay: Decimal, ytm: Yield, *, frequency: int | None = None) -> Decimal:
    resolved_frequency = frequency
    if resolved_frequency is None:
        resolved_frequency = ytm.compounding().periods_per_year() if hasattr(ytm, "compounding") else 2
    periods = int(resolved_frequency) if resolved_frequency else 1
    return macaulay / (Decimal(1) + (ytm.value() / Decimal(periods)))


@dataclass(frozen=True, slots=True)
class KeyRateDuration:
    tenor: Tenor
    duration: Decimal


@dataclass(frozen=True, slots=True)
class KeyRateDurations:
    items: list[KeyRateDuration]

    def as_dict(self) -> dict[Tenor, Decimal]:
        return {item.tenor: item.duration for item in self.items}


@dataclass(frozen=True, slots=True)
class KeyRateDurationCalculator:
    bump: float = DEFAULT_BUMP_SIZE

    def calculate(
        self,
        bond: _BondLike,
        curve: DiscountingCurve,
        settlement_date: Date,
        tenors: list[Tenor] | None = None,
    ) -> KeyRateDurations:
        grid = tenors or list(STANDARD_KEY_RATE_TENORS)
        grid = sorted(set(grid), key=_tenor_years)
        if not grid:
            raise ValueError("Key-rate duration requires a non-empty tenor grid.")

        pricer = BondPricer()
        base_price = pricer.price_from_curve(bond, curve, settlement_date).dirty.as_percentage()
        if base_price == 0:
            return KeyRateDurations(items=[])

        items: list[KeyRateDuration] = []
        for tenor in grid:
            curve_up = _key_rate_bumped_curve(curve, tenor_grid=grid, key_tenor=tenor, bump=self.bump)
            curve_down = _key_rate_bumped_curve(curve, tenor_grid=grid, key_tenor=tenor, bump=-self.bump)
            price_up = pricer.price_from_curve(bond, curve_up, settlement_date).dirty.as_percentage()
            price_down = pricer.price_from_curve(bond, curve_down, settlement_date).dirty.as_percentage()
            duration = (price_down - price_up) / (Decimal(2) * base_price * Decimal(str(self.bump)))
            items.append(KeyRateDuration(tenor=tenor, duration=duration))
        return KeyRateDurations(items=items)


def key_rate_duration_at_tenor(
    bond: _BondLike,
    curve: DiscountingCurve,
    settlement_date: Date,
    *,
    tenor: Tenor,
    bump: float = DEFAULT_BUMP_SIZE,
    tenor_grid: list[Tenor] | None = None,
) -> Decimal:
    grid = list(tenor_grid) if tenor_grid is not None else list(STANDARD_KEY_RATE_TENORS)
    if tenor not in grid:
        grid = sorted(grid + [tenor], key=_tenor_years)
    result = KeyRateDurationCalculator(bump=bump).calculate(bond, curve, settlement_date, tenors=grid)
    for item in result.items:
        if item.tenor == tenor:
            return item.duration
    return Decimal(0)


def spread_duration(
    bond: _BondLike,
    ytm: Yield | None,
    settlement_date: Date,
    *,
    bump: float = DEFAULT_BUMP_SIZE,
    curve: DiscountingCurve | None = None,
    spread: object | None = None,
) -> Decimal:
    if curve is None:
        if ytm is None:
            raise ValueError("spread_duration requires ytm when curve is not supplied.")
        return effective_duration(bond, ytm, settlement_date, bump=bump)

    spread_value = float(_to_decimal(spread or 0))
    pricer = BondPricer()
    base_curve = _parallel_bumped_curve(curve, spread_value)
    base_price = pricer.price_from_curve(bond, base_curve, settlement_date).dirty.as_percentage()
    if base_price == 0:
        return Decimal(0)

    curve_up = _parallel_bumped_curve(curve, spread_value + bump)
    curve_down = _parallel_bumped_curve(curve, spread_value - bump)
    price_up = pricer.price_from_curve(bond, curve_up, settlement_date).dirty.as_percentage()
    price_down = pricer.price_from_curve(bond, curve_down, settlement_date).dirty.as_percentage()
    return (price_down - price_up) / (Decimal(2) * base_price * Decimal(str(bump)))


class HedgeDirection(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"


@dataclass(frozen=True, slots=True)
class HedgeRecommendation:
    ratio: Decimal
    direction: HedgeDirection
    reason: str | None = None


def duration_hedge_ratio(
    target_duration: object,
    target_price: object,
    hedge_duration: object,
    hedge_price: object,
    *,
    target_face: object = Decimal(100),
    hedge_face: object = Decimal(100),
) -> Decimal:
    target_duration_value = _to_decimal(target_duration)
    target_price_value = _to_decimal(target_price)
    hedge_duration_value = _to_decimal(hedge_duration)
    hedge_price_value = _to_decimal(hedge_price)
    target_face_value = _to_decimal(target_face)
    hedge_face_value = _to_decimal(hedge_face)
    if target_price_value <= 0 or hedge_price_value <= 0:
        raise ValueError("target_price and hedge_price must be positive.")
    if target_face_value == 0 or hedge_face_value == 0:
        raise ValueError("target_face and hedge_face must be non-zero.")
    hedge_dollar_duration = hedge_duration_value * hedge_price_value * hedge_face_value
    if hedge_dollar_duration == 0:
        return Decimal(0)
    target_dollar_duration = target_duration_value * target_price_value * target_face_value
    return target_dollar_duration / hedge_dollar_duration


def dv01_hedge_ratio(target_dv01: object, hedge_dv01: object) -> Decimal:
    target_dv01_value = _to_decimal(target_dv01)
    hedge_dv01_value = _to_decimal(hedge_dv01)
    if hedge_dv01_value == 0:
        return Decimal(0)
    return target_dv01_value / hedge_dv01_value


@dataclass(frozen=True, slots=True)
class Position:
    modified_duration: Decimal
    dirty_price: Decimal
    face: Decimal = Decimal(100)

    def dv01(self) -> Decimal:
        return dv01_from_duration(self.modified_duration, self.dirty_price, self.face)

    def market_value(self) -> Decimal:
        return self.dirty_price * self.face / Decimal(100)


@dataclass(frozen=True, slots=True)
class PortfolioRisk:
    dv01: Decimal
    weighted_duration: Decimal


def aggregate_portfolio_risk(positions: list[Position]) -> PortfolioRisk:
    if not positions:
        return PortfolioRisk(dv01=Decimal(0), weighted_duration=Decimal(0))

    total_dv01 = Decimal(0)
    weighted_duration_numerator = Decimal(0)
    gross_market_value = Decimal(0)
    for position in positions:
        dv01_value = position.dv01()
        market_value = abs(position.market_value())
        total_dv01 += dv01_value
        weighted_duration_numerator += position.modified_duration * market_value
        gross_market_value += market_value
    weighted_duration = weighted_duration_numerator / gross_market_value if gross_market_value != 0 else Decimal(0)
    return PortfolioRisk(dv01=total_dv01, weighted_duration=weighted_duration)


class VaRMethod(str, Enum):
    HISTORICAL = "HISTORICAL"
    PARAMETRIC = "PARAMETRIC"


@dataclass(frozen=True, slots=True)
class VaRResult:
    value: Decimal
    confidence: Decimal
    method: VaRMethod


def _validate_confidence(confidence: float) -> float:
    level = float(confidence)
    if not 0.0 < level < 1.0:
        raise ValueError("confidence must lie strictly between 0 and 1.")
    return level


def _left_tail_quantile(sorted_returns: list[float], probability: float) -> float:
    if len(sorted_returns) == 1:
        return sorted_returns[0]
    position = probability * (len(sorted_returns) - 1)
    lower = floor(position)
    upper = ceil(position)
    if lower == upper:
        return sorted_returns[lower]
    weight = position - lower
    return sorted_returns[lower] + weight * (sorted_returns[upper] - sorted_returns[lower])


def historical_var(returns: list[float], confidence: float = 0.95) -> VaRResult:
    level = _validate_confidence(confidence)
    if not returns:
        return VaRResult(value=Decimal(0), confidence=Decimal(str(level)), method=VaRMethod.HISTORICAL)
    sorted_returns = sorted(float(value) for value in returns)
    tail_probability = 1.0 - level
    var_value = max(0.0, -_left_tail_quantile(sorted_returns, tail_probability))
    return VaRResult(
        value=Decimal(str(var_value)),
        confidence=Decimal(str(level)),
        method=VaRMethod.HISTORICAL,
    )


def parametric_var(returns: list[float], confidence: float = 0.95) -> VaRResult:
    level = _validate_confidence(confidence)
    if not returns:
        return VaRResult(value=Decimal(0), confidence=Decimal(str(level)), method=VaRMethod.PARAMETRIC)
    mu = mean(float(value) for value in returns)
    sigma = stdev(float(value) for value in returns) if len(returns) > 1 else 0.0
    left_tail_quantile = NormalDist().inv_cdf(1.0 - level)
    var_value = max(0.0, -(mu + sigma * left_tail_quantile))
    return VaRResult(
        value=Decimal(str(var_value)),
        confidence=Decimal(str(level)),
        method=VaRMethod.PARAMETRIC,
    )


def parametric_var_from_dv01(dv01: object, shock_bps: float, confidence: float = 0.95) -> VaRResult:
    level = _validate_confidence(confidence)
    z_score = NormalDist().inv_cdf(level)
    value = abs(_to_decimal(dv01)) * abs(Decimal(str(shock_bps))) * Decimal(str(z_score))
    return VaRResult(
        value=value,
        confidence=Decimal(str(level)),
        method=VaRMethod.PARAMETRIC,
    )


DurationType = Duration

__all__ = [
    "BondRiskCalculator",
    "BondRiskMetrics",
    "Convexity",
    "DEFAULT_BUMP_SIZE",
    "DV01",
    "Duration",
    "DurationType",
    "EffectiveDurationCalculator",
    "HedgeDirection",
    "HedgeRecommendation",
    "KeyRateDuration",
    "KeyRateDurationCalculator",
    "KeyRateDurations",
    "PortfolioRisk",
    "Position",
    "SMALL_BUMP_SIZE",
    "STANDARD_KEY_RATE_TENORS",
    "VaRMethod",
    "VaRResult",
    "aggregate_portfolio_risk",
    "analytical_convexity",
    "duration_hedge_ratio",
    "dv01_from_duration",
    "dv01_from_prices",
    "dv01_hedge_ratio",
    "dv01_per_100_face",
    "effective_convexity",
    "effective_duration",
    "historical_var",
    "key_rate_duration_at_tenor",
    "macaulay_duration",
    "modified_duration",
    "modified_from_macaulay",
    "notional_from_dv01",
    "parametric_var",
    "parametric_var_from_dv01",
    "price_change_with_convexity",
    "spread_duration",
]
