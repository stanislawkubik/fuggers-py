# `fuggers_py.bonds`

`fuggers_py.bonds` is the public entry point for bond instruments, bond quotes,
cash flows, pricing, yields, risk, spread analytics, YAS-style output, and
simple bond-option tools.

Import bond objects from this layer, not from internal module paths.

```python
from fuggers_py.bonds import BondPricer, BondQuote, FixedBondBuilder, RiskMetrics
```

## Units And Signs

- Clean and dirty bond prices are percent of par. `99.25` means 99.25 percent
  of face value.
- Coupon rates, most yields, spreads, repo rates, and funding rates are raw
  decimals. `0.05` means 5 percent.
- One basis point is `0.0001`.
- Helpers ending in `_pct` return percentage points. `4.5` means 4.5 percent.
- Helpers ending in `_bps` return basis points. `125` means 125 basis points.
- Money-market helpers are the exception: `discount_yield`,
  `bond_equivalent_yield`, `cd_equivalent_yield`, `money_market_yield`, and
  `money_market_yield_with_horizon` return quoted percentage points even though
  their names do not end in `_pct`.
- Spread helpers without `_bps` return raw decimals.
- `RiskMetrics.dv01` and `BondRiskMetrics.dv01` are percent-of-par price
  changes per 1 bp yield move. `dv01_from_duration()` returns a cash amount
  only because you pass a face amount.
- DV01 and PV01 are positive when the bond price rises as yield falls by 1 bp.
- Face amounts and settlement invoice cash fields are currency amounts.

## Public Surface Rule

The public surface is the names listed in `fuggers_py.bonds.__all__` and in
`specs/public_api_surface.json` for `fuggers_py.bonds`.

Bond-local support records are available from `fuggers_py.bonds.types`. Use
that package for identifiers, quote conventions, rating or sector metadata,
embedded put schedules, and amortization schedules.

`ZSpreadCalculator` is importable today because the package imports it
internally, but it is not in `__all__` and not in the public surface spec. Do
not document it or rely on it as public API. Use `z_spread()` and
`z_spread_from_curve()` instead.

## Core Examples

### Build, Price, And Read Cash Flows

```python
from decimal import Decimal

from fuggers_py import Compounding, Currency, Date, Frequency, Price
from fuggers_py import Yield, YieldCalculationRules
from fuggers_py.bonds import BondPricer, FixedBondBuilder

rules = YieldCalculationRules.us_treasury()
bond = (
    FixedBondBuilder.new()
    .with_issue_date(Date.from_ymd(2021, 1, 15))
    .with_maturity_date(Date.from_ymd(2031, 1, 15))
    .with_coupon_rate(Decimal("0.045"))
    .with_frequency(Frequency.SEMI_ANNUAL)
    .with_currency(Currency.USD)
    .with_rules(rules)
    .build()
)

settlement = Date.from_ymd(2026, 4, 22)
ytm = Yield.new(Decimal("0.0475"), Compounding.SEMI_ANNUAL)

pricer = BondPricer()
priced = pricer.price_from_yield(bond, ytm, settlement)

clean = priced.clean.as_percentage()
dirty = priced.dirty.as_percentage()
accrued = priced.accrued

round_trip_yield = pricer.yield_to_maturity(
    bond,
    Price.new(clean, Currency.USD),
    settlement,
)

future_flows = bond.cash_flows(settlement)
next_coupon = bond.next_coupon_date(settlement)
previous_coupon = bond.previous_coupon_date(settlement)
```

`BondPricer.price_from_yield()` discounts future cash flows after settlement.
It returns dirty price, clean price, and accrued interest. `yield_from_price()`
adds accrued interest to the clean price before solving for yield.

### Price From A Curve

`price_from_curve()` accepts any public curve object that provides a reference
date, day-count spec, and `discount_factor_at(tenor)`.

```python
from dataclasses import dataclass
from decimal import Decimal
from math import exp

from fuggers_py import Currency, Date, Frequency, YieldCalculationRules
from fuggers_py.bonds import BondPricer, FixedBondBuilder


@dataclass(frozen=True)
class CurveSpec:
    day_count: str = "ACT/365F"


@dataclass(frozen=True)
class FlatCurve:
    reference_date: Date
    zero_rate: float
    spec: CurveSpec = CurveSpec()

    def discount_factor_at(self, tenor: float) -> float:
        return exp(-self.zero_rate * tenor)


settlement = Date.from_ymd(2026, 4, 22)
curve = FlatCurve(reference_date=settlement, zero_rate=0.04)

bond = (
    FixedBondBuilder.new()
    .with_issue_date(Date.from_ymd(2021, 1, 15))
    .with_maturity_date(Date.from_ymd(2031, 1, 15))
    .with_coupon_rate(Decimal("0.045"))
    .with_frequency(Frequency.SEMI_ANNUAL)
    .with_currency(Currency.USD)
    .with_rules(YieldCalculationRules.us_treasury())
    .build()
)

curve_price = BondPricer().price_from_curve(bond, curve, settlement)
dirty_percent = curve_price.dirty.as_percentage()
```

The curve price uses discount factors at each cash-flow date divided by the
discount factor at settlement. Settlement after maturity raises a pricing error.

### Callable, Floating-Rate, And Sinking-Fund Builders

Builders collect fields step by step and validate them in `build()`. Required
dates, rates, frequency, currency, and rules must be present. The bond frequency
must match `YieldCalculationRules.frequency`.

```python
from dataclasses import replace
from decimal import Decimal

from fuggers_py import Currency, Date, Frequency, YieldCalculationRules
from fuggers_py.bonds import CallableBondBuilder, FixedBondBuilder
from fuggers_py.bonds import FloatingRateNoteBuilder, RateIndex
from fuggers_py.bonds import SinkingFundBondBuilder

base = (
    FixedBondBuilder.new()
    .with_issue_date(Date.from_ymd(2021, 1, 15))
    .with_maturity_date(Date.from_ymd(2031, 1, 15))
    .with_coupon_rate(Decimal("0.045"))
    .with_frequency(Frequency.SEMI_ANNUAL)
    .with_currency(Currency.USD)
    .with_rules(YieldCalculationRules.us_treasury())
    .build()
)

callable_bond = (
    CallableBondBuilder.new()
    .with_base_bond(base)
    .add_call(call_date=Date.from_ymd(2028, 1, 15), call_price=Decimal("100"))
    .build()
)
call_price = callable_bond.call_price_on(Date.from_ymd(2028, 1, 15))
worst_yield = callable_bond.yield_to_worst(Decimal("99.25"), Date.from_ymd(2026, 4, 22))

quarterly_rules = replace(
    YieldCalculationRules.us_corporate(),
    frequency=Frequency.QUARTERLY,
)
frn = (
    FloatingRateNoteBuilder.new()
    .with_issue_date(Date.from_ymd(2024, 1, 15))
    .with_maturity_date(Date.from_ymd(2027, 1, 15))
    .with_index(RateIndex.SOFR)
    .with_quoted_spread(Decimal("0.0075"))
    .with_current_reference_rate(Decimal("0.0520"))
    .with_frequency(Frequency.QUARTERLY)
    .with_currency(Currency.USD)
    .with_rules(quarterly_rules)
    .build()
)
coupon_rate = frn.effective_rate()

annual_rules = replace(YieldCalculationRules.us_corporate(), frequency=Frequency.ANNUAL)
sinker = (
    SinkingFundBondBuilder.new()
    .with_issue_date(Date.from_ymd(2024, 1, 15))
    .with_maturity_date(Date.from_ymd(2029, 1, 15))
    .with_coupon_rate(Decimal("0.05"))
    .with_frequency(Frequency.ANNUAL)
    .with_currency(Currency.USD)
    .with_rules(annual_rules)
    .add_sinking_entry(Date.from_ymd(2027, 1, 15), Decimal("0.25"))
    .add_sinking_entry(Date.from_ymd(2028, 1, 15), Decimal("0.25"))
    .build()
)
remaining_factor = sinker.factor_on(Date.from_ymd(2027, 1, 15))
average_life = sinker.average_life()
```

### Schedules, Accrued Interest, And Settlement

Schedules store both unadjusted accrual dates and adjusted payment dates.
Accrued interest inputs are currency or percent-of-par values depending on the
calling object; bond methods return accrued interest in the bond's quoted price
basis.

```python
from decimal import Decimal

from fuggers_py import CalendarId, Date, Frequency, YieldCalculationRules
from fuggers_py.bonds import AccruedInterestCalculator, AccruedInterestInputs
from fuggers_py.bonds import Schedule, ScheduleConfig, SettlementCalculator

rules = YieldCalculationRules.us_treasury()

schedule = Schedule.generate(
    ScheduleConfig(
        start_date=Date.from_ymd(2026, 1, 15),
        end_date=Date.from_ymd(2027, 1, 15),
        frequency=Frequency.SEMI_ANNUAL,
        calendar=rules.calendar,
        business_day_convention=rules.business_day_convention,
    )
)
payment_dates = schedule.dates

inputs = AccruedInterestInputs(
    settlement_date=Date.from_ymd(2026, 4, 22),
    accrual_start=Date.from_ymd(2026, 1, 15),
    accrual_end=Date.from_ymd(2026, 7, 15),
    coupon_amount=Decimal("2.25"),
    coupon_date=Date.from_ymd(2026, 7, 15),
    full_coupon_amount=Decimal("2.25"),
)
accrued = AccruedInterestCalculator.standard(inputs, rules=rules)

settlement_date = SettlementCalculator(
    calendar=CalendarId.weekend_only(),
    rules=rules.settlement_rules,
).settlement_date(Date.from_ymd(2026, 4, 22))
```

### Quotes And Reference Data

`BondQuote` stores only the fields in its constructor. It does not have bid,
ask, or mid fields. It validates that the quote currency matches the bond
currency. It also converts regressors to finite floats.

```python
from decimal import Decimal

from fuggers_py import Currency, Date, Frequency, YieldCalculationRules
from fuggers_py.bonds import BondQuote, FixedBondBuilder, deliverable_bpv_regressor
from fuggers_py.bonds import BondReferenceData, BondType, IssuerType

bond = (
    FixedBondBuilder.new()
    .with_issue_date(Date.from_ymd(2021, 1, 15))
    .with_maturity_date(Date.from_ymd(2031, 1, 15))
    .with_coupon_rate(Decimal("0.045"))
    .with_frequency(Frequency.SEMI_ANNUAL)
    .with_currency(Currency.USD)
    .with_rules(YieldCalculationRules.us_treasury())
    .with_instrument_id("UST-2031-4.5")
    .build()
)

quote = BondQuote(
    instrument=bond,
    clean_price=Decimal("99.25"),
    yield_to_maturity=Decimal("0.0468"),
    as_of=Date.from_ymd(2026, 4, 22),
    regressors={
        "deliverable_bpv": deliverable_bpv_regressor(81.2, deliverable=True),
    },
)
instrument_id = quote.instrument_id
quote_date = quote.resolved_settlement_date()

reference = BondReferenceData(
    instrument_id="corp-2029",
    bond_type=BondType.FIXED_RATE,
    issuer_type=IssuerType.CORPORATE,
    issue_date=Date.from_ymd(2024, 1, 15),
    maturity_date=Date.from_ymd(2029, 1, 15),
    coupon_rate=Decimal("0.0525"),
    frequency=Frequency.SEMI_ANNUAL,
    currency=Currency.USD,
    issuer_name="Example Corp",
)
reference_bond = reference.to_instrument()
```

### Risk And DV01

`RiskMetrics` returns percent-of-par sensitivities. Use `Position` or
`dv01_from_duration()` when you need cash DV01 for a face amount.

```python
from decimal import Decimal

from fuggers_py import Compounding, Currency, Date, Frequency
from fuggers_py import Yield, YieldCalculationRules
from fuggers_py.bonds import FixedBondBuilder, Position, RiskMetrics
from fuggers_py.bonds import aggregate_portfolio_risk, dv01_from_duration

bond = (
    FixedBondBuilder.new()
    .with_issue_date(Date.from_ymd(2021, 1, 15))
    .with_maturity_date(Date.from_ymd(2031, 1, 15))
    .with_coupon_rate(Decimal("0.045"))
    .with_frequency(Frequency.SEMI_ANNUAL)
    .with_currency(Currency.USD)
    .with_rules(YieldCalculationRules.us_treasury())
    .build()
)

settlement = Date.from_ymd(2026, 4, 22)
ytm = Yield.new(Decimal("0.0475"), Compounding.SEMI_ANNUAL)
metrics = RiskMetrics.from_bond(bond, ytm, settlement)

percent_of_par_dv01 = metrics.dv01
cash_dv01 = dv01_from_duration(
    metrics.modified_duration,
    dirty_price=Decimal("100.15"),
    face=Decimal("1000000"),
)

position = Position(
    modified_duration=metrics.modified_duration,
    dirty_price=Decimal("100.15"),
    face=Decimal("1000000"),
)
portfolio = aggregate_portfolio_risk([position])
portfolio_cash_dv01 = portfolio.dv01
```

### Yields

Current-yield helpers return raw decimals unless the name ends in `_pct`.
Money-market helpers return percentage points.

```python
from decimal import Decimal

from fuggers_py.bonds import bond_equivalent_yield, current_yield
from fuggers_py.bonds import current_yield_pct, discount_yield

raw_current = current_yield(Decimal("0.045"), Decimal("99.25"))
display_current = current_yield_pct(Decimal("0.045"), Decimal("99.25"))

# Money-market helpers return percentage points, not raw decimals.
discount_display = discount_yield(
    face_value=Decimal("100"),
    price=Decimal("98.75"),
    days_to_maturity=Decimal("180"),
)
bey_display = bond_equivalent_yield(
    face_value=Decimal("100"),
    price=Decimal("98.75"),
    days_to_maturity=Decimal("180"),
)
```

### Spreads And Balance-Sheet Overlays

Unsuffixed spread helpers return raw decimals. `_bps` helpers return basis
points.

```python
from decimal import Decimal

from fuggers_py import Date, Tenor
from fuggers_py.bonds import BenchmarkSpec, GovernmentCurve, SecurityId
from fuggers_py.bonds import GSpreadCalculator, g_spread_bps
from fuggers_py.bonds import CapitalSpreadAdjustment, HaircutSpreadAdjustment
from fuggers_py.bonds import apply_balance_sheet_overlays
from fuggers_py.bonds import reference_rate_decomposition

curve = (
    GovernmentCurve.us_treasury(Date.from_ymd(2026, 4, 22))
    .add_benchmark(Tenor.parse("5Y"), Decimal("0.041"))
    .add_benchmark(Tenor.parse("10Y"), Decimal("0.044"))
)

benchmark_yield = curve.yield_for_tenor(Tenor.parse("7Y"))
spread_bps = g_spread_bps(Decimal("0.0525"), benchmark_yield)
nearest_spec = BenchmarkSpec.nearest()

security_id = SecurityId.cusip_unchecked("91282CJL6")

capital = CapitalSpreadAdjustment(
    exposure=Decimal("1000000"),
    risk_weight=Decimal("0.20"),
    capital_ratio=Decimal("0.08"),
    hurdle_rate=Decimal("0.12"),
)
haircut = HaircutSpreadAdjustment(
    collateral_value=Decimal("1000000"),
    haircut=Decimal("0.02"),
    repo_rate=Decimal("0.050"),
    haircut_funding_rate=Decimal("0.058"),
)
overlay = apply_balance_sheet_overlays(
    base_spread=Decimal("0.0125"),
    adjustments=(capital, haircut),
)
adjusted_spread = overlay.adjusted_spread

funding = reference_rate_decomposition(
    repo_rate=Decimal("0.050"),
    general_collateral_rate=Decimal("0.051"),
    unsecured_overnight_rate=Decimal("0.052"),
    term_rate=Decimal("0.054"),
)
total_funding_basis = funding.total_funding_basis
```

### TIPS

`TipsBond` uses inflation fixings to compute an index ratio. The ratio scales
principal and coupons. `TipsPricer` prices projected inflation-adjusted cash
flows from a real yield.

```python
from decimal import Decimal

from fuggers_py import Compounding, Currency, Date, Frequency, YearMonth
from fuggers_py import Yield, YieldCalculationRules
from fuggers_py.bonds import TipsBond, TipsPricer
from fuggers_py.inflation import InMemoryInflationFixingSource, InflationFixing
from fuggers_py.inflation import USD_CPI_U_NSA

fixings = []
level = Decimal("300.0")
for year in range(2023, 2035):
    for month in range(1, 13):
        fixings.append(InflationFixing("CPURNSA", YearMonth(year, month), level))
        level += Decimal("0.2")

source = InMemoryInflationFixingSource(fixings)
tips = TipsBond.new(
    issue_date=Date.from_ymd(2024, 1, 15),
    maturity_date=Date.from_ymd(2034, 1, 15),
    coupon_rate=Decimal("0.0125"),
    inflation_convention=USD_CPI_U_NSA,
    base_reference_date=Date.from_ymd(2024, 1, 15),
    frequency=Frequency.SEMI_ANNUAL,
    currency=Currency.USD,
    rules=YieldCalculationRules.us_treasury(),
    fixing_source=source,
)

settlement = Date.from_ymd(2026, 4, 22)
ratio = tips.index_ratio(settlement, fixing_source=source)
adjusted_principal = tips.adjusted_principal(settlement, fixing_source=source)

real_yield = Yield.new(Decimal("0.018"), Compounding.SEMI_ANNUAL)
tips_price = TipsPricer().price_from_real_yield(
    tips,
    real_yield,
    settlement,
    fixing_source=source,
)
```

### YAS And Settlement Invoice

YAS output is display-oriented: yields are percentage points, spreads are basis
points, and the attached invoice has both percent-of-par and cash fields.

```python
from dataclasses import dataclass
from decimal import Decimal
from math import exp

from fuggers_py import Currency, Date, Frequency, Price, YieldCalculationRules
from fuggers_py.bonds import FixedBondBuilder, SettlementInvoiceBuilder, YASCalculator
from fuggers_py.bonds import calculate_accrued_amount, calculate_proceeds


@dataclass(frozen=True)
class CurveSpec:
    day_count: str = "ACT/365F"


@dataclass(frozen=True)
class FlatCurve:
    reference_date: Date
    zero_rate: float
    spec: CurveSpec = CurveSpec()

    def discount_factor_at(self, tenor: float) -> float:
        return exp(-self.zero_rate * tenor)

    def rate_at(self, tenor: float) -> float:
        return self.zero_rate

    def zero_rate_at(self, tenor: float) -> float:
        return self.zero_rate


bond = (
    FixedBondBuilder.new()
    .with_issue_date(Date.from_ymd(2021, 1, 15))
    .with_maturity_date(Date.from_ymd(2031, 1, 15))
    .with_coupon_rate(Decimal("0.045"))
    .with_frequency(Frequency.SEMI_ANNUAL)
    .with_currency(Currency.USD)
    .with_rules(YieldCalculationRules.us_treasury())
    .build()
)
settlement = Date.from_ymd(2026, 4, 22)

invoice = SettlementInvoiceBuilder(
    settlement_date=settlement,
    clean_price=Decimal("99.25"),
    accrued_interest=bond.accrued_interest(settlement),
    face_value=Decimal("1000000"),
).build()

accrued_cash = calculate_accrued_amount(
    face_value=Decimal("1000000"),
    accrued_interest=invoice.accrued_interest,
)
settlement_cash = calculate_proceeds(invoice.principal_amount, accrued_cash)

yas = YASCalculator(curve=FlatCurve(settlement, 0.04)).calculate(
    bond,
    Price.new(Decimal("99.25"), Currency.USD),
    settlement,
)
yas_duration = yas.modified_duration()
```

### Bond Options

Bond options use a short-rate model and a recombining tree. The returned option
price is in the same value units as the tree cash flows, not a yield.

```python
from dataclasses import dataclass
from decimal import Decimal
from math import exp

from fuggers_py import Currency, Date, Frequency, OptionType, YieldCalculationRules
from fuggers_py.bonds import BondOption, ExerciseStyle, FixedBondBuilder, HullWhiteModel


@dataclass(frozen=True)
class CurveSpec:
    day_count: str = "ACT/365F"


@dataclass(frozen=True)
class FlatCurve:
    reference_date: Date
    zero_rate: float
    spec: CurveSpec = CurveSpec()

    def discount_factor_at(self, tenor: float) -> float:
        return exp(-self.zero_rate * tenor)

    def rate_at(self, tenor: float) -> float:
        return self.zero_rate

    def zero_rate_at(self, tenor: float) -> float:
        return self.zero_rate


valuation_date = Date.from_ymd(2026, 4, 22)
bond = (
    FixedBondBuilder.new()
    .with_issue_date(Date.from_ymd(2024, 1, 15))
    .with_maturity_date(Date.from_ymd(2029, 1, 15))
    .with_coupon_rate(Decimal("0.04"))
    .with_frequency(Frequency.SEMI_ANNUAL)
    .with_currency(Currency.USD)
    .with_rules(YieldCalculationRules.us_treasury())
    .build()
)
model = HullWhiteModel(
    mean_reversion=Decimal("0.03"),
    volatility=Decimal("0.01"),
    term_structure=FlatCurve(reference_date=valuation_date, zero_rate=0.04),
)
option = BondOption(
    expiry=Date.from_ymd(2027, 1, 15),
    strike=Decimal("100"),
    bond=bond,
    model=model,
    option_type=OptionType.CALL,
    exercise_style=ExerciseStyle.EUROPEAN,
    valuation_date=valuation_date,
)
option_value = option.price()
```

## Public Export Reference

### Contracts, Instruments, Cash Flows, And Builders

| Export | What It Represents | Behavior, Methods, And Properties |
|---|---|---|
| `Bond` | Abstract bond contract used by pricing, cash-flow, and risk code. | Concrete bonds implement `identifiers()`, `currency()`, `notional()`, `issue_date()`, `maturity_date()`, `frequency()`, `rules()`, `cash_flows()`, and `accrued_interest()`. The helper methods `max_date()`, `next_coupon_date()`, and `previous_coupon_date()` read the cash-flow list. |
| `BondAnalytics` | Mixin that adds convenience analytics to concrete bonds. | Methods call public pricing/risk objects: `price_from_yield()`, `yield_from_price()`, `risk_metrics()`, and `modified_duration()`. |
| `BondCashFlow` | One dated bond cash flow. | Fields are `date`, `amount`, `flow_type`, optional accrual dates, `factor`, and optional `reference_rate`. Methods: `is_coupon()`, `is_principal()`, and `factored_amount()`. `factored_amount()` returns `amount * factor`. |
| `CashFlowType` | Labels a cash flow as coupon, principal, inflation coupon, inflation principal, combined coupon/principal, or fee. | Used by `BondCashFlow.is_coupon()` and `BondCashFlow.is_principal()`. |
| `CashFlowGenerator` | Helper that builds cash flows from schedule dates. | `fixed_rate_bond_cashflows()` builds coupon and redemption flows. `future_cashflows()` filters flows strictly after a cutoff date. |
| `FixedBond` | Concrete fixed-coupon bond. | Constructor validation checks dates, positive notional, coupon between 0 and 1, non-zero frequency, and matching rules frequency. Useful methods: `new()`, `identifiers()`, `currency()`, `notional()`, `issue_date()`, `maturity_date()`, `frequency()`, `coupon_rate()`, `rules()`, `schedule()`, `cash_flows()`, and `accrued_interest()`. |
| `FixedBondBuilder` | Builder for `FixedBond`. | Use `new()`, `with_issue_date()`, `with_maturity_date()`, `with_coupon_rate()`, `with_frequency()`, `with_currency()`, `with_notional()`, `with_identifiers()`, `with_instrument_id()`, `with_rules()`, `with_stub_rules()`, and `build()`. Missing required fields raise `MissingRequiredField`. |
| `FixedRateBond` | Alias of `FixedBond`. | Use the same methods and behavior as `FixedBond`. |
| `FixedRateBondBuilder` | Alias of `FixedBondBuilder`. | Use the same builder methods as `FixedBondBuilder`. |
| `FixedCouponBond` | Protocol for objects with `coupon_rate()`. | Use it for type checks or functions that only need a fixed coupon rate. It is not a concrete instrument. |
| `CallableBond` | Bond with call and optional put workouts. | Wraps a fixed base bond. Useful methods include `is_callable_on()`, `first_call()`, `next_call()`, `call_price_on()`, `cash_flows_to_call()`, `yield_to_call()`, `yield_to_first_call()`, `put_schedule()`, `is_putable_on()`, `put_price_on()`, `yield_to_put()`, `yield_to_first_put()`, `yield_to_worst()`, `workout_dates()`, `first_workout_date()`, and `yield_to_first_workout()`. |
| `CallableBondBuilder` | Builder for `CallableBond`. | Use `new()`, `with_base_bond()`, `with_call_schedule()`, `with_put_schedule()`, `add_call()`, `with_protection_end_date()`, `add_put()`, and `build()`. Call prices and put prices are percent of par. |
| `CallEntry` | One call date and redemption price. | Coerces `call_price` and `make_whole_spread` to `Decimal`. Validates positive call price and valid call end date. Method: `is_exercisable_on()`. |
| `CallSchedule` | Ordered list of call entries plus optional protection end date. | `new()` sorts entries. Methods: `is_protected()`, `future_entries()`, `first_call_after()`, `entry_for_date()`, and `call_price_on()`. |
| `CallType` | Exercise style for a call entry. | Values include European, American, Bermudan, and make-whole. |
| `AccelerationOption` | Alias of `CallType`. | Kept as a public name for call-style option classification. |
| `CallScheduleEntry` | Reference-data call or put entry. | Fields are `exercise_date` and `price`. The constructor coerces `price` to `Decimal`. Used by `BondReferenceData`, not by `CallableBond` directly. |
| `EmbeddedOptionBond` | Protocol for bonds with workout yields or put schedules. | Methods: `yield_to_worst()` and `put_schedule()`. It is a shape contract, not a concrete bond. |
| `FloatingRateNote` | Concrete floating-rate bond. | Stores index, quoted spread, reset frequency, current reference rate, optional cap/floor, and rules. Useful methods: `new()`, `index()`, `quoted_spread()`, `cap_rate()`, `floor_rate()`, `current_reference_rate()`, `current_coupon_rate()`, `effective_rate()`, `required_fixing_dates()`, `period_coupon()`, `cash_flows()`, `projected_cash_flows()`, `cash_flows_with_fixings()`, and `accrued_interest()`. Cap and floor are raw decimal rates. |
| `FloatingRateNoteBuilder` | Builder for `FloatingRateNote`. | Use `new()`, date/rate/currency/rules methods, `with_index()`, `with_quoted_spread()`, `with_cap()`, `with_floor()`, `with_current_reference_rate()`, `with_index_definition()`, and `build()`. Quoted spread is a raw decimal. |
| `FloatingCouponBond` | Protocol for floating-rate coupon objects. | Methods: `index()`, `quoted_spread()`, and `current_coupon_rate()`. |
| `FloatingRateTerms` | Reference-data terms for a floating-rate note. | Constructor uppercases `index_name` and coerces spread, current reference rate, cap, and floor to `Decimal`. Method: `rate_index()` maps the name to `RateIndex`. |
| `SinkingFundEntry` | One sinking-fund payment date and factor. | Constructor coerces factor to `Decimal` and validates the schedule in `SinkingFundSchedule`. |
| `SinkingFundPayment` | Alias of `SinkingFundEntry`. | Same fields and behavior as `SinkingFundEntry`. |
| `SinkingFundSchedule` | Ordered principal-reduction schedule. | `new()` sorts entries. Methods: `factor_on()`, `factor_for_payment()`, and `to_amortization()`. Factors are raw decimal principal reductions. |
| `SinkingFundBond` | Fixed-coupon bond with scheduled principal reductions. | Useful methods include `sinking_schedule()`, `factor_on()`, `amortization_schedule()`, `average_life()`, `yield_to_average_life()`, plus the normal fixed-bond methods. |
| `SinkingFundBondBuilder` | Builder for `SinkingFundBond`. | Use fixed-bond builder methods plus `with_sinking_schedule()`, `add_sinking_entry()`, `build_schedule()`, and `build()`. |
| `TipsBond` | Inflation-linked US Treasury-style bond. | Validates dated date, maturity, currency match with inflation convention, positive notional, coupon bounds, and frequency/rules match. Useful methods: `new()`, `dated_date()`, `inflation_convention()`, `inflation_index_definition()`, `inflation_index_type()`, `base_reference_date()`, `reference_cpi()`, `index_ratio()`, `adjusted_principal()`, `final_principal_redemption()`, `projected_coupon_cash_flows()`, `projected_cash_flows()`, `cash_flow_schedule()`, `cash_flows()`, and `accrued_interest()`. |
| `InflationLinkedBond` | Protocol for inflation-linked bond objects. | Method: `inflation_index_type()`. It is not a concrete bond. |
| `AmortizingBond` | Protocol for bonds with principal reductions. | Method: `amortization_schedule()`. |
| `ZeroCouponBond` | Concrete bond with one principal payment and no coupons. | Methods: `identifiers()`, `currency()`, `notional()`, `issue_date()`, `maturity_date()`, `frequency()`, `rules()`, `cash_flows()`, and `accrued_interest()`. Accrued interest is zero. |
| `ScheduleConfig` | Inputs for coupon schedule generation. | Fields are start/end dates, frequency, calendar, business-day convention, end-of-month flag, and stub rules. Methods: `first_regular_date()`, `penultimate_date()`, `stub_type()`, and `uses_forward_generation()`. |
| `Schedule` | Generated coupon schedule. | Fields are `unadjusted_dates`, adjusted `dates`, and `config`. `generate()` validates dates, generates forward or backward, deduplicates, sorts, and applies the calendar. |
| `AccruedInterestInputs` | Inputs for accrued-interest calculations. | Holds settlement date, accrual period, coupon amount, coupon date, full coupon amount, and optional reference period bounds. |
| `AccruedInterestCalculator` | Accrued-interest calculation helpers. | Static methods: `standard()`, `ex_dividend()`, and `irregular_period()`. They validate accrual periods and use `YieldCalculationRules`. |
| `SettlementCalculator` | Resolves settlement date from trade date, calendar, and settlement rules. | Method: `settlement_date()`. You can pass `YieldCalculationRules.*().settlement_rules`. |

### Bond Types And Classification Records

| Export | What It Represents | Behavior, Methods, And Properties |
|---|---|---|
| `BondType` | Bond kind used in reference data. | Used by `BondReferenceData.to_instrument()` to choose fixed, floating, callable, puttable, or zero-coupon construction. |
| `IssuerType` | Issuer category. | `BondReferenceData` uses it to choose default yield rules when no explicit rules are supplied. Corporate records default to corporate rules; others default to Treasury rules. |
| `CreditRating` | Rating bucket enum. | Method: `score()` returns an ordered numeric score for comparison. |
| `RatingInfo` | Rating metadata record. | Fields are `rating`, optional `agency`, and optional `outlook`. |
| `RateIndex` | Floating-rate index enum. | Method: `display_name()` returns a readable index name. `FloatingRateTerms.rate_index()` maps text to this enum. |
| `Sector` | Sector enum. | Used by issuer and reference data. |
| `SectorInfo` | Sector metadata record. | Fields are `sector`, optional `issuer`, optional `country`, optional `region`, and optional `subsector`. |
| `Seniority` | Capital-structure seniority enum. | Used in reference data and spread/risk grouping. |
| `SeniorityInfo` | Seniority metadata record. | Fields are `seniority` and `secured`. |
| `ASWType` | Asset-swap type enum. | Used by asset-swap calculators. |

### Quotes And Reference Data

| Export | What It Represents | Behavior, Methods, And Properties |
|---|---|---|
| `BondQuote` | Market quote attached to one concrete bond. | Fields are `instrument`, clean/dirty price, accrued interest, yield-to-maturity, yield-to-worst, `as_of`, source, currency, regressors, and fit weight. Decimal fields are coerced to `Decimal`. Source is stripped. Currency must match the bond. Regressors and fit weight must be finite floats. Methods/properties: `instrument_id` and `resolved_settlement_date()`. |
| `deliverable_bpv_regressor` | Encodes a deliverable-bond BPV regressor. | Returns `bpv` as a float when deliverable, otherwise `0.0`. Rejects non-finite values. |
| `BondReferenceData` | Static bond record that can build an instrument. | Coerces identifiers and decimal fields, sorts call/put schedules, normalizes text fields, validates non-negative outstanding amount and liquidity score. Method: `to_instrument()`. |
| `BondReferenceSource` | Protocol for lookup by instrument id. | Method: `get_bond_reference()`. |
| `IssuerReferenceData` | Static issuer record. | Strips issuer text, uppercases country, and rejects empty issuer names. |
| `IssuerReferenceSource` | Protocol for issuer lookup. | Method: `get_issuer_reference()`. |
| `RatingRecord` | Rating record keyed by instrument or issuer. | Strips rating, agency, outlook, and issuer name. Parses `instrument_id` when supplied. |
| `RatingSource` | Protocol for rating lookup. | Method: `get_rating()`. |
| `EtfHoldingsSource` | Protocol for ETF holdings lookup. | Method: `get_etf_holdings()`. |
| `ReferenceDataProvider` | Small delegating provider over optional sources. | Methods: `get_bond_reference()`, `get_issuer_reference()`, `get_rating()`, and `get_etf_holdings()`. Missing sources return `None` or an empty tuple. |

### Pricing And Yield Engines

| Export | What It Represents | Behavior, Methods, And Properties |
|---|---|---|
| `BondPricer` | Main price/yield converter for bonds. | Methods: `price_from_curve()`, `price_from_yield()`, `yield_from_price()`, and `yield_to_maturity()`. Prices are percent of par. TIPS are routed to `TipsPricer`. Price currency must match bond currency when solving yield. |
| `TipsPricer` | Real-yield pricer for `TipsBond`. | Methods: `accrued_interest()`, `present_value_from_real_yield()`, `dirty_price_from_real_yield()`, `clean_price_from_real_yield()`, `price_from_real_yield()`, `real_yield_from_clean_price()`, and `risk_metrics_from_real_yield()`. Uses projected inflation-adjusted cash flows. |
| `PriceResult` | Clean/dirty price result. | Fields are `dirty`, `clean`, and `accrued`. Properties: `dirty_price`, `clean_price`, `accrued_interest`, and `present_value`. `present_value` is dirty price as percent of par. |
| `BondResult` | Alias of `PriceResult`. | Same fields and properties as `PriceResult`. |
| `YieldResult` | Result from `BondPricer.yield_from_price()`. | Fields are `ytm` and `engine`. This is not the same class returned by `YieldSolver.solve()`. |
| `YieldEngineResult` | Lower-level solver result. | Fields are `yield_rate`, `iterations`, `converged`, `residual`, `method`, and `convention`. |
| `CashFlowData` | Solver input cash flow. | Fields are settlement-relative `years` and cash-flow `amount` in percent-of-par terms. |
| `StandardYieldEngine` | Low-level price/yield engine. | Methods: `yield_from_price()` and `dirty_price_from_yield()`. The one-layer public import uses the pricing engine version. |
| `YieldEngine` | Protocol for price/yield engines. | Methods: `yield_from_price()`, `dirty_price_from_yield()`, and `clean_price_from_yield()`. |
| `YieldSolver` | Standalone numerical yield solver. | Method: `solve()`. It solves from dirty price, cash-flow amounts, times, frequency, and convention. It translates bond pricing failures into analytics errors. |
| `RiskMetrics` | Pricing-layer duration, convexity, and DV01 record. | Fields are `modified_duration`, `macaulay_duration`, `convexity`, and `dv01`. Properties: `duration` and `pv01`. Class methods: `from_bond()` and `from_projected_cashflows()`. `pv01` is an alias for `dv01`. |
| `DurationResult` | Alias of `RiskMetrics`. | Same fields, properties, and class methods as `RiskMetrics`. |
| `current_yield` | Current yield from coupon rate and clean price. | Returns raw decimal. Clean price is percent of par. |
| `current_yield_pct` | Display current yield from coupon rate and clean price. | Returns percentage points. |
| `current_yield_simple` | Float current-yield helper. | Returns raw decimal using float arithmetic. |
| `current_yield_simple_pct` | Float current-yield display helper. | Returns percentage points. |
| `current_yield_from_amount` | Current yield from coupon amount and clean price. | Coupon amount is annual cash coupon per 100 face. Returns raw decimal. |
| `current_yield_from_amount_pct` | Display current yield from coupon amount. | Returns percentage points. |
| `current_yield_from_bond` | Current yield from a bond-like object. | Reads `coupon_rate` from a method or attribute. Returns raw decimal. |
| `current_yield_from_bond_pct` | Display current yield from a bond-like object. | Returns percentage points. |
| `simple_yield` | Simple annualized yield helper. | Uses coupon amount, price, redemption value, and years. Returns raw decimal. |
| `simple_yield_f64` | Float version of simple yield. | Returns a float raw decimal. |
| `street_convention_yield` | Street-convention yield helper. | Returns raw decimal yield using street-style inputs. |
| `true_yield` | Adjusts a street yield by settlement adjustment. | Inputs and output are percentage-point display values in the YAS path. |
| `settlement_adjustment` | Computes the adjustment between street and true yield. | Used by `true_yield()`. |
| `discount_yield` | Money-market discount yield. | Returns percentage points. Inputs are face value, price, and days to maturity. |
| `bond_equivalent_yield` | Bond-equivalent money-market yield. | Returns percentage points. |
| `cd_equivalent_yield` | Certificate-of-deposit equivalent yield. | Returns percentage points. |
| `money_market_yield` | Default money-market yield. | Returns percentage points and currently maps to bond-equivalent yield. |
| `money_market_yield_with_horizon` | Money-market yield with a horizon argument. | Returns the base money-market yield; the current implementation does not change the result for horizon. |
| `discount_yield_simple` | Simple discount-yield helper. | Returns raw decimal in the `YieldEngine` helper set. |
| `bond_equivalent_yield_simple` | Simple bond-equivalent helper. | Returns raw decimal in the `YieldEngine` helper set. |
| `RollForwardMethod` | Short-date roll-forward decision enum. | Used by `ShortDateCalculator`. |
| `ShortDateCalculator` | Decides when short-dated bonds use money-market logic. | Constructors: `new()` and `bloomberg()`. Methods: `is_short_dated()`, `use_money_market_below()`, and `roll_forward_method()`. |

### Risk

| Export | What It Represents | Behavior, Methods, And Properties |
|---|---|---|
| `BondRiskMetrics` | Risk result record. | Fields are `modified_duration`, `macaulay_duration`, `convexity`, and `dv01`. DV01 is percent-of-par per 1 bp. |
| `BondRiskCalculator` | Convenience wrapper around risk functions for one bond/yield/date. | Methods: `modified_duration()`, `macaulay_duration()`, `convexity()`, `dv01()`, and `all_metrics()`. |
| `EffectiveDurationCalculator` | Bumped-duration calculator. | Field `bump` is a raw decimal yield shift. Method: `calculate()`. |
| `Duration` | Small value wrapper for a duration. | Method: `as_decimal()`. |
| `DurationType` | Alias of `Duration`. | Same behavior as `Duration`. |
| `Convexity` | Small value wrapper for convexity. | Method: `as_decimal()`. |
| `DV01` | Small value wrapper for DV01. | Method: `as_decimal()`. |
| `KeyRateDuration` | One key-rate duration point. | Fields are `tenor` and `duration`. |
| `KeyRateDurations` | Collection of key-rate duration points. | Field `items`; method `as_dict()`. |
| `KeyRateDurationCalculator` | Key-rate bumped curve calculator. | Field `bump`; method `calculate()`. |
| `HedgeDirection` | Hedge direction enum. | Values describe whether the hedge should be long or short. |
| `HedgeRecommendation` | Hedge recommendation record. | Fields are `ratio`, `direction`, and optional `reason`. |
| `Position` | Duration/price/face position for portfolio risk. | Methods: `dv01()` returns cash DV01 using face; `market_value()` returns dirty-price market value. |
| `PortfolioRisk` | Aggregated portfolio risk record. | Fields are total cash `dv01` and market-value-weighted duration. |
| `VaRMethod` | Value-at-risk method enum. | Values are historical and parametric. |
| `VaRResult` | Value-at-risk result. | Fields are `value`, `confidence`, and `method`. |
| `DEFAULT_BUMP_SIZE` | Standard yield bump. | Raw decimal 1 bp bump used by risk functions. |
| `SMALL_BUMP_SIZE` | Smaller yield bump. | Raw decimal bump for high-precision sensitivity calculations. |
| `modified_duration` | Calculates modified duration from bond, yield, and settlement date. | Returns a raw duration number. Uses a 1 bp finite difference around the dirty price/yield relation. |
| `macaulay_duration` | Calculates Macaulay duration. | Returns a raw duration number. |
| `modified_from_macaulay` | Converts Macaulay duration to modified duration. | Uses compounding frequency from the yield when possible; defaults to semiannual-like behavior when frequency is omitted. |
| `effective_duration` | Bumped effective duration. | Uses price down and price up around a raw decimal yield bump. |
| `analytical_convexity` | Analytical convexity with fallback. | Falls back to `effective_convexity()` if the analytical path cannot compute. |
| `effective_convexity` | Bumped convexity. | Uses dirty prices at yield plus/minus bump. |
| `price_change_with_convexity` | Estimates price change from duration and convexity. | Inputs are duration, convexity, price, and raw yield change. |
| `dv01_per_100_face` | DV01 for 100 face. | Uses modified duration and dirty price. Result is percent-of-par cash change for 100 face. |
| `dv01_from_duration` | Cash DV01 from duration, dirty price, and face. | `dirty_price` is percent of par; `face` is currency amount. |
| `dv01_from_prices` | DV01 from down/up bumped prices. | Returns `(price_down - price_up) / 2`. |
| `notional_from_dv01` | Face amount needed for a target DV01. | Requires non-zero duration and price. |
| `key_rate_duration_at_tenor` | Single-tenor key-rate duration. | Adds the requested tenor to the grid when missing. |
| `spread_duration` | Duration to a spread move. | Uses yield duration when no curve is supplied; uses shifted discount curve when a curve is supplied. |
| `duration_hedge_ratio` | Hedge ratio from target and hedge duration/price/face. | Returns target dollar duration divided by hedge dollar duration. |
| `dv01_hedge_ratio` | Hedge ratio from target and hedge DV01. | Returns zero when hedge DV01 is zero. |
| `aggregate_portfolio_risk` | Aggregates a list of `Position` records. | Empty list returns zero DV01 and zero weighted duration. |
| `historical_var` | Historical value-at-risk from return observations. | Returns zero for empty returns. Confidence must be between 0 and 1. |
| `parametric_var` | Normal-curve value-at-risk from return observations. | Returns zero for empty returns. |
| `parametric_var_from_dv01` | Value-at-risk from DV01 and a shock size in basis points. | Uses absolute DV01 and absolute shock. |

### Spreads, Asset Swaps, And Funding Adjustments

| Export | What It Represents | Behavior, Methods, And Properties |
|---|---|---|
| `SecurityId` | Typed security identifier for spread analytics. | Constructors: `cusip()`, `cusip_unchecked()`, `isin()`, `sedol()`, and `figi()`. `cusip()`, `isin()`, `sedol()`, and `figi()` validate. Methods: `id_type()`, `as_str()`, and `__str__()`. |
| `BenchmarkKind` | Benchmark selection enum. | Used inside `BenchmarkSpec`. |
| `BenchmarkSpec` | Benchmark-selection record. | Constructors: `interpolated()`, `nearest()`, `ten_year()`, `five_year()`, and `explicit()`. Method: `description()`. Explicit yield is a raw decimal. |
| `GovernmentBenchmark` | One government curve point. | Fields are `tenor` and raw decimal `yield_rate`. |
| `GovernmentCurve` | Sparse government curve with interpolation. | Methods: `add_benchmark()`, `benchmark_for_tenor()`, `nearest_benchmark()`, `interpolated_yield()`, `yield_for_tenor()`, `yield_for_date()`, `us_treasury()`, and `uk_gilt()`. Ties in nearest lookup choose the shorter tenor. |
| `GSpreadCalculator` | Curve-backed government-spread calculator. | Methods: `spread_decimal()` and `spread_bps()`. Decimal spreads are raw decimals; bps spreads are basis points. |
| `ISpreadCalculator` | Curve-backed swap-spread calculator. | Methods: `spread_decimal()` and `spread_bps()`. It reads a zero rate from the supplied curve at bond maturity. |
| `DiscountMarginCalculator` | Floating-rate discount-margin solver. | Methods: `calculate()`, `price_with_dm()`, `spread_dv01()`, and `spread_duration()`. Discount margin is a raw decimal. `spread_dv01()` uses `(price_down - price_up) / 2`. |
| `OASCalculator` | Option-adjusted spread calculator. | Methods: `calculate()`, `price_with_oas()`, `effective_duration()`, `effective_convexity()`, and `option_value()`. OAS is a raw decimal spread. |
| `ParParAssetSwap` | Par/par asset-swap calculator. | Method: `calculate()`. |
| `ProceedsAssetSwap` | Proceeds asset-swap calculator. | Method: `calculate()`. |
| `ReferenceRateBreakdown` | Repo-to-term funding breakdown. | Fields hold raw decimal rates and ladder differences, including `total_funding_basis`. |
| `CompoundingConvexityBreakdown` | Term-rate compounding/convexity adjustment record. | Fields hold raw decimal adjustment pieces. |
| `SpreadAdjustmentBreakdown` | One named spread adjustment. | Coerces `spread_adjustment` to `Decimal`; strips name and description. |
| `SpreadAdjustment` | Protocol for spread overlay objects. | Methods: `breakdown()` and `spread_adjustment()`. |
| `BaseSpreadAdjustment` | Base class for spread overlay classes. | `spread_adjustment()` returns `breakdown().spread_adjustment`; subclasses implement `breakdown()`. |
| `SpreadAdjustmentSummary` | Base spread plus component overlays. | Fields are `base_spread`, `total_adjustment`, `adjusted_spread`, and component breakdowns. Numeric fields are coerced to `Decimal`. |
| `BalanceSheetSpreadOverlay` | Container for spread adjustments. | Methods: `summary()`, `apply()`, and `apply_to_funding_spread()`. |
| `FundingSpreadOverlayResult` | Funding-spread overlay result. | Fields are base funding spread, adjusted funding spread, optional credit spread, optional all-in spread, and overlay summary. |
| `CapitalSpreadAdjustment` | Capital-charge overlay object. | Stores exposure, risk weight, capital ratio, hurdle rate, pass-through, and name. Method: `breakdown()`. |
| `CapitalAdjustmentBreakdown` | Capital overlay breakdown. | Includes capital consumed, annual capital cost, passed-through cost, and raw decimal spread adjustment. |
| `HaircutSpreadAdjustment` | Haircut-funding overlay object. | Stores collateral value, haircut, repo rate, haircut funding rate, year fraction, optional financing base, and name. Method: `breakdown()`. |
| `HaircutAdjustmentBreakdown` | Haircut overlay breakdown. | Includes haircut amount, drag amount, financing base, and spread adjustment. |
| `ShadowCostSpreadAdjustment` | Shadow-cost overlay object. | Stores shadow cost rate, utilization or usage/capacity, pass-through, and name. Method: `breakdown()`. |
| `ShadowCostAdjustmentBreakdown` | Shadow-cost overlay breakdown. | Includes utilization, optional usage/capacity, pass-through, and spread adjustment. |
| `SecuredUnsecuredBasisModel` | Protocol for secured/unsecured overnight basis models. | Method: `basis()`. |
| `GQDSecuredUnsecuredBasisModel` | GQD-style secured/unsecured basis model. | Method: `basis()`. |
| `Sovereign` | Sovereign issuer helper. | Methods: `currency()`, `bond_name()`, `standard_tenors()`, `us_treasury()`, `uk_gilt()`, and `german_bund()`. |
| `SupranationalIssuer` | Supranational issuer classification. | Use for spread/reference classification where issuer is not one sovereign. |
| `g_spread` | Bond yield minus government yield. | Returns raw decimal. Positive means bond yield is above benchmark yield. |
| `g_spread_bps` | G-spread in basis points. | Returns `g_spread() * 10000`. |
| `g_spread_with_benchmark` | G-spread against a `GovernmentCurve`. | Returns raw decimal using interpolated, nearest, tenor-specific, or explicit benchmark selection. |
| `g_spread_with_benchmark_bps` | Curve-backed G-spread in basis points. | Returns basis points. |
| `i_spread` | Bond yield minus swap rate. | Returns raw decimal. |
| `i_spread_bps` | I-spread in basis points. | Returns `i_spread() * 10000`. |
| `z_spread` | Solves Z-spread from bond, clean price, curve, and settlement date. | Adds accrued interest to clean price before solving. Returns raw decimal. |
| `z_spread_from_curve` | Solves Z-spread from explicit cash flows and dirty price. | Returns raw decimal. |
| `z_discount_margin` | Z-style discount margin helper. | Returns raw decimal spread. |
| `simple_margin` | Simple margin helper for floating-rate pricing. | Returns raw decimal margin. |
| `reference_rate_decomposition` | Breaks funding rates into repo, GC, overnight unsecured, and term pieces. | Returns `ReferenceRateBreakdown`. All inputs and outputs are raw decimals. |
| `simple_to_compounded_equivalent_rate` | Converts simple rate to compounded equivalent. | Returns raw decimal rate. |
| `compounding_convexity_breakdown` | Builds compounding and convexity adjustment breakdown. | Returns `CompoundingConvexityBreakdown`. |
| `adjusted_term_rate` | Applies compounding and convexity adjustments to a term rate. | Returns raw decimal rate. |
| `compose_spread_adjustments` | Adds component spread adjustments to a base spread. | Returns `SpreadAdjustmentSummary`. |
| `apply_balance_sheet_overlays` | Applies adjustment objects to a base spread. | Returns `SpreadAdjustmentSummary`. |
| `apply_funding_spread_overlays` | Applies adjustment objects to a funding spread and optional credit spread. | Returns `FundingSpreadOverlayResult`. |
| `capital_adjustment_breakdown` | Computes capital overlay details. | Validates positive exposure, non-negative risk weight/hurdle/pass-through, and capital ratio between 0 and 1. |
| `capital_spread_adjustment` | Computes only the raw decimal capital spread adjustment. | Uses the same validation as `capital_adjustment_breakdown()`. |
| `haircut_adjustment_breakdown` | Computes haircut funding-drag details. | Validates positive collateral value, positive financing base, positive year fraction, and haircut between 0 and 1. |
| `haircut_spread_adjustment` | Computes only the raw decimal haircut spread adjustment. | Uses the same validation as `haircut_adjustment_breakdown()`. |
| `utilization_ratio` | Computes usage divided by capacity. | Requires non-negative usage and positive capacity. |
| `shadow_cost_adjustment_breakdown` | Computes shadow-cost overlay details. | Accepts direct utilization or usage/capacity. Requires non-negative rates and pass-through. |
| `shadow_cost_spread_adjustment` | Computes only the raw decimal shadow-cost spread adjustment. | Uses the same validation as `shadow_cost_adjustment_breakdown()`. |
| `secured_unsecured_overnight_basis` | Computes secured/unsecured overnight basis. | Returns raw decimal basis. |

### YAS And Settlement Output

| Export | What It Represents | Behavior, Methods, And Properties |
|---|---|---|
| `YASCalculator` | Builds Bloomberg-style bond analysis output. | Methods: `calculate()` and `validate_bloomberg()`. `calculate()` solves yield from clean price, computes display yields, spreads, risk, and settlement invoice. |
| `BatchYASCalculator` | Runs one `YASCalculator` over many bonds. | Method: `calculate_many()`. Bond and price list lengths must match. |
| `YasAnalysis` | YAS output record. | Yields are percentage points; spreads are basis points. Fields include YTM, street yield, true yield, current yield, simple yield, optional money-market yield, spreads, benchmark tenor, risk, and invoice. Methods: `modified_duration()`, `convexity()`, and `dv01()`. |
| `YASResult` | Alias of `YasAnalysis`. | Same fields and methods as `YasAnalysis`. |
| `YasAnalysisBuilder` | Builder for `YasAnalysis`. | Method: `build()`. It validates required yield, current-yield, simple-yield, risk, and invoice fields. |
| `BloombergReference` | Reference values for YAS validation. | Constructor stores expected YTM, spreads, duration, and convexity. Class method: `boeing_2025()`. |
| `ValidationFailure` | One YAS validation mismatch. | Fields are `field`, `expected`, `actual`, and `tolerance`. |
| `SettlementInvoice` | Settlement invoice result. | Fields include settlement date, clean price, accrued interest, dirty price, accrued days, principal cash amount, accrued cash amount, settlement cash amount, and face value. |
| `SettlementInvoiceBuilder` | Builder for `SettlementInvoice`. | Method: `build()`. Clean price and accrued interest are percent of par. Principal, accrued amount, and settlement amount are cash. |
| `calculate_accrued_amount` | Converts percent-of-par accrued interest to cash. | Returns `face_value * accrued_interest / 100`. |
| `calculate_proceeds` | Adds principal and accrued cash. | Returns settlement cash amount. |
| `calculate_settlement_date` | Resolves settlement date from trade date and settlement rules. | The required rules object is available as `YieldCalculationRules.*().settlement_rules`. |

### Callable-Bond Options

| Export | What It Represents | Behavior, Methods, And Properties |
|---|---|---|
| `BondOption` | Option on a bond. | Fields are expiry, strike, optional bond, optional model, option type, exercise style, and valuation date. Strike is coerced to `Decimal` and must be positive. Method: `price()`. |
| `BinomialTree` | Recombining tree over event dates. | Constructor `new()` sorts and deduplicates dates and requires at least two dates. Methods: `value_lattice()` and `price_cashflows()`. |
| `HullWhiteModel` | Short-rate model used by the tree pricer. | Coerces mean reversion and volatility to `Decimal`; both must be non-negative. Methods: `base_forward_rate()`, `short_rate()`, `node_rate()`, and `discount()`. |
| `ExerciseStyle` | Bond-option exercise timing enum. | Values are European and American. American exercise compares immediate payoff with continuation value at each node. |

### Exceptions

| Export | What It Means |
|---|---|
| `BondError` | Base bond-domain error with constructors `invalid_spec()`, `missing_field()`, and `pricing_failed()`. |
| `AnalyticsError` | Analytics-layer error with constructors `invalid_input()`, `invalid_settlement()`, `yield_solver_failed()`, `pricing_failed()`, and `spread_failed()`. |
| `IdentifierError` | Base identifier error. |
| `InvalidIdentifier` | Invalid identifier value. |
| `InvalidBondSpec` | Invalid bond specification, such as bad dates, coupon bounds, or frequency/rules mismatch. |
| `MissingRequiredField` | Builder is missing a required field. |
| `BondPricingError` | Bond pricing failed. |
| `YieldConvergenceFailed` | Yield solver did not converge. |
| `ScheduleError` | Schedule generation failed. |
| `SettlementError` | Settlement calculation failed. |
| `InvalidInput` | Analytics input is invalid. |
| `InvalidSettlement` | Settlement date is invalid for the requested calculation. |
| `YieldSolverError` | Yield solver failed at the analytics layer. |
| `PricingError` | Pricing failed at the analytics layer. |
| `SpreadError` | Spread calculation failed. |

## Boundaries

- Built fitted curves live in `fuggers_py.curves`.
- Inflation fixings, CPI history, and index-ratio helpers live in
  `fuggers_py.inflation`.
- CDS instruments and CDS pricing live in `fuggers_py.credit`.
- Repo and financing analytics live in `fuggers_py.funding`.
- Portfolio aggregation outside bond-specific `Position` helpers lives in
  `fuggers_py.portfolio`.

```{eval-rst}
.. automodule:: fuggers_py.bonds
   :members:
   :member-order: bysource
```
