# `fuggers_py.credit`

Public home for credit default swap (CDS) instruments, CDS quote records, CDS
pricing, CDS risk, and bond-CDS relative value.

Use one-layer imports from `fuggers_py.credit` for credit objects and helpers.

```python
from fuggers_py.credit import (
    Cds,
    CdsPricer,
    CdsQuote,
    ProtectionSide,
    adjusted_cds_spread,
    bond_cds_basis,
    cds_cs01,
)
```

## What This Package Owns

`credit` owns:

- CDS instruments: `Cds`, `CreditDefaultSwap`, `CdsPremiumPeriod`, and
  `ProtectionSide`.
- CDS market records: `CdsQuote` and `CdsReferenceData`.
- CDS pricing: `CdsPricer` and `CdsPricingResult`.
- CDS risk helpers: `risky_pv01`, `cds_cs01`, and `cs01`.
- Bond-CDS relative value helpers: `adjusted_cds_spread`,
  `adjusted_cds_breakdown`, `bond_cds_basis`, `bond_cds_basis_breakdown`,
  `cds_adjusted_risk_free_rate`, and `proxy_risk_free_breakdown`.
- Result records for the relative value helpers: `AdjustedCdsBreakdown`,
  `BondCdsBasisBreakdown`, and `RiskFreeProxyBreakdown`.

## Conventions

- Rates and spreads are raw decimals. `0.0125` means 1.25%, or 125 basis
  points.
- A basis point is `0.0001`.
- Recovery rates are raw decimals. `0.40` means 40%.
- CDS notionals, present values, premium legs, protection legs, risky PV01, and
  CS01 are currency-unit `Decimal` values.
- `upfront` fields are raw decimals of notional. `0.02` means 2% of notional.
- `ProtectionSide.BUY` means buying default protection. `ProtectionSide.SELL`
  means selling default protection.
- `Cds` is exactly the same class as `CreditDefaultSwap`. Use `Cds` for shorter
  code, or `CreditDefaultSwap` when the full name is clearer.
- `cs01` is exactly the same function as `cds_cs01`.

## CDS Instruments

### `Cds` and `CreditDefaultSwap`

`CreditDefaultSwap` represents one CDS contract. Use it when you need to build
premium payment dates, price a CDS, or calculate CDS spread risk.

`Cds` is an alias for `CreditDefaultSwap`.

The main inputs are:

- `effective_date`: first accrual date.
- `maturity_date`: final accrual date. It must be after `effective_date`.
- `running_spread`: the quoted running spread as a raw decimal.
- `notional`: currency amount used to scale pricing results. It must be
  positive.
- `protection_side`: buy or sell protection.
- `recovery_rate`: expected recovered fraction after default. It must be in
  `[0, 1)`.
- `currency`: payment currency.
- `payment_frequency`, `day_count_convention`, `calendar`,
  `business_day_convention`, `end_of_month`, and `stub_rules`: schedule rules.
- `accrued_on_default_fraction`: fraction of a coupon period accrued if default
  happens inside that period. It must be in `[0, 1]`.
- `upfront`: upfront amount as a decimal of notional.
- `settlement_date`: stored on the instrument. The current CDS pricer does not
  use it; pricing valuation dates come from the curves.
- `reference_entity` and `instrument_id`: optional labels used by callers.

Constructor behavior:

- Decimal-like values are converted to `Decimal`.
- `protection_side` accepts `ProtectionSide` values or strings such as
  `"buy"`, `"buy protection"`, `"sell"`, and `"protection seller"`.
- `currency`, `payment_frequency`, `day_count_convention`, `calendar`, and
  `business_day_convention` accept their normal objects or supported strings.
- `reference_entity` is stripped of surrounding spaces.
- `instrument_id` is parsed into an `InstrumentId`.
- A zero payment frequency is rejected.

Useful public property and methods:

- `kind`: returns `"credit.cds"`.
- `schedule()`: builds the payment schedule from the CDS dates and schedule
  rules.
- `premium_periods()`: returns one `CdsPremiumPeriod` for each premium accrual
  period.
- `loss_given_default()`: returns `1 - recovery_rate`.
- `upfront_amount()`: returns `notional * upfront`.

### `CdsPremiumPeriod`

`CdsPremiumPeriod` is one premium accrual period. It stores:

- `start_date`: period accrual start.
- `end_date`: period accrual end.
- `payment_date`: date when the premium for the period is paid.
- `year_fraction`: accrual length as a `Decimal`.

`premium_periods()` creates these records from the instrument schedule and day
count rule.

### `ProtectionSide`

`ProtectionSide` stores the payoff direction.

- `ProtectionSide.BUY` has sign `+1`.
- `ProtectionSide.SELL` has sign `-1`.
- `parse(value)` accepts supported strings and returns the enum value.
- `sign()` returns `Decimal(1)` for `BUY` and `Decimal(-1)` for `SELL`.
- `opposite()` returns the other side.

Example:

```python
from decimal import Decimal

from fuggers_py import Date, InstrumentId
from fuggers_py.credit import Cds, ProtectionSide

cds = Cds(
    effective_date=Date.from_ymd(2026, 1, 15),
    maturity_date=Date.from_ymd(2031, 1, 15),
    running_spread=Decimal("0.0125"),
    notional=Decimal("10000000"),
    protection_side="buy protection",
    recovery_rate="0.40",
    currency="USD",
    payment_frequency="quarterly",
    day_count_convention="ACT/360",
    business_day_convention="modified following",
    upfront=Decimal("0.01"),
    reference_entity=" ACME Corp ",
    instrument_id=InstrumentId("ACME-CDS-5Y"),
)

assert cds.protection_side is ProtectionSide.BUY
assert cds.kind == "credit.cds"
assert cds.loss_given_default() == Decimal("0.60")
assert cds.upfront_amount() == Decimal("100000.00")

periods = cds.premium_periods()
first_period = periods[0]

print(first_period.start_date, first_period.end_date)
print(first_period.payment_date, first_period.year_fraction)

sell_side = cds.protection_side.opposite()
assert sell_side.sign() == Decimal("-1")
```

## Quotes And Reference Data

### `CdsQuote`

`CdsQuote` stores a market quote for one CDS. Use it when you need a clean quote
record with an instrument id, spread, upfront, recovery, tenor, source, and
optional bid/ask/mid values.

Fields:

- `instrument_id`: parsed into `InstrumentId`.
- `par_spread`: running spread as a raw decimal.
- `upfront`: upfront as a raw decimal of notional.
- `recovery_rate`: recovery as a raw decimal.
- `tenor`: stripped and uppercased when present.
- `reference_entity`: stripped when present.
- `as_of`, `currency`, and `source`: quote metadata.
- `bid`, `ask`, and `mid`: side-specific quote values.

Constructor behavior:

- Decimal-like quote fields are converted to `Decimal`.
- If `mid` is missing and both `bid` and `ask` are present, `mid` becomes their
  average.
- If `mid` is still missing, it falls back to `par_spread` when present, then to
  `upfront`.

Useful public methods:

- `quoted_value(side="mid")`: returns `bid`, `ask`, or `mid`. The side can be a
  quote-side enum or the strings `"bid"`, `"ask"`, or `"mid"`.
- `for_side(side)`: returns a copy with `par_spread` set to the chosen side. It
  returns `None` if that side is unavailable.

### `CdsReferenceData`

`CdsReferenceData` stores static reference information for a CDS. Use it for
descriptive data that changes rarely, such as reference entity, tenor,
seniority, restructuring clause, coupon, and recovery rate.

Constructor behavior:

- `instrument_id` is parsed into `InstrumentId`.
- `reference_entity` is stripped.
- `tenor`, `seniority`, and `restructuring_clause` are stripped and uppercased.
- `coupon` and `recovery_rate` are converted to `Decimal` when present.

Example:

```python
from decimal import Decimal

from fuggers_py import Date, Currency
from fuggers_py.credit import CdsQuote, CdsReferenceData

quote = CdsQuote(
    instrument_id="acme-cds-5y",
    par_spread="0.0120",
    recovery_rate="0.40",
    tenor=" 5y ",
    reference_entity=" ACME Corp ",
    as_of=Date.from_ymd(2026, 1, 15),
    currency=Currency.USD,
    source=" dealer sheet ",
    bid=Decimal("0.0115"),
    ask=Decimal("0.0125"),
)

assert quote.tenor == "5Y"
assert quote.reference_entity == "ACME Corp"
assert quote.mid == Decimal("0.0120")
assert quote.quoted_value("ask") == Decimal("0.0125")

ask_quote = quote.for_side("ask")
assert ask_quote is not None
assert ask_quote.par_spread == Decimal("0.0125")

reference = CdsReferenceData(
    instrument_id="acme-cds-5y",
    reference_entity=" ACME Corp ",
    tenor=" 5y ",
    seniority=" snrfor ",
    restructuring_clause=" xr ",
    coupon="0.05",
    recovery_rate="0.40",
)

assert reference.tenor == "5Y"
assert reference.seniority == "SNRFOR"
assert reference.coupon == Decimal("0.05")
```

## Pricing And Risk

### Curve Inputs

`CdsPricer` takes a CDS and a curve container. A curve container can be any
object with the attributes the pricer needs.

For discounting, the pricer looks in this order:

1. `curves.multicurve_environment.discount_curve(cds.currency)`.
2. `curves.discount_curve`.
3. `curves.collateral_curve`.

The selected discount curve must expose:

- `reference_date`: a `Date`.
- `discount_factor_at(tenor)`: discount factor for a year-based tenor.
- `spec.day_count`: a day-count label such as `"ACT/365F"`.

For credit risk, the pricer uses `curves.credit_curve`.

The credit curve must expose `reference_date` and one of these ways to get
survival probability:

- `survival_probability(date)`.
- `survival_probability_at_tenor(tenor)`.
- `value_type` plus `value_at_tenor(tenor)` or `value_at(tenor)`, where the
  value type name ends in `SURVIVAL_PROBABILITY`, `HAZARD_RATE`, or
  `CREDIT_SPREAD`.

Survival probability means the chance the reference entity has not defaulted by
the given date. If the credit curve stores hazard rates, the pricer converts
the hazard rate into survival probability. If it stores credit spreads, the
pricer converts spread into hazard using `spread / (1 - recovery_rate)`.

The valuation date is the later of the discount curve reference date and the
credit curve reference date. Premium periods ending on or before that valuation
date are skipped.

### `CdsPricer`

`CdsPricer` prices a CDS from discount and credit curves.

Constructor inputs:

- `default_timing_fraction`: where default is assumed to happen inside each
  premium period. `0` means period start, `0.5` means midpoint, and `1` means
  period end. It must be in `[0, 1]`.
- `cs01_bump`: spread bump used by `cs01()`. The default is `0.0001`, one basis
  point.

Useful public methods:

- `risky_pv01(cds, curves)`: currency value of one full `1.0` running-spread
  unit. Multiply by `0.0001` to get one-basis-point spread value.
- `accrued_on_default(cds, curves)`: expected accrued premium paid when default
  happens inside a period.
- `protection_leg(cds, curves)`: expected default protection payment.
- `premium_leg(cds, curves)`: `cds.running_spread * risky_pv01`.
- `par_spread(cds, curves)`: spread that makes the premium leg match the
  protection leg.
- `upfront(cds, curves)`: `(protection_leg - premium_leg) / notional`, returned
  as a raw decimal of notional.
- `pv(cds, curves)`: signed present value after subtracting the CDS upfront
  amount.
- `cs01(cds, curves)`: signed currency change for a one-basis-point spread
  move.
- `price(cds, curves)`: returns all main outputs in `CdsPricingResult`.

### `CdsPricingResult`

`CdsPricingResult` stores the output from `CdsPricer.price()`.

Fields:

- `premium_leg`: currency value of the running spread payments. It is not
  flipped by protection side.
- `accrued_on_default`: currency value of expected accrued premium on default.
  It is not flipped by protection side.
- `protection_leg`: currency value of expected protection payments. It is not
  flipped by protection side.
- `par_spread`: raw decimal spread.
- `upfront`: raw decimal of notional.
- `present_value`: signed by `ProtectionSide`.
- `risky_pv01`: currency value of one full `1.0` running-spread unit. It is not
  flipped by protection side.
- `cs01`: signed by `ProtectionSide`.

For the same CDS terms, selling protection flips `present_value` and `cs01`.
The leg values, par spread, upfront, and risky PV01 stay the same.

### Risk Helpers

`risky_pv01(cds, curves, pricer=None)` calls `CdsPricer.risky_pv01()`. If no
pricer is passed, it creates a default `CdsPricer`.

`cds_cs01(cds, curves, pricer=None)` calls `CdsPricer.cs01()`. If no pricer is
passed, it creates a default `CdsPricer`.

`cs01` is an alias for `cds_cs01`.

Example:

```python
from dataclasses import dataclass
from decimal import Decimal
import math
from types import SimpleNamespace

from fuggers_py import Date
from fuggers_py.credit import Cds, CdsPricer, ProtectionSide, cds_cs01, risky_pv01


class FlatDiscountCurve:
    def __init__(self, reference_date: Date, rate: Decimal) -> None:
        self.reference_date = reference_date
        self.rate = rate
        self.spec = SimpleNamespace(day_count="ACT/365F")

    def discount_factor_at(self, tenor: float) -> Decimal:
        return Decimal(str(math.exp(-float(self.rate) * tenor)))


@dataclass(frozen=True, slots=True)
class FlatCreditCurve:
    reference_date: Date
    hazard_rate: Decimal

    def survival_probability(self, date: Date) -> Decimal:
        tenor = max(self.reference_date.days_between(date), 0) / 365.0
        return Decimal(str(math.exp(-float(self.hazard_rate) * tenor)))


@dataclass(frozen=True, slots=True)
class CurveSet:
    discount_curve: FlatDiscountCurve
    credit_curve: FlatCreditCurve


valuation_date = Date.from_ymd(2026, 1, 15)
curves = CurveSet(
    discount_curve=FlatDiscountCurve(valuation_date, Decimal("0.035")),
    credit_curve=FlatCreditCurve(valuation_date, Decimal("0.020")),
)

buy_cds = Cds(
    effective_date=valuation_date,
    maturity_date=valuation_date.add_years(5),
    running_spread=Decimal("0.0125"),
    notional=Decimal("10000000"),
    protection_side=ProtectionSide.BUY,
    recovery_rate=Decimal("0.40"),
)

pricer = CdsPricer(default_timing_fraction=Decimal("0.5"))
result = pricer.price(buy_cds, curves)

par_spread_bps = result.par_spread * Decimal("10000")
cs01_value = cds_cs01(buy_cds, curves, pricer=pricer)
risky_annuity_value = risky_pv01(buy_cds, curves, pricer=pricer)

assert result.cs01 == cs01_value
assert result.risky_pv01 == risky_annuity_value
assert result.premium_leg == buy_cds.running_spread * result.risky_pv01

print(par_spread_bps)
print(result.present_value)
print(result.cs01)
```

## Adjusted CDS Spread, Bond-CDS Basis, And Proxy Risk-Free Rate

These helpers use raw decimal rates and spreads. All inputs are converted to
`Decimal`.

### `adjusted_cds_spread` and `adjusted_cds_breakdown`

`adjusted_cds_spread()` removes explicit adjustments from a quoted CDS spread:

```text
adjusted spread = quoted spread - delivery option adjustment - FX adjustment - other adjustment
```

Use it when the quoted CDS spread includes items you want to strip out before
comparing it with a bond spread.

`adjusted_cds_breakdown()` returns the same calculation in an
`AdjustedCdsBreakdown` record with:

- `quoted_spread`
- `delivery_option_adjustment`
- `fx_adjustment`
- `other_adjustment`
- `adjusted_spread`

### `bond_cds_basis` and `bond_cds_basis_breakdown`

`bond_cds_basis()` compares a bond spread with an adjusted CDS spread:

```text
basis = bond spread - adjusted CDS spread
```

A positive value means the bond spread is wider than the adjusted CDS spread. A
negative value means the bond spread is tighter than the adjusted CDS spread.

`bond_cds_basis_breakdown()` returns the same calculation in a
`BondCdsBasisBreakdown` record with:

- `bond_spread`
- `quoted_cds_spread`
- `adjusted_cds_spread`
- `delivery_option_adjustment`
- `fx_adjustment`
- `other_cds_adjustment`
- `basis`

### `cds_adjusted_risk_free_rate` and `proxy_risk_free_breakdown`

`cds_adjusted_risk_free_rate()` starts with a bond yield, removes the adjusted
CDS spread, then removes explicit liquidity and funding adjustments:

```text
proxy risk-free rate = bond yield - adjusted CDS spread - liquidity adjustment - funding adjustment
```

Use it when a bond yield includes credit spread and other listed adjustments,
and you want a simple proxy for a risk-free rate.

`proxy_risk_free_breakdown()` returns the same calculation in a
`RiskFreeProxyBreakdown` record with:

- `bond_yield`
- `quoted_cds_spread`
- `adjusted_cds_spread`
- `liquidity_adjustment`
- `funding_adjustment`
- `proxy_risk_free_rate`

Example:

```python
from decimal import Decimal

from fuggers_py.credit import (
    adjusted_cds_breakdown,
    adjusted_cds_spread,
    bond_cds_basis,
    bond_cds_basis_breakdown,
    cds_adjusted_risk_free_rate,
    proxy_risk_free_breakdown,
)

adjusted = adjusted_cds_breakdown(
    quoted_spread=Decimal("0.0320"),
    delivery_option_adjustment=Decimal("0.0030"),
    fx_adjustment=Decimal("0.0020"),
    other_adjustment=Decimal("0.0010"),
)

assert adjusted.adjusted_spread == Decimal("0.0260")
assert adjusted_cds_spread(
    quoted_spread=Decimal("0.0320"),
    delivery_option_adjustment=Decimal("0.0030"),
    fx_adjustment=Decimal("0.0020"),
    other_adjustment=Decimal("0.0010"),
) == adjusted.adjusted_spread

basis = bond_cds_basis_breakdown(
    bond_spread=Decimal("0.0180"),
    cds_spread=Decimal("0.0150"),
    delivery_option_adjustment=Decimal("0.0010"),
    fx_adjustment=Decimal("0.0005"),
)

assert basis.adjusted_cds_spread == Decimal("0.0135")
assert basis.basis == Decimal("0.0045")
assert bond_cds_basis(
    bond_spread=Decimal("0.0180"),
    cds_spread=Decimal("0.0150"),
    delivery_option_adjustment=Decimal("0.0010"),
    fx_adjustment=Decimal("0.0005"),
) == basis.basis

proxy = proxy_risk_free_breakdown(
    bond_yield=Decimal("0.0550"),
    cds_spread=Decimal("0.0200"),
    delivery_option_adjustment=Decimal("0.0020"),
    fx_adjustment=Decimal("0.0010"),
    liquidity_adjustment=Decimal("0.0005"),
    funding_adjustment=Decimal("0.0003"),
)

assert proxy.adjusted_cds_spread == Decimal("0.0170")
assert proxy.proxy_risk_free_rate == Decimal("0.0372")
assert cds_adjusted_risk_free_rate(
    bond_yield=Decimal("0.0550"),
    cds_spread=Decimal("0.0200"),
    delivery_option_adjustment=Decimal("0.0020"),
    fx_adjustment=Decimal("0.0010"),
    liquidity_adjustment=Decimal("0.0005"),
    funding_adjustment=Decimal("0.0003"),
) == proxy.proxy_risk_free_rate
```

## Export Reference

| Export | What it represents | Main behavior |
| --- | --- | --- |
| `Cds` | Short name for `CreditDefaultSwap`. | Exact alias. |
| `CreditDefaultSwap` | One CDS contract. | Builds schedules and premium periods; stores notional, spread, side, recovery, upfront, schedule rules, and labels. |
| `CdsPremiumPeriod` | One premium accrual period. | Stores accrual start, accrual end, payment date, and year fraction. |
| `ProtectionSide` | Buy or sell protection direction. | Parses aliases, returns pricing sign, and returns the opposite side. |
| `CdsQuote` | Market quote for one CDS. | Normalizes quote fields and can return bid, ask, or mid values. |
| `CdsReferenceData` | Static CDS reference record. | Normalizes reference entity, tenor, seniority, restructuring clause, coupon, and recovery. |
| `CdsPricer` | CDS pricing calculator. | Resolves discount and credit curves, computes legs, par spread, upfront, PV, risky PV01, and CS01. |
| `CdsPricingResult` | CDS pricing output. | Stores legs, par spread, upfront, signed PV, risky PV01, and signed CS01. |
| `risky_pv01` | Convenience risk helper. | Calls `CdsPricer.risky_pv01()`. |
| `cds_cs01` | Convenience CS01 helper. | Calls `CdsPricer.cs01()`. |
| `cs01` | Short name for `cds_cs01`. | Exact alias. |
| `adjusted_cds_spread` | Adjusted CDS spread helper. | Returns quoted spread minus delivery, FX, and other adjustments. |
| `adjusted_cds_breakdown` | Adjusted CDS spread with detail. | Returns `AdjustedCdsBreakdown`. |
| `AdjustedCdsBreakdown` | Adjusted CDS spread output. | Stores quoted spread, adjustments, and adjusted spread. |
| `bond_cds_basis` | Bond spread versus adjusted CDS spread. | Returns `bond spread - adjusted CDS spread`. |
| `bond_cds_basis_breakdown` | Bond-CDS basis with detail. | Returns `BondCdsBasisBreakdown`. |
| `BondCdsBasisBreakdown` | Bond-CDS basis output. | Stores bond spread, quoted CDS spread, adjusted CDS spread, adjustments, and basis. |
| `cds_adjusted_risk_free_rate` | CDS-adjusted proxy risk-free rate. | Returns bond yield minus adjusted CDS spread, liquidity adjustment, and funding adjustment. |
| `proxy_risk_free_breakdown` | Proxy risk-free rate with detail. | Returns `RiskFreeProxyBreakdown`. |
| `RiskFreeProxyBreakdown` | Proxy risk-free rate output. | Stores bond yield, CDS spreads, liquidity adjustment, funding adjustment, and proxy rate. |

## Boundaries

- Bond instruments, bond spreads, and bond pricing live in `fuggers_py.bonds`.
- Curve objects live in `fuggers_py.curves`.
- Portfolio credit-quality aggregation lives in `fuggers_py.portfolio`.

```{eval-rst}
.. automodule:: fuggers_py.credit
   :members:
   :member-order: bysource
```
