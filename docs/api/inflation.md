# `fuggers_py.inflation`

`fuggers_py.inflation` is the public home for CPI history, reference CPI,
index ratios, inflation swaps, inflation swap pricing, and simple inflation
analytics.

Use one-layer imports from `fuggers_py.inflation`.

```python
from decimal import Decimal

from fuggers_py import Date, YearMonth
from fuggers_py.inflation import (
    InMemoryInflationFixingSource,
    InflationFixing,
    USD_CPI_U_NSA,
    reference_cpi,
)

fixings = InMemoryInflationFixingSource(
    [
        InflationFixing("CPURNSA", YearMonth(2026, 1), Decimal("320.000")),
        InflationFixing("CPURNSA", YearMonth(2026, 2), Decimal("321.000")),
    ]
)

value = reference_cpi(
    settlement_date=Date.from_ymd(2026, 4, 1),
    convention=USD_CPI_U_NSA,
    fixing_source=fixings,
)

print(value)  # Decimal("320.000")
```

## Core Rules

- CPI fixings are monthly index levels. They are not daily rates.
- CPI fixing months use `YearMonth`.
- Rates use raw decimal form unless this page says otherwise. `Decimal("0.025")`
  means 2.5%.
- Treasury auction coupon rates are different: `TreasuryAuctionedTipsRow`
  stores the Treasury percentage value. `1.625` means 1.625%, and
  `tips_bond_from_treasury_auction_row()` divides it by `100` when it builds a
  `TipsBond`.
- Reference CPI turns monthly CPI fixings into a daily value.
- An index ratio is `settlement reference CPI / base-date reference CPI`.
- Swap PV signs follow the swap side. A pay-fixed swap has a negative fixed-leg
  sign and a positive inflation-leg sign. A receive-fixed swap is the opposite.
- Standard coupon inflation swaps currently support USD CPI-U / `CPURNSA` only.
- Parser functions take text or already parsed payloads. Loader functions read a
  local file and then call the matching parser.

## Conventions

### `InflationInterpolation`

`InflationInterpolation` names how monthly CPI fixings become daily reference
CPI values.

- `MONTHLY` uses one monthly CPI fixing for the whole settlement month.
- `LINEAR` uses two monthly CPI fixings and moves from the first value toward
  the second value day by day.
- `FLAT` is an enum value, but `reference_cpi()` does not support it yet. Passing
  it raises `UnsupportedInflationInterpolation`.

### `InflationConvention`

`InflationConvention` describes an inflation index. It tells the library which
CPI source to use, which currency the index belongs to, how many months of lag
to apply, and which interpolation rule to use.

The constructor cleans common inputs:

- `name` is stripped.
- `family` and `index_source` are uppercased.
- `observation_lag_months` is converted to `int`.
- `aliases` are stripped, uppercased, deduplicated, and kept in order.
- A negative observation lag raises `InvalidObservationLag`.

Useful method:

- `lookup_names()` returns the source name and aliases that fixing lookup should
  try, in order.

`InflationIndexDefinition` is an alias for `InflationConvention`.

```python
from fuggers_py.inflation import USD_CPI_U_NSA

print(USD_CPI_U_NSA.name)                    # "USD CPI-U NSA"
print(USD_CPI_U_NSA.index_source)            # "CPURNSA"
print(USD_CPI_U_NSA.observation_lag_months)  # 3
print(USD_CPI_U_NSA.lookup_names())
# ("CPURNSA", "CPI-U", "CPI-U NSA", "US CPI-U", "US CPI-U NSA")
```

```python
from fuggers_py import Currency
from fuggers_py.inflation import InflationConvention, InflationInterpolation

custom = InflationConvention(
    name="Example CPI",
    family="example_cpi",
    currency=Currency.USD,
    index_source="example",
    observation_lag_months="2",
    interpolation_method=InflationInterpolation.MONTHLY,
    aliases=(" example-alt ", "EXAMPLE-ALT"),
)

print(custom.family)                  # "EXAMPLE_CPI"
print(custom.index_source)            # "EXAMPLE"
print(custom.observation_lag_months)  # 2
print(custom.lookup_names())          # ("EXAMPLE", "EXAMPLE-ALT")
```

### `USD_CPI_U_NSA`

`USD_CPI_U_NSA` is the built-in convention for US CPI-U, not seasonally
adjusted. It uses:

- currency `USD`
- source name `CPURNSA`
- three-month observation lag
- linear daily interpolation
- aliases such as `CPI-U` and `US CPI-U NSA`

Use it when pricing or referencing US CPI-linked instruments.

### Errors

Inflation errors inherit from `InflationError`.

- `InflationError` is the base class for inflation-specific failures.
- `InvalidObservationLag` is raised when a convention has a negative lag. It
  stores `observation_lag_months`.
- `MissingInflationFixing` is raised when reference CPI needs a monthly CPI
  fixing that the source cannot return. It stores `index_name`, `requested_date`,
  and `observation_months`.
- `UnsupportedInflationInterpolation` is raised when `reference_cpi()` receives
  an interpolation method it does not implement. It stores
  `interpolation_method`.

```python
from dataclasses import replace

from fuggers_py import Date
from fuggers_py.inflation import (
    InMemoryInflationFixingSource,
    InflationInterpolation,
    InvalidObservationLag,
    MissingInflationFixing,
    UnsupportedInflationInterpolation,
    USD_CPI_U_NSA,
    reference_cpi,
)

empty_source = InMemoryInflationFixingSource()

try:
    reference_cpi(Date.from_ymd(2026, 4, 1), USD_CPI_U_NSA, empty_source)
except MissingInflationFixing as error:
    print(error.index_name)            # "CPURNSA"
    print(error.observation_months)    # missing lagged months

try:
    replace(USD_CPI_U_NSA, observation_lag_months=-1)
except InvalidObservationLag as error:
    print(error.observation_lag_months)  # -1

flat_convention = replace(
    USD_CPI_U_NSA,
    interpolation_method=InflationInterpolation.FLAT,
)

try:
    reference_cpi(Date.from_ymd(2026, 4, 1), flat_convention, empty_source)
except UnsupportedInflationInterpolation as error:
    print(error.interpolation_method)  # FLAT
```

## CPI Fixings And Sources

### `InflationFixing`

`InflationFixing` is one published monthly CPI value for one index.

Fields:

- `index_name`: source name such as `CPURNSA`
- `observation_month`: the month the CPI value belongs to
- `value`: the CPI index level

The constructor cleans inputs:

- `index_name` is stripped and uppercased.
- `observation_month` is parsed into `YearMonth`.
- `value` is parsed into `Decimal`.

```python
from fuggers_py.inflation import InflationFixing

fixing = InflationFixing(
    index_name=" cpurnsa ",
    observation_month="2026-01",
    value="320.000",
)

print(fixing.index_name)         # "CPURNSA"
print(fixing.observation_month)  # 2026-01
print(fixing.value)              # Decimal("320.000")
```

### `InMemoryInflationFixingSource`

`InMemoryInflationFixingSource` stores CPI fixings in memory. Use it for
examples, tests, and small local datasets.

The source stores fixings by `(index_name, observation_month)`. Later fixings
with the same key replace earlier ones.

Useful methods and fields:

- `fixings` is the stored dictionary.
- `add_inflation_fixing(fixing)` stores a fixing and returns the source, so calls
  can be chained.
- `get_inflation_fixing(index_name, observation_month)` returns the matching
  `InflationFixing` or `None`. It strips and uppercases `index_name` and parses
  `observation_month`.

```python
from fuggers_py.inflation import InMemoryInflationFixingSource, InflationFixing

source = InMemoryInflationFixingSource()
source.add_inflation_fixing(InflationFixing("CPURNSA", "2026-01", "320.000"))
source.add_inflation_fixing(InflationFixing("CPURNSA", "2026-02", "321.000"))

jan = source.get_inflation_fixing(" cpurnsa ", "2026-01")
print(jan.value)  # Decimal("320.000")
```

### CPI parsers and loaders

Use parsers when you already have text or decoded JSON. Use loaders when the
data is in a local file.

- `parse_monthly_cpi_fixings_csv(text, index_name="CPURNSA")` parses normalized
  CSV rows.
- `parse_monthly_cpi_fixings_json(payload, index_name="CPURNSA")` parses
  normalized JSON rows. The payload can be a JSON string, bytes, a list of row
  dicts, or a dict with rows under `data`, `observations`, or `fixings`.
- `load_monthly_cpi_fixings_csv(path, index_name="CPURNSA")` reads a CSV file and
  calls `parse_monthly_cpi_fixings_csv()`.
- `load_monthly_cpi_fixings_json(path, index_name="CPURNSA")` reads a JSON file
  and calls `parse_monthly_cpi_fixings_json()`.
- `parse_bls_cpi_json(payload, index_name="CPURNSA")` parses BLS-style CPI JSON.
  It skips annual `M13` rows and keeps monthly `M01` to `M12` rows.
- `parse_fred_cpi_csv(text, index_name="CPURNSA")` parses a FRED monthly CSV. It
  uses the date column and the first non-date value column.
- `treasury_cpi_source_from_fixings(fixings)` wraps parsed fixings in an
  `InMemoryInflationFixingSource`.

Normalized CPI rows can use these month fields:

- `observation_month`
- `month`
- `date`
- `reference_month`

Normalized CPI rows can use these value fields:

- `value`
- `cpi`
- `reference_cpi`
- `index_level`
- `cpurnsa`

```python
from pathlib import Path

from fuggers_py.inflation import (
    load_monthly_cpi_fixings_csv,
    load_monthly_cpi_fixings_json,
    parse_fred_cpi_csv,
    parse_monthly_cpi_fixings_csv,
    parse_monthly_cpi_fixings_json,
    treasury_cpi_source_from_fixings,
)

csv_text = """
observation_month,value
2026-01,320.000
2026-02,321.000
"""

fixings = parse_monthly_cpi_fixings_csv(csv_text)
source = treasury_cpi_source_from_fixings(fixings)
print(source.get_inflation_fixing("CPURNSA", "2026-02").value)

fred_text = """
DATE,CPURNSA
2026-01-01,320.000
2026-02-01,321.000
"""

fred_fixings = parse_fred_cpi_csv(fred_text)
print(fred_fixings[0].observation_month)

path = Path("/tmp/fuggers_py_cpi_fixings.csv")
path.write_text(csv_text)
loaded = load_monthly_cpi_fixings_csv(path)
print(len(loaded))  # 2

json_payload = {
    "fixings": [
        {"observation_month": "2026-01", "value": "320.000"},
        {"observation_month": "2026-02", "value": "321.000"},
    ]
}

json_fixings = parse_monthly_cpi_fixings_json(json_payload)
print(json_fixings[1].value)  # Decimal("321.000")

json_path = Path("/tmp/fuggers_py_cpi_fixings.json")
json_path.write_text('{"fixings": [{"observation_month": "2026-01", "value": "320.000"}]}')
json_loaded = load_monthly_cpi_fixings_json(json_path)
print(len(json_loaded))  # 1
```

```python
from fuggers_py.inflation import parse_bls_cpi_json

payload = {
    "Results": {
        "series": [
            {
                "data": [
                    {"year": "2026", "period": "M02", "value": "321.000"},
                    {"year": "2026", "period": "M13", "value": "ignored"},
                ]
            }
        ]
    }
}

fixings = parse_bls_cpi_json(payload)
print(fixings[0].observation_month)  # 2026-02
```

## Reference CPI And Index Ratios

### `reference_cpi`

`reference_cpi(settlement_date, convention, fixing_source)` returns the CPI
value used on a daily settlement date.

The function first applies the convention's observation lag. With the built-in
US CPI convention, an April 2026 settlement uses January and February 2026 CPI
because the lag is three months.

Behavior by interpolation method:

- `MONTHLY`: needs one lagged monthly fixing and returns that value for the
  whole settlement month.
- `LINEAR`: needs two lagged monthly fixings. On day 1 it returns the first
  fixing. After day 1 it moves from the first fixing toward the second fixing
  using `(day of month - 1) / days in settlement month`.
- Other methods raise `UnsupportedInflationInterpolation`.

The fixing source can be an object with `get_inflation_fixing(index_name,
observation_month)`. It can also be a market data snapshot that exposes an
`inflation_fixing_source`.

```python
from fuggers_py import Date
from fuggers_py.inflation import (
    InMemoryInflationFixingSource,
    InflationFixing,
    USD_CPI_U_NSA,
    reference_cpi,
)

source = InMemoryInflationFixingSource(
    [
        InflationFixing("CPURNSA", "2026-01", "320.000"),
        InflationFixing("CPURNSA", "2026-02", "321.000"),
    ]
)

start_value = reference_cpi(Date.from_ymd(2026, 4, 1), USD_CPI_U_NSA, source)
mid_month_value = reference_cpi(Date.from_ymd(2026, 4, 16), USD_CPI_U_NSA, source)

print(start_value)      # Decimal("320.000")
print(mid_month_value)  # moves toward Decimal("321.000")
```

### `reference_index_ratio`

`reference_index_ratio(settlement_date, base_date, convention, fixing_source)`
returns:

```text
reference_cpi(settlement_date) / reference_cpi(base_date)
```

Use it when you need the inflation uplift from one date to another.

```python
from fuggers_py import Date
from fuggers_py.inflation import (
    InMemoryInflationFixingSource,
    InflationFixing,
    USD_CPI_U_NSA,
    reference_index_ratio,
)

source = InMemoryInflationFixingSource(
    [
        InflationFixing("CPURNSA", "2026-01", "320.000"),
        InflationFixing("CPURNSA", "2026-02", "321.000"),
        InflationFixing("CPURNSA", "2026-03", "322.000"),
        InflationFixing("CPURNSA", "2026-04", "323.000"),
    ]
)

ratio = reference_index_ratio(
    settlement_date=Date.from_ymd(2026, 6, 1),
    base_date=Date.from_ymd(2026, 4, 1),
    convention=USD_CPI_U_NSA,
    fixing_source=source,
)

print(ratio)
```

### `InflationProjection`

`InflationProjection` is a small interface for objects that can forecast
reference CPI directly.

The public protocol method is:

- `reference_cpi(date, convention) -> Decimal`

`InflationSwapPricer.reference_cpi()` also accepts projection objects with
`projected_reference_cpi(date)`, `get_reference_cpi(date, convention)`, or
`get_inflation_fixing(index_name, observation_month)`. This lets the pricer work
with both forecast curves and fixing sources.

```python
from decimal import Decimal

from fuggers_py.inflation import USD_CPI_U_NSA


class FlatCpiProjection:
    def reference_cpi(self, date, convention):
        return Decimal("325.000")


projection = FlatCpiProjection()
print(projection.reference_cpi(None, USD_CPI_U_NSA))
```

## Treasury TIPS Reference Data

### `TreasuryAuctionedTipsRow`

`TreasuryAuctionedTipsRow` stores the Treasury auction fields needed to build a
TIPS bond.

Fields:

- `cusip`
- `security_type`
- `security_term`
- `issue_date`
- `dated_date`
- `maturity_date`
- `coupon_rate`
- `original_issue_date`
- `ref_cpi_on_issue_date`
- `ref_cpi_on_dated_date`
- `original_security_term`

Constructor behavior:

- `cusip` is stripped and uppercased.
- `security_type`, `security_term`, and `original_security_term` are stripped.
- `coupon_rate` is parsed into `Decimal`.
- `coupon_rate` is a Treasury percentage value. Pass `1.625` for 1.625%, not
  `0.01625`.

### Treasury parsers and loaders

- `parse_treasury_auctioned_tips_csv(text)` parses Treasury auction rows from
  CSV text and keeps only TIPS rows.
- `parse_treasury_auctioned_tips_json(payload)` parses Treasury auction rows
  from JSON text, bytes, a list of rows, or a dict with rows under `data`,
  `securities`, or `auctioned`.
- `load_treasury_auctioned_tips_csv(path)` reads a CSV file and calls
  `parse_treasury_auctioned_tips_csv()`.
- `load_treasury_auctioned_tips_json(path)` reads a JSON file and calls
  `parse_treasury_auctioned_tips_json()`.

A row is treated as TIPS when it contains a reference CPI field or text such as
`TIPS`, `inflation protected`, or `inflation-protected`.

### `tips_bond_from_treasury_auction_row`

`tips_bond_from_treasury_auction_row(row, fixing_source=None, identifiers=None)`
converts a parsed Treasury row into `fuggers_py.bonds.TipsBond`.

Important behavior:

- `dated_date` is required. If it is missing, the function raises `ValueError`.
- The function uses `USD_CPI_U_NSA`.
- The row coupon rate is divided by `100` before it is passed to `TipsBond`.
- If `identifiers` is not supplied, the function builds a preview bond and then
  replaces its CUSIP with the Treasury row CUSIP.

```python
from pathlib import Path

from fuggers_py.inflation import (
    load_treasury_auctioned_tips_csv,
    load_treasury_auctioned_tips_json,
    parse_treasury_auctioned_tips_csv,
    parse_treasury_auctioned_tips_json,
    tips_bond_from_treasury_auction_row,
)

csv_text = """
CUSIP,SecurityType,SecurityTerm,IssueDate,DatedDate,MaturityDate,InterestRate,RefCPIOnDatedDate
91282CGK1,TIPS,10-Year,2026-01-15,2026-01-15,2036-01-15,1.625,320.000
"""

rows = parse_treasury_auctioned_tips_csv(csv_text)
row = rows[0]

print(row.cusip)        # "91282CGK1"
print(row.coupon_rate)  # Decimal("1.625"), meaning 1.625%

bond = tips_bond_from_treasury_auction_row(row)
print(bond.maturity_date())

csv_path = Path("/tmp/fuggers_py_tips_rows.csv")
csv_path.write_text(csv_text)
csv_loaded = load_treasury_auctioned_tips_csv(csv_path)
print(csv_loaded[0].maturity_date)

json_rows = {
    "data": [
        {
            "cusip": "91282CGK1",
            "securityType": "TIPS",
            "securityTerm": "10-Year",
            "issueDate": "2026-01-15",
            "datedDate": "2026-01-15",
            "maturityDate": "2036-01-15",
            "interestRate": "1.625",
            "refCpiOnDatedDate": "320.000",
        }
    ]
}

json_parsed = parse_treasury_auctioned_tips_json(json_rows)
print(json_parsed[0].cusip)

json_path = Path("/tmp/fuggers_py_tips_rows.json")
json_path.write_text(
    '[{"cusip": "91282CGK1", "securityType": "TIPS", "securityTerm": "10-Year", '
    '"issueDate": "2026-01-15", "datedDate": "2026-01-15", '
    '"maturityDate": "2036-01-15", "interestRate": "1.625", '
    '"refCpiOnDatedDate": "320.000"}]'
)
json_loaded = load_treasury_auctioned_tips_json(json_path)
print(json_loaded[0].coupon_rate)
```

## Inflation Swaps

### Shared swap rules

Inflation swaps use two legs:

- The fixed leg pays the fixed swap rate.
- The inflation leg pays the realized inflation change.

`pay_receive` names the fixed leg side:

- `PAY` means pay fixed and receive inflation.
- `RECEIVE` means receive fixed and pay inflation.

The helper methods make that sign rule visible:

- `fixed_leg_sign()` returns the sign for fixed-leg PV.
- `inflation_leg_sign()` returns the opposite sign for inflation-leg PV.

### `ZeroCouponInflationSwap`

`ZeroCouponInflationSwap` represents one fixed payment and one inflation payment
at maturity.

Constructor behavior:

- `notional` and `fixed_rate` are parsed into `Decimal`.
- `pay_receive`, `currency`, `payment_calendar`,
  `business_day_convention`, and `instrument_id` are parsed from strings when
  needed.
- If `effective_date` is missing, it is set to the payment calendar settlement
  date two business days after `trade_date`.
- `inflation_convention` is required.
- `maturity_date` must be after `effective_date`.
- `notional` must be positive.
- `currency` must match `inflation_convention.currency`.

Useful methods and properties:

- `new(...)` is the keyword-only constructor helper.
- `payment_date()` adjusts `maturity_date` by the payment calendar and business
  day rule.
- `kind` returns `"inflation.swap.zero_coupon"`.
- `fixed_leg_sign()` returns the fixed-leg sign.
- `inflation_leg_sign()` returns the inflation-leg sign.
- `fixed_leg_year_fraction()` returns `Decimal(1)`.
- `index_initial_date()` returns `effective_date`.
- `index_final_date()` returns `maturity_date`.

```python
from decimal import Decimal

from fuggers_py import Date
from fuggers_py.inflation import USD_CPI_U_NSA, ZeroCouponInflationSwap

swap = ZeroCouponInflationSwap.new(
    trade_date=Date.from_ymd(2026, 1, 2),
    effective_date=Date.from_ymd(2026, 1, 6),
    maturity_date=Date.from_ymd(2031, 1, 6),
    notional=Decimal("1000000"),
    fixed_rate=Decimal("0.025"),
    pay_receive="PAY",
    inflation_convention=USD_CPI_U_NSA,
)

print(swap.kind)
print(swap.payment_date())
print(swap.fixed_leg_sign())
print(swap.inflation_leg_sign())
```

### `StandardCouponInflationSwap`

`StandardCouponInflationSwap` represents a coupon inflation swap. It has a fixed
coupon period schedule and an inflation period schedule.

Constructor behavior:

- `notional` and `fixed_rate` are parsed into `Decimal`.
- `pay_receive`, `currency`, `fixed_day_count_convention`, and `instrument_id`
  are parsed from strings when needed.
- If `effective_date` is missing, it is set to the schedule calendar settlement
  date two business days after `trade_date`.
- If `normalize_effective_date_to_reference_month_start=True`, the effective
  date is moved to the adjusted first day of its month.
- If `inflation_schedule` is missing, it uses the fixed `schedule`.
- Fixed and inflation period overrides are stored as tuples.
- `inflation_convention` is required.
- `maturity_date` must be after `effective_date`.
- `notional` must be positive.
- `currency` must match `inflation_convention.currency`.
- The first release supports only USD CPI-U / `CPURNSA`.
- Fixed and inflation schedules must have the same number of periods.
- Fixed and inflation period start dates, end dates, and payment dates must
  match.
- The schedule must start on `effective_date` and end on `maturity_date`.

Useful methods and properties:

- `new(...)` is the keyword-only constructor helper.
- `fixed_leg_sign()` returns the fixed-leg sign.
- `inflation_leg_sign()` returns the inflation-leg sign.
- `fixed_periods()` returns fixed accrual periods. If fixed periods were passed
  to `new(..., fixed_periods=...)`, it returns those.
- `inflation_periods()` returns inflation accrual periods. If inflation periods
  were passed to `new(..., inflation_periods=...)`, it returns those.
- `payment_dates()` returns the fixed period payment dates.
- `kind` returns `"inflation.swap.standard_coupon"`.

```python
from decimal import Decimal

from fuggers_py import Date
from fuggers_py.inflation import USD_CPI_U_NSA, StandardCouponInflationSwap

swap = StandardCouponInflationSwap.new(
    trade_date=Date.from_ymd(2026, 1, 2),
    effective_date=Date.from_ymd(2026, 1, 6),
    maturity_date=Date.from_ymd(2027, 1, 6),
    notional=Decimal("1000000"),
    fixed_rate=Decimal("0.025"),
    pay_receive="RECEIVE",
    inflation_convention=USD_CPI_U_NSA,
    normalize_effective_date_to_reference_month_start=False,
)

print(swap.kind)
print(swap.payment_dates())
print(swap.fixed_periods()[0].year_fraction)
print(swap.inflation_periods()[0].start_date)
```

## Inflation Swap Pricing

### Curve and projection inputs

`InflationSwapPricer` can price with explicit curves or with a curves bundle.

A discount curve must provide:

- `reference_date`
- `spec.day_count`
- `discount_factor_at(tenor)`

The pricer turns a payment date into a tenor using the curve reference date and
day count, then asks the curve for the discount factor.

An inflation projection can provide one of these:

- `projected_reference_cpi(date)`
- `reference_cpi(date, convention)`
- `get_reference_cpi(date, convention)`
- `get_inflation_fixing(index_name, observation_month)`

If the projection only provides monthly fixings, the pricer calls
`reference_cpi()` to turn those fixings into daily reference CPI.

### `InflationSwapPricer`

`InflationSwapPricer` prices zero-coupon and standard coupon inflation swaps.

Useful methods:

- `fixed_leg_pv(swap, curves=None, discount_curve=None)` returns fixed-leg PV.
- `inflation_leg_pv(swap, curves=None, discount_curve=None,
  inflation_projection=None)` returns inflation-leg PV.
- `pv(swap, curves=None, discount_curve=None, inflation_projection=None)` returns
  fixed-leg PV plus inflation-leg PV.
- `par_fixed_rate(swap, curves=None, discount_curve=None,
  inflation_projection=None)` returns the fixed rate that makes the swap PV zero.
- `pv01(swap, curves=None, discount_curve=None, bump=Decimal("0.0001"))` returns
  the signed value of a one-basis-point fixed-rate bump. A basis point is
  `0.0001`.
- `fixed_leg_annuity(swap, curves=None, discount_curve=None)` returns the fixed
  leg's discounted notional times year fraction.
- `reference_cpi(swap, date, curves=None, inflation_projection=None)` returns
  the projection's reference CPI for a date.
- `price(swap, curves=None, discount_curve=None, inflation_projection=None)`
  returns a pricing result record.

```python
from decimal import Decimal

from fuggers_py import Date
from fuggers_py.inflation import (
    InflationSwapPricer,
    USD_CPI_U_NSA,
    ZeroCouponInflationSwap,
)


class FlatDiscountCurve:
    reference_date = Date.from_ymd(2026, 1, 2)
    spec = type("Spec", (), {"day_count": "ACT/365F"})()

    def discount_factor_at(self, tenor):
        return Decimal("0.950000")


class SimpleCpiProjection:
    def reference_cpi(self, date, convention):
        if date.year() < 2031:
            return Decimal("320.000")
        return Decimal("360.000")


swap = ZeroCouponInflationSwap.new(
    trade_date=Date.from_ymd(2026, 1, 2),
    effective_date=Date.from_ymd(2026, 1, 6),
    maturity_date=Date.from_ymd(2031, 1, 6),
    notional=Decimal("1000000"),
    fixed_rate=Decimal("0.025"),
    pay_receive="PAY",
    inflation_convention=USD_CPI_U_NSA,
)

pricer = InflationSwapPricer()
discount_curve = FlatDiscountCurve()
projection = SimpleCpiProjection()

print(pricer.fixed_leg_annuity(swap, discount_curve=discount_curve))
print(pricer.fixed_leg_pv(swap, discount_curve=discount_curve))
print(pricer.inflation_leg_pv(swap, discount_curve=discount_curve, inflation_projection=projection))
print(pricer.pv(swap, discount_curve=discount_curve, inflation_projection=projection))
print(pricer.par_fixed_rate(swap, discount_curve=discount_curve, inflation_projection=projection))
print(pricer.pv01(swap, discount_curve=discount_curve))
print(pricer.reference_cpi(swap, swap.index_final_date(), inflation_projection=projection))

result = pricer.price(swap, discount_curve=discount_curve, inflation_projection=projection)
print(result.present_value)
print(result.par_fixed_rate)
```

### `ZeroCouponInflationSwapPricingResult`

`ZeroCouponInflationSwapPricingResult` is returned by `price()` for a
zero-coupon inflation swap.

Fields:

- `par_fixed_rate`: raw decimal fixed rate that makes PV zero
- `present_value`: fixed-leg PV plus inflation-leg PV
- `fixed_leg_pv`
- `inflation_leg_pv`
- `pv01`: signed value of a one-basis-point fixed-rate bump
- `index_initial`: starting reference CPI
- `index_final`: final reference CPI
- `payment_date`
- `discount_factor`
- `fixed_leg_annuity`

```python
result = pricer.price(swap, discount_curve=discount_curve, inflation_projection=projection)

print(result.index_initial)
print(result.index_final)
print(result.discount_factor)
print(result.present_value)
```

### `StandardCouponInflationSwapPeriodPricing`

`StandardCouponInflationSwapPeriodPricing` stores one priced coupon period.

Fields:

- `start_date`
- `end_date`
- `payment_date`
- `year_fraction`
- `index_initial`
- `index_final`
- `inflation_rate`: `(index_final / index_initial) - 1`
- `fixed_cashflow`
- `inflation_cashflow`
- `discount_factor`
- `fixed_leg_pv`
- `inflation_leg_pv`

The numeric fields are parsed into `Decimal`.

### `StandardCouponInflationSwapPricingResult`

`StandardCouponInflationSwapPricingResult` is returned by `price()` for a
standard coupon inflation swap.

Fields:

- `par_fixed_rate`: raw decimal fixed rate that makes PV zero
- `present_value`: fixed-leg PV plus inflation-leg PV
- `fixed_leg_pv`
- `inflation_leg_pv`
- `pv01`: signed value of a one-basis-point fixed-rate bump
- `fixed_leg_annuity`
- `periods`: tuple of `StandardCouponInflationSwapPeriodPricing`

Numeric fields are parsed into `Decimal`, and `periods` is stored as a tuple.

```python
from decimal import Decimal

from fuggers_py import Date
from fuggers_py.inflation import (
    InflationSwapPricer,
    StandardCouponInflationSwap,
    USD_CPI_U_NSA,
)


class FlatDiscountCurve:
    reference_date = Date.from_ymd(2026, 1, 2)
    spec = type("Spec", (), {"day_count": "ACT/365F"})()

    def discount_factor_at(self, tenor):
        return Decimal("0.980000")


class SimpleCpiProjection:
    def reference_cpi(self, date, convention):
        if date.year() == 2026:
            return Decimal("320.000")
        return Decimal("328.000")


standard_swap = StandardCouponInflationSwap.new(
    trade_date=Date.from_ymd(2026, 1, 2),
    effective_date=Date.from_ymd(2026, 1, 6),
    maturity_date=Date.from_ymd(2027, 1, 6),
    notional=Decimal("1000000"),
    fixed_rate=Decimal("0.025"),
    pay_receive="PAY",
    inflation_convention=USD_CPI_U_NSA,
    normalize_effective_date_to_reference_month_start=False,
)

standard_result = InflationSwapPricer().price(
    standard_swap,
    discount_curve=FlatDiscountCurve(),
    inflation_projection=SimpleCpiProjection(),
)

print(standard_result.present_value)
for period in standard_result.periods:
    print(period.start_date, period.end_date, period.inflation_rate)
```

## Inflation Analytics

Analytics helpers compare nominal yields, real yields, and inflation swap rates.
All rates are raw decimals.

### `breakeven_inflation_rate`

`breakeven_inflation_rate(nominal_yield=..., real_yield=..., compounding=...)`
returns the inflation rate implied by a nominal yield and a real yield.

- With continuous compounding, it returns `nominal_yield - real_yield`.
- With other compounding, it returns
  `(1 + nominal_yield) / (1 + real_yield) - 1`.
- Nominal and real yields must be greater than `-1`.

### `nominal_real_yield_basis`

`nominal_real_yield_basis(nominal_yield=..., real_yield=..., compounding=...)`
returns the nominal-real basis.

- With continuous compounding, it returns `nominal_yield - real_yield`.
- With other compounding, it calls `breakeven_inflation_rate()`.

### `nominal_real_yield_spread`

`nominal_real_yield_spread(...)` is an alias for
`nominal_real_yield_basis(...)`.

### `linker_swap_parity_check`

`linker_swap_parity_check(nominal_yield=..., real_yield=...,
inflation_swap_rate=..., compounding=...)` compares a linker breakeven with an
inflation swap rate.

It returns `LinkerSwapParityCheck`.

### `LinkerSwapParityCheck`

`LinkerSwapParityCheck` stores:

- `nominal_yield`
- `real_yield`
- `linker_breakeven`
- `swap_breakeven`
- `parity_gap`

`parity_gap` is `linker_breakeven - swap_breakeven`. Numeric fields are parsed
into `Decimal`.

```python
from decimal import Decimal

from fuggers_py import Compounding
from fuggers_py.inflation import (
    breakeven_inflation_rate,
    linker_swap_parity_check,
    nominal_real_yield_basis,
    nominal_real_yield_spread,
)

breakeven = breakeven_inflation_rate(
    nominal_yield=Decimal("0.045"),
    real_yield=Decimal("0.018"),
    compounding=Compounding.ANNUAL,
)

basis = nominal_real_yield_basis(
    nominal_yield=Decimal("0.045"),
    real_yield=Decimal("0.018"),
)

spread = nominal_real_yield_spread(
    nominal_yield=Decimal("0.045"),
    real_yield=Decimal("0.018"),
)

check = linker_swap_parity_check(
    nominal_yield=Decimal("0.045"),
    real_yield=Decimal("0.018"),
    inflation_swap_rate=Decimal("0.026"),
)

print(breakeven)
print(basis)
print(spread)
print(check.parity_gap)
```

## Boundaries

- TIPS instruments and TIPS bond pricing live in `fuggers_py.bonds`.
- Nominal and real curve objects live in `fuggers_py.curves`.
- Rates instruments live in `fuggers_py.rates`.
- Portfolio inflation exposure is aggregated in `fuggers_py.portfolio`.

## Export Reference

```{eval-rst}
.. automodule:: fuggers_py.inflation
   :members:
   :member-order: bysource
```
