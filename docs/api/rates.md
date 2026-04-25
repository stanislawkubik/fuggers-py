# `fuggers_py.rates`

Public home for nominal interest-rate products, rate-index conventions,
fixing storage, swap and FRA pricing, rates risk, futures delivery helpers,
and rates option pricers.

Use one-layer imports from `fuggers_py.rates` for rates objects:

```python
from fuggers_py.rates import (
    FixedFloatSwap,
    FixedLegSpec,
    FloatingLegSpec,
    IndexFixingStore,
    ScheduleDefinition,
    SwapPricer,
    SwapQuote,
    key_rate_risk,
    swap_dv01,
)
```

The public export source of truth is `fuggers_py.rates.__all__`, mirrored in
`specs/public_api_surface.json`.

## Core Rules

- Rates, spreads, basis values, volatilities, and FX forward points are raw
  decimals. `Decimal("0.05")` means 5%, and `Decimal("0.0001")` means one
  basis point.
- A basis point is one hundredth of 1%. In decimal form it is `0.0001`.
- Bond future prices and bond clean or dirty prices are percent of par.
  `112.5` means 112.5% of face value.
- Notionals and present values are currency amounts.
- PV means present value: today's value of future cash flows.
- A pay leg has a negative sign. A receive leg has a positive sign.
- `swap_dv01()` and `key_rate_risk()` return positive values when the
  instrument gains PV after rates move down by one basis point.
- Cross-currency swaps quote `spot_fx_rate` as receive-currency units per one
  pay-currency unit.
- Constructors normalize many labels. For example, `"usd"` becomes
  `Currency.USD`, `"quarterly"` becomes a quarterly frequency, and `"3M"`
  becomes a `Tenor`.
- Constructors also validate important contract rules, such as positive
  notionals and maturity dates after start dates.

## Curve Inputs Used By Pricers

Rates pricers take an instrument plus a curve container. The container is not a
special rates class. It only needs the fields the resolver reads:

- `discount_curve`
- `forward_curve`
- `collateral_curve`
- `projection_curves`
- `multicurve_environment`
- `fx_forward_curve`
- optional fields used by other analytics, such as `repo_curve` and
  `vol_surface`

The tiny curve classes below are only for examples. Real code normally uses
curves from `fuggers_py.curves`.

```python
from dataclasses import dataclass, field
from decimal import Decimal
from math import exp

from fuggers_py import Date


@dataclass(frozen=True)
class ExampleCurveSpec:
    day_count: str = "ACT_365_FIXED"


@dataclass(frozen=True)
class FlatCurve:
    reference_date: Date
    rate: Decimal
    spec: ExampleCurveSpec = field(default_factory=ExampleCurveSpec)

    def discount_factor_at(self, tenor_years: float) -> Decimal:
        return Decimal(str(exp(-float(self.rate) * float(tenor_years))))

    def zero_rate_at(self, tenor_years: float) -> Decimal:
        return self.rate

    def rate_at(self, tenor_years: float) -> Decimal:
        return self.rate

    def forward_rate_between(self, start_tenor: float, end_tenor: float) -> Decimal:
        return self.rate


@dataclass(frozen=True)
class ExampleRatesCurves:
    discount_curve: FlatCurve
    forward_curve: FlatCurve
    government_curve: object | None = None
    benchmark_curve: object | None = None
    credit_curve: object | None = None
    repo_curve: object | None = None
    collateral_curve: object | None = None
    fx_forward_curve: object | None = None
    multicurve_environment: object | None = None
    projection_curves: dict[str, object] = field(default_factory=dict)
    inflation_curve: object | None = None
    inflation_curves: dict[str, object] = field(default_factory=dict)
    vol_surface: object | None = None


valuation_date = Date.from_ymd(2026, 1, 15)
curves = ExampleRatesCurves(
    discount_curve=FlatCurve(valuation_date, Decimal("0.035")),
    forward_curve=FlatCurve(valuation_date, Decimal("0.04")),
)
```

## Schedules And Legs

These objects describe coupon periods and swap legs.

| Export | What it represents | Behavior and useful methods |
| --- | --- | --- |
| `AccrualPeriod` | One coupon accrual window. | Stores `start_date`, `end_date`, adjusted `payment_date`, and `year_fraction`. `year_fraction` is coerced to `Decimal`. |
| `ScheduleDefinition` | Rules used to build a date schedule. | Coerces frequency, calendar, and business-day convention labels. `generate(start, end)` returns a schedule. `accrual_periods(start, end, day_count_convention=...)` returns `AccrualPeriod` records. |
| `FixedLegSpec` | Fixed-rate cash-flow leg. | Coerces pay/receive, notional, fixed rate, currency, and day count. Notional must be positive. `accrual_periods(start, end)` builds fixed-leg periods. |
| `FloatingLegSpec` | Floating-rate cash-flow leg. | Coerces pay/receive, notional, spread, index tenor, currency, and day count. Index name is uppercased. Notional must be positive. `rate_index()` returns the normalized curve lookup key. `accrual_periods(start, end)` builds floating-leg periods. |

```python
from decimal import Decimal

from fuggers_py import Currency, Date, PayReceive
from fuggers_py.rates import FixedLegSpec, FloatingLegSpec, ScheduleDefinition

start = Date.from_ymd(2026, 1, 15)
end = Date.from_ymd(2027, 1, 15)

schedule = ScheduleDefinition(frequency="quarterly")
raw_schedule = schedule.generate(start, end)
periods = schedule.accrual_periods(start, end, day_count_convention="ACT_360")

fixed_leg = FixedLegSpec(
    pay_receive=PayReceive.PAY,
    notional=Decimal("1000000"),
    fixed_rate=Decimal("0.04"),
    currency=Currency.USD,
)
floating_leg = FloatingLegSpec(
    pay_receive="receive",
    notional=Decimal("1000000"),
    index_name="sofr",
    index_tenor="3M",
    spread=Decimal("0.0005"),
    currency="USD",
)

rate_index = floating_leg.rate_index()
fixed_period_count = len(fixed_leg.accrual_periods(start, end))
first_year_fraction = periods[0].year_fraction
```

## Swap, FRA, Basis, And Asset-Swap Products

These objects store dated rates trades. They do not fetch curves or market data.
They validate contract shape and expose period helpers used by pricers.

| Export | What it represents | Behavior and useful methods |
| --- | --- | --- |
| `FixedFloatSwap` | Fixed-rate leg against floating-rate leg in one currency. | Maturity must be after effective date. Legs must share currency and have opposite pay/receive directions. `currency()`, `fixed_periods()`, and `floating_periods()` expose derived data. |
| `InterestRateSwap` | Alias for `FixedFloatSwap`. | It is the same class, not a separate product type. |
| `Ois` | Overnight indexed swap. | Subclass of `FixedFloatSwap` with `kind == "rates.swap.ois"`. It reuses fixed-float validation. |
| `OvernightIndexedSwap` | Alias for `Ois`. | It is the same class, not a separate product type. |
| `Fra` | Forward-rate agreement. | Stores start date, end date, notional, fixed rate, pay/receive direction, currency, day count, and optional index metadata. `year_fraction()` returns the accrual factor. `rate_index()` returns the normalized index when `index_tenor` is set. |
| `ForwardRateAgreement` | Alias for `Fra`. | It is the same class, not a separate product type. |
| `BasisSwap` | Same-currency floating leg against floating leg. | Legs must share currency. `pay_leg` must be marked pay, and `receive_leg` must be marked receive. `currency()`, `pay_periods()`, `receive_periods()`, and `quoted_leg_spec()` expose derived data. |
| `SameCurrencyBasisSwap` | Alias for `BasisSwap`. | It is the same class, not a separate product type. |
| `CrossCurrencyBasisSwap` | Floating leg in one currency against floating leg in another currency. | Legs must use different currencies. `spot_fx_rate` must be positive and is quoted as receive-currency per pay-currency. `currency_pair()`, `pay_periods()`, `receive_periods()`, and `quoted_leg_spec()` expose derived data. |
| `AssetSwap` | Fixed-rate bond plus floating leg. | Exactly one of `market_clean_price` or `market_dirty_price` is required. Prices are percent of par. `currency()`, `maturity_date()`, `accrued_interest()`, `dirty_price()`, `clean_price()`, and `effective_floating_notional()` expose derived values. |

### Swap Pricing And Risk

`SwapPricer` discounts the fixed and floating coupons. The fixed leg uses the
discount curve. The floating leg uses the projection curve for its index and
tenor. The result PV is in the swap currency.

```python
from decimal import Decimal

from fuggers_py import Currency, Date, PayReceive
from fuggers_py.rates import (
    FixedFloatSwap,
    FixedLegSpec,
    FloatingLegSpec,
    SwapPricer,
    key_rate_risk,
    swap_dv01,
)

effective = Date.from_ymd(2026, 1, 15)
maturity = Date.from_ymd(2031, 1, 15)

swap = FixedFloatSwap(
    effective_date=effective,
    maturity_date=maturity,
    fixed_leg=FixedLegSpec(
        pay_receive=PayReceive.PAY,
        notional=Decimal("1000000"),
        fixed_rate=Decimal("0.04"),
        currency=Currency.USD,
    ),
    floating_leg=FloatingLegSpec(
        pay_receive=PayReceive.RECEIVE,
        notional=Decimal("1000000"),
        index_name="SOFR",
        index_tenor="3M",
        currency=Currency.USD,
    ),
)

pricer = SwapPricer()
result = pricer.price(swap, curves)

par_rate = pricer.par_rate(swap, curves)
present_value = pricer.pv(swap, curves)
dv01 = swap_dv01(swap, curves)
key_rates = key_rate_risk(swap, curves, tenor_grid=("2Y", "5Y", "10Y"))

summary = {
    "par_rate": result.par_rate,
    "pv": present_value,
    "fixed_leg_pv": result.fixed_leg_pv,
    "floating_leg_pv": result.floating_leg_pv,
    "dv01": dv01,
    "five_year_key_rate": key_rates["5Y"],
}
```

### FRA Pricing

`FraPricer` projects the forward rate for the FRA accrual window and discounts
the payoff to the FRA start date. The sign follows the FRA holder's
pay/receive direction.

```python
from decimal import Decimal

from fuggers_py import Currency, Date, PayReceive
from fuggers_py.rates import Fra, FraPricer

fra = Fra(
    start_date=Date.from_ymd(2026, 4, 15),
    end_date=Date.from_ymd(2026, 7, 15),
    notional=Decimal("5000000"),
    fixed_rate=Decimal("0.039"),
    pay_receive=PayReceive.RECEIVE,
    currency=Currency.USD,
    index_name="SOFR",
    index_tenor="3M",
)

fra_pricer = FraPricer()
fra_result = fra_pricer.price(fra, curves)

fra_outputs = {
    "index": fra.rate_index(),
    "year_fraction": fra.year_fraction(),
    "forward_rate": fra_result.forward_rate,
    "pv": fra_result.present_value,
}
```

### Basis And Cross-Currency Basis Pricing

`BasisSwapPricer` solves the spread for the quoted leg. `CrossCurrencyBasisSwapPricer`
does the same, but it also converts cash flows into the selected valuation
currency. If no explicit FX forward curve is supplied, it derives forward FX
from the two discount curves and the swap spot FX rate.

```python
from decimal import Decimal

from fuggers_py import Currency, Date, PayReceive
from fuggers_py.rates import (
    BasisSwap,
    BasisSwapPricer,
    CrossCurrencyBasisSwap,
    CrossCurrencyBasisSwapPricer,
    FloatingLegSpec,
)

basis = BasisSwap(
    effective_date=Date.from_ymd(2026, 1, 15),
    maturity_date=Date.from_ymd(2029, 1, 15),
    pay_leg=FloatingLegSpec(PayReceive.PAY, Decimal("1000000"), "SOFR", "1M"),
    receive_leg=FloatingLegSpec(PayReceive.RECEIVE, Decimal("1000000"), "SOFR", "3M"),
    quoted_leg=PayReceive.RECEIVE,
)

basis_pricer = BasisSwapPricer()
basis_result = basis_pricer.price(basis, curves)
basis_leg = basis.quoted_leg_spec()

xccy = CrossCurrencyBasisSwap(
    effective_date=Date.from_ymd(2026, 1, 15),
    maturity_date=Date.from_ymd(2029, 1, 15),
    pay_leg=FloatingLegSpec(PayReceive.PAY, Decimal("900000"), "EURIBOR", "3M", currency=Currency.EUR),
    receive_leg=FloatingLegSpec(PayReceive.RECEIVE, Decimal("1000000"), "SOFR", "3M", currency=Currency.USD),
    spot_fx_rate=Decimal("1.10"),
    quoted_leg=PayReceive.RECEIVE,
)

xccy_pricer = CrossCurrencyBasisSwapPricer()
xccy_result = xccy_pricer.price(xccy, curves, valuation_currency=Currency.USD)

basis_outputs = {
    "basis_par_spread": basis_result.par_spread,
    "quoted_leg_index": basis_leg.rate_index(),
    "xccy_pair": xccy.currency_pair(),
    "xccy_pv_usd": xccy_result.present_value,
    "principal_exchange_pv": xccy_result.principal_exchange_pv,
}
```

### Asset-Swap Pricing

`AssetSwapPricer` uses the bond, the floating leg, the market bond price, and
the resolved curves. It returns a par spread, PV, funding component, credit
component, and a detailed breakdown. Funding and credit components are spreads,
not currency amounts. Breakdown PV fields are currency amounts.

```python
from decimal import Decimal

from fuggers_py import Currency, Date, Frequency, PayReceive
from fuggers_py.bonds import FixedBondBuilder
from fuggers_py.rates import AssetSwap, AssetSwapPricer, FloatingLegSpec

bond = (
    FixedBondBuilder.new()
    .with_issue_date(Date.from_ymd(2021, 1, 15))
    .with_maturity_date(Date.from_ymd(2031, 1, 15))
    .with_coupon_rate(Decimal("0.035"))
    .with_frequency(Frequency.SEMI_ANNUAL)
    .with_currency(Currency.USD)
    .with_notional(Decimal("100"))
    .build()
)

asset_swap = AssetSwap(
    bond=bond,
    settlement_date=Date.from_ymd(2026, 1, 15),
    floating_leg=FloatingLegSpec(PayReceive.RECEIVE, Decimal("1000000"), "SOFR", "3M"),
    quoted_spread=Decimal("0.0010"),
    market_clean_price=Decimal("99.25"),
)

asset_swap_pricer = AssetSwapPricer()
asset_swap_result = asset_swap_pricer.price(asset_swap, curves)

asset_swap_outputs = {
    "clean_price": asset_swap.clean_price(),
    "dirty_price": asset_swap.dirty_price(),
    "effective_floating_notional": asset_swap.effective_floating_notional(),
    "par_spread": asset_swap_result.par_spread,
    "pv": asset_swap_result.present_value,
    "funding_component": asset_swap_result.funding_component,
    "credit_component": asset_swap_result.credit_component,
}
```

## Pricing And Risk Reference

| Export | What it represents | Behavior and outputs |
| --- | --- | --- |
| `SwapPricer` | Fixed-float swap pricer. | `annuity()` returns discounted fixed-leg accrual notional. `fixed_leg_pv()` and `floating_leg_pv()` return signed currency PVs. `par_rate()` returns the raw decimal fixed rate that sets PV to zero. `pv()` returns total signed PV. `price()` returns `SwapPricingResult`. |
| `SwapPricingResult` | Full swap pricing output. | Fields: `par_rate`, `present_value`, `fixed_leg_pv`, `floating_leg_pv`, and `annuity`. PV fields are currency amounts. |
| `FraPricer` | FRA pricer. | `forward_rate()` projects the FRA rate. `pv()` returns signed currency PV. `price()` returns `FraPricingResult`. |
| `FraPricingResult` | FRA pricing output. | Fields: `forward_rate`, `present_value`, `year_fraction`, and `discount_factor`. |
| `BasisSwapPricer` | Same-currency basis-swap pricer. | `pay_leg_pv()`, `receive_leg_pv()`, `pv()`, `par_spread()`, and `price()` use the quoted leg to solve the par spread. |
| `BasisSwapPricingResult` | Basis-swap pricing output. | Fields: `par_spread`, `present_value`, `pay_leg_pv`, `receive_leg_pv`, and `spread_annuity`. |
| `CrossCurrencyBasisSwapPricer` | Cross-currency basis-swap pricer. | `pay_leg_pv()`, `receive_leg_pv()`, `principal_exchange_pv()`, `pv()`, `par_spread()`, and `price()` report values in `valuation_currency`. |
| `CrossCurrencyBasisSwapPricingResult` | Cross-currency basis result. | Fields: `valuation_currency`, `par_spread`, `present_value`, leg PVs, `principal_exchange_pv`, and `spread_annuity`. |
| `AssetSwapPricer` | Asset-swap pricer. | `par_spread()`, `funding_component()`, `credit_component()`, `pv()`, and `price()` decompose a bond asset swap. |
| `AssetSwapPricingResult` | Asset-swap pricing output. | Fields: `par_spread`, `present_value`, `funding_component`, `credit_component`, and `breakdown`. |
| `AssetSwapBreakdown` | Detailed asset-swap calculation record. | Fields include clean and dirty price, accrued interest, quoted spread, annuity, spread PV factor, effective floating notional, reference rates, and funding/credit PV pieces. |
| `swap_dv01` | One-basis-point risk for fixed-float and OIS swaps. | Bumps relevant curves up and down by default `0.0001`. Positive means PV rises when rates fall. |
| `key_rate_risk` | Tenor-by-tenor risk map. | Bumps each tenor node separately and returns `dict[str, Decimal]`. Keys are tenor labels such as `"5Y"`. Positive means PV rises when that tenor is bumped lower. |

## Quotes, Reference Data, Fixings, And Indices

These objects store market quotes and reference-index fixings. They do not price
trades by themselves.

| Export | What it represents | Behavior and useful methods |
| --- | --- | --- |
| `SwapQuote` | Swap market quote. | Stores `rate`, optional `bid`, `ask`, and `mid`. Decimal fields are coerced. Tenor and index labels are normalized. `quoted_value(side="mid")` returns a side value. `for_side(side)` returns a copy with `rate` set to that side, or `None`. |
| `BasisSwapQuote` | Basis-swap market quote. | Same side behavior as `SwapQuote`, but the main value field is `basis`. |
| `BondFutureQuote` | Government bond future quote. | Same side behavior as `SwapQuote`, but the main value field is `price`. Delivery month and CTD id are parsed when supplied. |
| `FxForwardQuote` | FX forward quote. | Stores a currency pair, forward rate, spot rate, and points. If `forward_rate` is missing and both `spot_rate` and `points` are present, it sets `forward_rate = spot_rate + points`. Properties: `instrument_id` and `currency`. Methods: `quoted_value()` and `for_side()`. |
| `SwapReferenceData` | Static swap reference metadata. | Parses `instrument_id`; uppercases tenor, floating index, day count, and calendar labels. |
| `ArrearConvention` | Whether a coupon resets in advance or in arrears. | Values: `IN_ADVANCE`, `IN_ARREARS`. |
| `ObservationShiftType` | How overnight observation dates are shifted. | Values: `NONE`, `LOOKBACK`, `OBSERVATION_SHIFT`. |
| `ShiftType` | Alias for `ObservationShiftType`. | It is the same enum, not a separate type. |
| `LookbackDays` | Small record for a business-day lookback count. | `int(value)` returns the day count. |
| `LockoutDays` | Small record for a final-days lockout count. | `int(value)` returns the day count. |
| `OvernightCompounding` | How overnight fixings become one period rate. | Values: `COMPOUNDED`, `SIMPLE`, and `AVERAGED`. `compounded_rate()`, `simple_average_rate()`, `required_fixing_dates()`, and `accrual_factor()` compute period data. |
| `PublicationTime` | When a daily fixing is published. | Values: `SAME_DAY`, `END_OF_DAY`, `NEXT_BUSINESS_DAY`. |
| `IndexConventions` | Rules for a floating or overnight index. | Defaults to ACT/360, compounded overnight, same-day publication, and no shift. Properties: `observation_shift_type` and `observation_shift_days`. |
| `IndexSource` | Where a fixing came from. | Values: `MANUAL`, `PUBLICATION`, `CURVE`, and `FALLBACK`. |
| `IndexFixing` | One fixing for one index and date. | Uppercases `index_name`; coerces `rate` to `Decimal`. |
| `IndexFixingStore` | In-memory fixing store. | `from_rates()`, `add_fixing()`, `add_fixings()`, `get_fixing()`, `get_rate()`, `has_fixing()`, `history()`, `get_range()`, `last_fixing_before()`, `indices()`, `count()`, `has_index()`, `clear()`, and `rate_for_period()` manage and use fixings. |
| `BondIndex` | Reference-rate definition with optional fixing store. | `fixing(date)` returns a stored rate. `rate_for_period(start, end, ...)` asks the store for a period rate, using conventions, fallback rates, or a forward curve. `str(index)` returns the name. |

```python
from decimal import Decimal

from fuggers_py import Currency, Date
from fuggers_py.rates import (
    BondIndex,
    FxForwardQuote,
    IndexConventions,
    IndexFixingStore,
    OvernightCompounding,
    SwapQuote,
)

swap_quote = SwapQuote(
    instrument_id="USD-SOFR-5Y",
    rate=Decimal("0.0410"),
    bid=Decimal("0.0409"),
    ask=Decimal("0.0411"),
    tenor="5y",
    floating_index="sofr",
    currency=Currency.USD,
)
mid_rate = swap_quote.quoted_value()
bid_quote = swap_quote.for_side("bid")

fx_quote = FxForwardQuote(
    currency_pair="EUR/USD",
    spot_rate=Decimal("1.1000"),
    points=Decimal("0.0025"),
)
forward_rate = fx_quote.forward_rate
quote_currency = fx_quote.currency

store = IndexFixingStore.from_rates(
    "SOFR",
    {
        Date.from_ymd(2026, 1, 15): Decimal("0.0395"),
        Date.from_ymd(2026, 1, 16): Decimal("0.0396"),
    },
)
store.add_fixing("SOFR", Date.from_ymd(2026, 1, 20), Decimal("0.0397"))

conventions = IndexConventions(overnight_compounding=OvernightCompounding.COMPOUNDED)
period_rate = store.rate_for_period(
    "SOFR",
    Date.from_ymd(2026, 1, 15),
    Date.from_ymd(2026, 1, 22),
    conventions=conventions,
    fallback_rate=Decimal("0.0396"),
)
needed_fixings = OvernightCompounding.COMPOUNDED.required_fixing_dates(
    Date.from_ymd(2026, 1, 15),
    Date.from_ymd(2026, 1, 22),
    conventions=conventions,
)

sofr = BondIndex(name="SOFR", conventions=conventions, fixing_store=store)
latest_rate = sofr.fixing(Date.from_ymd(2026, 1, 20))
```

## Government Bond Futures

These exports support deliverable government bond futures. Futures prices are
percent of par. Invoice amounts are currency values.

| Export | What it represents | Behavior and useful methods |
| --- | --- | --- |
| `GovernmentBondFuture` | Listed government bond future contract. | Stores delivery date or delivery window, contract size, tick size, standard coupon, coupon frequency, and exchange. Requires a delivery anchor. `from_reference(reference, delivery_date=...)` builds from futures reference data. `resolved_delivery_date()` picks the best date anchor. `tick_value()` returns the currency value of one tick. |
| `DeliverableBond` | One bond that can be delivered into a futures contract. | Clean price is percent of par. Coupon rate is a raw decimal. `from_reference()`, `reference()`, `rules()`, `to_bond()`, `accrued_interest()`, `dirty_price()`, `yield_to_maturity()`, `price_from_yield()`, and `price_with_yield_shift()` expose bond and delivery calculations. |
| `DeliverableBasket` | Ordered set of deliverable bonds. | Requires at least one bond, unique ids, and one common currency. `currency()`, `instrument_ids()`, and `get_deliverable()` expose basket data. |
| `conversion_factor` | Selects the conversion factor for one deliverable. | Computes the theoretical factor and can prefer an exchange-published factor. Returns a result object with `theoretical_conversion_factor`, selected `conversion_factor`, and `used_published_override`. The result type is not exported by `fuggers_py.rates`. |
| `invoice_amount` | Converts futures price and conversion factor into delivery cash amount. | Formula: `contract_size * (futures_price * conversion_factor + accrued_interest) / 100`. |
| `cheapest_to_deliver` | Ranks the basket and selects the cheapest-to-deliver bond. | Lower gross basis wins. The returned result object includes the selected id, conversion factor, gross basis, delivery payoff, and ranked candidates. The result type is not exported by `fuggers_py.rates`. |

```python
from decimal import Decimal

from fuggers_py import Currency, Date, Frequency
from fuggers_py.rates import (
    DeliverableBasket,
    DeliverableBond,
    GovernmentBondFuture,
    cheapest_to_deliver,
    conversion_factor,
    invoice_amount,
)

future = GovernmentBondFuture(
    delivery_month="2026-06",
    instrument_id="USM6",
    currency=Currency.USD,
    contract_size=Decimal("100000"),
    tick_size=Decimal("0.015625"),
    standard_coupon_rate=Decimal("0.06"),
    coupon_frequency=Frequency.SEMI_ANNUAL,
    exchange="CBOT",
)

# Use this form when reference data gives you a contract reference object.
# reference_contract = GovernmentBondFuture.from_reference(reference)

bond_a = DeliverableBond(
    instrument_id="91282C-example-A",
    issue_date=Date.from_ymd(2021, 5, 15),
    maturity_date=Date.from_ymd(2031, 5, 15),
    coupon_rate=Decimal("0.0375"),
    clean_price=Decimal("101.25"),
    published_conversion_factor=Decimal("0.8750"),
)
bond_b = DeliverableBond(
    instrument_id="91282C-example-B",
    issue_date=Date.from_ymd(2020, 8, 15),
    maturity_date=Date.from_ymd(2030, 8, 15),
    coupon_rate=Decimal("0.0300"),
    clean_price=Decimal("98.75"),
    published_conversion_factor=Decimal("0.8420"),
)

basket = DeliverableBasket(as_of=Date.from_ymd(2026, 1, 15), deliverables=(bond_a, bond_b))

tick_value = future.tick_value()
selected_factor = conversion_factor(future, bond_a).conversion_factor
cash_due = invoice_amount(
    future.contract_size,
    futures_price=Decimal("112.50"),
    conversion_factor=selected_factor,
    accrued_interest=bond_a.accrued_interest(future.resolved_delivery_date()),
)
ctd = cheapest_to_deliver(future, basket, futures_price=Decimal("112.50"))
selected_bond = basket.get_deliverable(ctd.cheapest_to_deliver)
```

## Rates Options

Rates options include swaptions, caps/floors, and options on government bond
futures.

| Export | What it represents | Behavior and useful methods |
| --- | --- | --- |
| `CapFloorType` | Cap or floor label. | `parse()` accepts `"CAP"`, `"CAPLET_STRIP"`, `"FLOOR"`, and `"FLOORLET_STRIP"`. `option_type()` maps caps to calls and floors to puts. |
| `CapFloor` | Cap or floor on a floating leg. | Strike is a raw decimal and must be non-negative. Maturity must be after effective date. `currency()`, `option_type()`, and `optionlet_periods()` expose derived data. |
| `Swaption` | European option on a fixed-float swap. | Strike is a raw decimal and must be non-negative. Expiry must be on or before the underlying swap effective date. `currency()`, `underlying`, and `option_type()` expose derived data. Payer swaptions are calls on the swap rate; receiver swaptions are puts. |
| `FuturesOption` | Option on a government bond future. | Strike is in futures price points and must be positive. Expiry must be on or before delivery. `currency()`, `underlying`, and `contract_multiplier()` expose derived data. |
| `Black76Pricer` | Lognormal rates option pricer. | Assumes positive forwards and strikes. `formula()` prices a simple call or put. `swaption()`, `cap_floor()`, and `futures_option()` price products. Volatility is raw decimal lognormal volatility. |
| `BachelierPricer` | Normal rates option pricer. | Works with additive moves and can handle low or negative forwards. Methods mirror `Black76Pricer`. Volatility is raw decimal normal volatility. |
| `HullWhiteOptionPricer` | Lightweight Hull-White style proxy. | Converts model parameters into an approximate normal volatility, then delegates to `BachelierPricer`. The helper model class `HullWhiteRateOptionModel` is not exported by `fuggers_py.rates`; pass any object with `normal_volatility(expiry_years=..., underlying_tenor_years=...)`, or import the model from the deeper options module when you intentionally leave the one-layer facade. |
| `HasExpiry` | Typing helper for objects with `expiry_date`. | Use in type hints when a function only needs an expiry date. |
| `HasOptionType` | Typing helper for option-like objects. | Use in type hints when a function only needs an `option_type()` method. |
| `HasUnderlyingInstrument` | Typing helper for option-like objects with `underlying`. | Use in type hints when a function only needs the underlying product. |

Option formula and option pricing result records are returned by methods, but
they are not exported from `fuggers_py.rates`. Use their attributes directly.

```python
from dataclasses import dataclass
from decimal import Decimal

from fuggers_py import Date, OptionType, PayReceive
from fuggers_py.rates import (
    BachelierPricer,
    Black76Pricer,
    CapFloor,
    CapFloorType,
    FuturesOption,
    HasExpiry,
    HullWhiteOptionPricer,
    Swaption,
)

normal_result = BachelierPricer().formula(
    forward=Decimal("0.04"),
    strike=Decimal("0.0425"),
    volatility=Decimal("0.01"),
    expiry_years=Decimal("1.0"),
    option_type=OptionType.CALL,
)
lognormal_result = Black76Pricer().formula(
    forward=Decimal("0.04"),
    strike=Decimal("0.0425"),
    volatility=Decimal("0.20"),
    expiry_years=Decimal("1.0"),
    option_type=OptionType.CALL,
)

swaption = Swaption(
    expiry_date=Date.from_ymd(2026, 1, 15),
    underlying_swap=swap,
    strike=Decimal("0.04"),
    exercise_into=PayReceive.PAY,
)
swaption_price = BachelierPricer().swaption(
    swaption,
    curves,
    volatility=Decimal("0.01"),
)

cap = CapFloor(
    effective_date=Date.from_ymd(2026, 1, 15),
    maturity_date=Date.from_ymd(2028, 1, 15),
    floating_leg=swap.floating_leg,
    strike=Decimal("0.045"),
    cap_floor_type=CapFloorType.parse("caplet_strip"),
)
cap_price = BachelierPricer().cap_floor(cap, curves, volatility=Decimal("0.012"))

future_option = FuturesOption(
    expiry_date=Date.from_ymd(2026, 5, 15),
    underlying_future=future,
    strike=Decimal("112.0"),
    option_type=OptionType.CALL,
)
future_option_price = BachelierPricer().futures_option(
    future_option,
    futures_price=Decimal("112.50"),
    volatility=Decimal("1.25"),
)


@dataclass(frozen=True)
class FlatHullWhiteProxy:
    normal_vol: Decimal

    def normal_volatility(self, *, expiry_years: object, underlying_tenor_years: object) -> Decimal:
        return self.normal_vol


hull_white_price = HullWhiteOptionPricer(
    model=FlatHullWhiteProxy(Decimal("0.01")),
).swaption(swaption, curves)


def expires_on(option: HasExpiry) -> Date:
    return option.expiry_date


option_outputs = {
    "normal_formula_pv": normal_result.present_value,
    "black_formula_pv": lognormal_result.present_value,
    "swaption_pv": swaption_price.present_value,
    "cap_pv": cap_price.present_value,
    "futures_option_pv": future_option_price.present_value,
    "futures_option_multiplier": future_option.contract_multiplier(),
    "swaption_expiry": expires_on(swaption),
    "swaption_underlying": swaption.underlying,
}
```

## Aliases

These exports are alternate names. They do not add behavior.

| Alias | Same object as |
| --- | --- |
| `InterestRateSwap` | `FixedFloatSwap` |
| `ForwardRateAgreement` | `Fra` |
| `SameCurrencyBasisSwap` | `BasisSwap` |
| `OvernightIndexedSwap` | `Ois` |
| `ShiftType` | `ObservationShiftType` |

Use the alias when it makes the calling code easier to read. Use the base name
when you want the most direct link to the implementation.

## Boundaries

- Built curves live in `fuggers_py.curves`.
- Bond instruments delivered into futures baskets live in `fuggers_py.bonds`.
- Inflation swaps and CPI history live in `fuggers_py.inflation`.
- Volatility surface records live in `fuggers_py.vol_surfaces`.
- Low-level option formula result records and futures helper result records are
  returned by rates methods, but they are not exported from `fuggers_py.rates`.

```{eval-rst}
.. automodule:: fuggers_py.rates
   :members:
   :member-order: bysource
```
