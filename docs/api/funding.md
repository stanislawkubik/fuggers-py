# `fuggers_py.funding`

Public home for repo trades, repo quotes, haircut quotes, repo reference records,
and funding analytics.

Use one-layer imports from `fuggers_py.funding` for funding objects and funding
functions:

```python
from fuggers_py.funding import RepoTrade, repo_net_carry
```

`Date`, `Currency`, and other shared core values come from `fuggers_py`.

## What This Package Owns

`funding` owns:

- repo trades: `RepoTrade`
- repo and haircut quotes: `RepoQuote` and `HaircutQuote`
- static repo reference records: `RepoReferenceData`
- repo carry and financing helpers
- implied repo and futures invoice helpers
- haircut, all-in funding, and specialness helpers

Repo curves do not live here. Curve objects live under `fuggers_py.curves`.
Bond futures contracts and conversion factors live under `fuggers_py.rates`.
Bond collateral instruments live under `fuggers_py.bonds`.

## Conventions

- Rates are raw decimals. `0.045` means 4.5%.
- Haircuts are raw decimals. `0.02` means 2%.
- Currency cash amounts are plain currency units. `1000000` means one million.
- Bond and futures prices are percent-of-par values. `99.5` means 99.5 per
  100 face amount.
- Accrued interest and coupon income in implied repo helpers are also
  percent-of-par values. `1.25` means 1.25 per 100 face amount, not 1.25 cash
  units.
- `face_amount` is a currency amount.
- Year fractions are raw decimals. `0.25` means one quarter of a year.
- Repo trade dates are `Date` values.
- Positive financing cost means a cost paid by the repo cash borrower.
- Positive net carry means collateral income is larger than financing costs.
- Positive specialness spread means the specific collateral repo rate is below
  the general collateral repo rate.

## Public Exports

| Export | What it is |
| --- | --- |
| `RepoTrade` | One repo trade with dates, rate, collateral price, haircut, and size. |
| `RepoQuote` | One market quote for a repo rate and optional haircut. |
| `HaircutQuote` | One market quote for a financing haircut. |
| `RepoReferenceData` | Static reference data for a repo instrument or repo market point. |
| `repo_financing_cost` | Repo interest paid over the trade period. |
| `repo_net_carry` | Collateral income minus repo and haircut funding costs. |
| `repo_carry_return` | Net carry divided by cash lent. |
| `implied_repo_rate` | Repo rate implied by buying a bond and delivering it into a future. |
| `implied_repo_rate_from_trade` | Same implied repo calculation, using dates and spot price from a `RepoTrade`. |
| `futures_invoice_amount` | Cash amount paid at futures delivery. |
| `haircut_amount` | Collateral value held back by a haircut. |
| `financed_cash` | Cash lent after the haircut. |
| `haircut_financing_cost` | Cost of funding the haircut amount. |
| `haircut_drag` | Extra cost of funding the haircut at a different rate than the repo rate. |
| `all_in_financing_cost` | Repo cost on financed cash plus haircut funding cost. |
| `specialness_spread` | General collateral rate minus specific collateral rate. |
| `specialness_value` | Currency value of the specialness spread. |
| `is_special` | `True` when the specific collateral rate is below the general collateral rate. |

## `RepoTrade`

`RepoTrade` represents one repo trade. A repo trade lends cash against
collateral. The collateral is valued from a bond-style price, and the cash lent
is reduced by any haircut.

Use `RepoTrade` when you want one object that can answer: how much cash is lent,
how much collateral is behind the loan, how much interest is due, and what cash
is due at repurchase.

### Construction Behavior

`RepoTrade` stores:

- `start_date` and `end_date`
- `rate`
- `collateral_price`
- `haircut`
- either `notional` or `cash_amount`
- `currency`
- `day_count_convention`
- optional `collateral_instrument_id`

The constructor normalizes several inputs:

- Decimal-like inputs may be `Decimal`, `int`, `float`, or `str`; they are stored
  as `Decimal`.
- `currency` may be a `Currency` value or a currency string such as `"usd"`.
- `collateral_instrument_id` may be a string; whitespace is stripped.
- `day_count_convention` may be a day-count value or a supported string alias.
  Supported aliases include `ACT360`, `ACT_360`, `ACT365F`,
  `ACT_365_FIXED`, `ACT365L`, `ACT_365_LEAP`, `30E_360`, `30_360_E`, and
  `30_360_US`.

The constructor validates the trade:

- `end_date` must be after `start_date`.
- `haircut` must be at least `0` and below `1`.
- At least one of `notional` or `cash_amount` is required.
- `notional`, when provided, must be positive.
- `cash_amount`, when provided, must be positive.

### Methods

`day_count()` returns the day-count object used by the trade.

`year_fraction()` returns the time between `start_date` and `end_date` as a
decimal part of a year.

`collateral_market_value()` returns the market value of the collateral:

- if `notional` is set: `notional * collateral_price / 100`
- if only `cash_amount` is set: `cash_amount / (1 - haircut)`

`haircut_amount()` returns `collateral_market_value() * haircut`.

`cash_lent()` returns:

- `cash_amount`, when the trade was built with a cash amount
- otherwise `collateral_market_value() * (1 - haircut)`

`interest_amount()` returns `cash_lent() * rate * year_fraction()`.

`repurchase_amount()` returns `cash_lent() + interest_amount()`.

### Example

```python
from decimal import Decimal

from fuggers_py import Date
from fuggers_py.funding import RepoTrade, repo_financing_cost

trade = RepoTrade(
    start_date=Date.from_ymd(2026, 1, 2),
    end_date=Date.from_ymd(2026, 2, 1),
    rate="0.05",
    collateral_price="101.50",
    haircut="0.02",
    notional="1000000",
    currency="usd",
    day_count_convention="ACT_360",
    collateral_instrument_id="US91282CKH3",
)

year_fraction = trade.year_fraction()
collateral_value = trade.collateral_market_value()
cash_lent = trade.cash_lent()
haircut_cash = trade.haircut_amount()
repo_interest = trade.interest_amount()
cash_due_at_repurchase = trade.repurchase_amount()

same_interest = repo_financing_cost(trade)

assert collateral_value == Decimal("1015000")
assert cash_lent == Decimal("994700.00")
assert haircut_cash == Decimal("20300.00")
assert same_interest == repo_interest
assert cash_due_at_repurchase == cash_lent + repo_interest
```

## `RepoQuote`

`RepoQuote` is a market quote for a repo rate. It can also carry a haircut, a
start and end date, a tenor label such as `"1W"`, a collateral type, an as-of
date, a currency, a source, and bid/ask/mid quote sides.

Use it to store market data before feeding rates or haircuts into pricing,
curve, or carry code.

### Construction Behavior

The constructor normalizes values after the dataclass is created:

- `instrument_id` is parsed and stripped.
- `rate`, `haircut`, `bid`, `ask`, and `mid` are stored as `Decimal` when set.
- `term` is stripped and uppercased.
- `collateral_type` and `source` are stripped.
- `currency` is stored as provided; pass a `Currency` value when you want a
  canonical currency object.
- If `mid` is missing and `rate` is set, `mid` is set to `rate`.
- If `mid` and `rate` are both missing, but both `bid` and `ask` are set,
  `mid` is set to the average of `bid` and `ask`.

### Methods

`quoted_value(side="mid")` returns the requested quote side. The side may be
`"bid"`, `"ask"`, or `"mid"`. It returns `None` when that side is not available.

`for_side(side)` returns a copy of the quote with `rate` set to the requested
side. It returns `None` when that side is not available.

### Example

```python
from decimal import Decimal

from fuggers_py import Currency, Date
from fuggers_py.funding import RepoQuote

quote = RepoQuote(
    instrument_id=" repo-ust-1w ",
    bid="0.0440",
    ask="0.0460",
    term=" 1w ",
    collateral_type=" UST ",
    as_of=Date.from_ymd(2026, 4, 17),
    currency=Currency.USD,
    source=" broker screen ",
)

mid_rate = quote.quoted_value("mid")
bid_rate = quote.quoted_value("bid")
ask_quote = quote.for_side("ask")

assert str(quote.instrument_id) == "repo-ust-1w"
assert quote.term == "1W"
assert quote.collateral_type == "UST"
assert mid_rate == Decimal("0.0450")
assert bid_rate == Decimal("0.0440")
assert ask_quote is not None
assert ask_quote.rate == Decimal("0.0460")
```

## `HaircutQuote`

`HaircutQuote` is a market quote for a haircut. A haircut is the part of
collateral value that is not financed. A `0.02` haircut means 2% of the
collateral value is held back.

Use it when haircut data is separate from the repo rate quote.

### Construction Behavior

The constructor normalizes values after the dataclass is created:

- `instrument_id` is parsed and stripped.
- `haircut`, `bid`, `ask`, and `mid` are stored as `Decimal` when set.
- `collateral_type` and `source` are stripped.
- `currency` is stored as provided; pass a `Currency` value when you want a
  canonical currency object.
- If `mid` is missing and `haircut` is set, `mid` is set to `haircut`.
- If `mid` and `haircut` are both missing, but both `bid` and `ask` are set,
  `mid` is set to the average of `bid` and `ask`.

### Methods

`quoted_value(side="mid")` returns the requested quote side. The side may be
`"bid"`, `"ask"`, or `"mid"`. It returns `None` when that side is not available.

`for_side(side)` returns a copy of the quote with `haircut` set to the requested
side. It returns `None` when that side is not available.

### Example

```python
from decimal import Decimal

from fuggers_py import Currency, Date
from fuggers_py.funding import HaircutQuote

quote = HaircutQuote(
    instrument_id=" ust-on-the-run ",
    bid="0.015",
    ask="0.025",
    collateral_type=" Treasury ",
    as_of=Date.from_ymd(2026, 4, 17),
    currency=Currency.USD,
)

mid_haircut = quote.quoted_value("mid")
ask_quote = quote.for_side("ask")

assert str(quote.instrument_id) == "ust-on-the-run"
assert quote.collateral_type == "Treasury"
assert mid_haircut == Decimal("0.020")
assert ask_quote is not None
assert ask_quote.haircut == Decimal("0.025")
```

## `RepoReferenceData`

`RepoReferenceData` stores static repo facts. Static facts are values that
describe the repo instrument or market point, not a live market quote.

Use it to keep the usual currency, collateral currency, term, collateral type,
default haircut, and settlement lag for a repo market point.

### Construction Behavior

The constructor normalizes values after the dataclass is created:

- `instrument_id` is parsed and stripped.
- `term` is stripped and uppercased.
- `collateral_type` is stripped.
- `haircut` is stored as `Decimal` when set.
- `currency` and `collateral_currency` are stored as provided; pass `Currency`
  values when you want canonical currency objects.

`RepoReferenceData` has no helper methods beyond its public fields.

### Example

```python
from decimal import Decimal

from fuggers_py import Currency
from fuggers_py.funding import RepoReferenceData

reference = RepoReferenceData(
    instrument_id=" repo-ust-1w ",
    currency=Currency.USD,
    collateral_currency=Currency.USD,
    term=" 1w ",
    collateral_type=" UST ",
    haircut="0.02",
    settlement_lag_days=1,
)

assert str(reference.instrument_id) == "repo-ust-1w"
assert reference.term == "1W"
assert reference.collateral_type == "UST"
assert reference.haircut == Decimal("0.02")
```

## Repo Carry Helpers

Repo carry helpers work from a `RepoTrade`.

`repo_financing_cost(trade)` returns `trade.interest_amount()`. The result is a
currency amount.

`repo_net_carry(trade, collateral_income=0, haircut_financing_cost=0)` returns:

```text
collateral_income - trade.interest_amount() - haircut_financing_cost
```

The result is a currency amount. Positive means income is larger than costs.
Negative means the repo and haircut costs are larger than income.

`repo_carry_return(trade, collateral_income=0, haircut_financing_cost=0)`
returns:

```text
repo_net_carry(...) / trade.cash_lent()
```

The result is a raw decimal return. It raises `ValueError` if cash lent is zero.

### Example

```python
from decimal import Decimal

from fuggers_py import Date
from fuggers_py.funding import (
    RepoTrade,
    repo_carry_return,
    repo_financing_cost,
    repo_net_carry,
)

trade = RepoTrade(
    start_date=Date.from_ymd(2026, 2, 3),
    end_date=Date.from_ymd(2026, 3, 5),
    rate=Decimal("0.03"),
    collateral_price=Decimal("100.00"),
    haircut=Decimal("0.02"),
    cash_amount=Decimal("980000"),
    currency="USD",
)

financing_cost = repo_financing_cost(trade)
net_carry = repo_net_carry(
    trade,
    collateral_income=Decimal("5000"),
    haircut_financing_cost=Decimal("100"),
)
carry_return = repo_carry_return(
    trade,
    collateral_income=Decimal("5000"),
    haircut_financing_cost=Decimal("100"),
)

profitable = net_carry > Decimal("0")

assert financing_cost == trade.interest_amount()
assert net_carry == Decimal("5000") - financing_cost - Decimal("100")
assert carry_return == net_carry / trade.cash_lent()
assert profitable is True
```

## Haircuts and All-In Financing Cost

These helpers use collateral value, haircut, rates, and year fraction directly.
They do not need a `RepoTrade`.

`haircut_amount(collateral_value, haircut)` returns:

```text
collateral_value * haircut
```

The result is a currency amount.

`financed_cash(collateral_value, haircut)` returns:

```text
collateral_value - haircut_amount(...)
```

The result is the cash amount financed by the repo.

`haircut_financing_cost(collateral_value, haircut, funding_rate, year_fraction)`
returns:

```text
haircut_amount(...) * funding_rate * year_fraction
```

The result is a currency amount.

`haircut_drag(collateral_value, haircut, repo_rate, haircut_funding_rate,
year_fraction)` returns:

```text
haircut_amount(...) * (haircut_funding_rate - repo_rate) * year_fraction
```

Positive drag means the haircut is funded at a higher rate than the repo rate.
Negative drag means the haircut is funded at a lower rate.

`all_in_financing_cost(collateral_value, haircut, repo_rate,
haircut_funding_rate, year_fraction)` returns:

```text
financed_cash(...) * repo_rate * year_fraction
+ haircut_financing_cost(...)
```

The result is a currency amount.

### Example

```python
from decimal import Decimal

from fuggers_py.funding import (
    all_in_financing_cost,
    financed_cash,
    haircut_amount,
    haircut_drag,
    haircut_financing_cost,
)

collateral_value = Decimal("1000000")
haircut = Decimal("0.02")
repo_rate = Decimal("0.045")
haircut_funding_rate = Decimal("0.055")
year_fraction = Decimal("0.25")

withheld_cash = haircut_amount(
    collateral_value=collateral_value,
    haircut=haircut,
)
cash_lent = financed_cash(
    collateral_value=collateral_value,
    haircut=haircut,
)
haircut_cost = haircut_financing_cost(
    collateral_value=collateral_value,
    haircut=haircut,
    funding_rate=haircut_funding_rate,
    year_fraction=year_fraction,
)
drag = haircut_drag(
    collateral_value=collateral_value,
    haircut=haircut,
    repo_rate=repo_rate,
    haircut_funding_rate=haircut_funding_rate,
    year_fraction=year_fraction,
)
all_in_cost = all_in_financing_cost(
    collateral_value=collateral_value,
    haircut=haircut,
    repo_rate=repo_rate,
    haircut_funding_rate=haircut_funding_rate,
    year_fraction=year_fraction,
)

assert withheld_cash == Decimal("20000.00")
assert cash_lent == Decimal("980000.00")
assert haircut_cost == Decimal("275.0000")
assert drag == Decimal("50.0000")
assert all_in_cost == Decimal("11300.0000")
```

## Futures Invoice and Implied Repo

These helpers use bond-future delivery math.

`futures_invoice_amount(futures_price, conversion_factor,
accrued_at_delivery=0, face_amount=100)` returns the cash paid at delivery:

```text
face_amount * (futures_price * conversion_factor + accrued_at_delivery) / 100
```

`futures_price` and `accrued_at_delivery` are percent-of-par values.
`face_amount` is a currency amount.

`implied_repo_rate(...)` calculates the repo rate implied by this trade:

1. buy the bond at `spot_price + accrued_on_purchase`
2. receive the futures invoice amount at delivery
3. add coupon income received before delivery
4. convert the gain or loss into an annualized raw decimal rate

In formula form:

```text
purchase_amount = face_amount * (spot_price + accrued_on_purchase) / 100
delivery_amount = futures_invoice_amount(...) + face_amount * coupon_income / 100
implied_repo_rate = (delivery_amount / purchase_amount - 1) / year_fraction
```

`spot_price`, `futures_price`, `coupon_income`, `accrued_on_purchase`, and
`accrued_at_delivery` are percent-of-par values. `face_amount` is a currency
amount.

`implied_repo_rate` raises `ValueError` when the dates produce a zero year
fraction or when the purchase amount is zero.

`implied_repo_rate_from_trade(trade, ...)` uses:

- `trade.collateral_price` as the spot price
- `trade.start_date` and `trade.end_date` as the implied repo dates
- `trade.day_count_convention` as the day-count rule
- `trade.notional` as `face_amount` when `trade.notional` is set
- `100` as `face_amount` when the trade has no `notional`

It does not use `trade.cash_amount` as the futures face amount.

### Example

```python
from decimal import Decimal

from fuggers_py import Date
from fuggers_py.funding import (
    RepoTrade,
    futures_invoice_amount,
    implied_repo_rate,
    implied_repo_rate_from_trade,
)

start = Date.from_ymd(2026, 3, 1)
delivery = Date.from_ymd(2026, 6, 1)

invoice = futures_invoice_amount(
    futures_price=Decimal("112.50"),
    conversion_factor=Decimal("0.89"),
    accrued_at_delivery=Decimal("1.20"),
    face_amount=Decimal("1000000"),
)

rate = implied_repo_rate(
    spot_price=Decimal("100.40"),
    futures_price=Decimal("112.50"),
    conversion_factor=Decimal("0.89"),
    start_date=start,
    end_date=delivery,
    coupon_income=Decimal("1.50"),
    accrued_on_purchase=Decimal("0.80"),
    accrued_at_delivery=Decimal("1.20"),
    face_amount=Decimal("1000000"),
)

trade = RepoTrade(
    start_date=start,
    end_date=delivery,
    rate=Decimal("0.045"),
    collateral_price=Decimal("100.40"),
    haircut=Decimal("0.02"),
    notional=Decimal("1000000"),
)

rate_from_trade = implied_repo_rate_from_trade(
    trade,
    futures_price=Decimal("112.50"),
    conversion_factor=Decimal("0.89"),
    coupon_income=Decimal("1.50"),
    accrued_on_purchase=Decimal("0.80"),
    accrued_at_delivery=Decimal("1.20"),
)

cash_only_trade = RepoTrade(
    start_date=start,
    end_date=delivery,
    rate=Decimal("0.045"),
    collateral_price=Decimal("100.40"),
    haircut=Decimal("0.02"),
    cash_amount=Decimal("980000"),
)

cash_only_rate = implied_repo_rate_from_trade(
    cash_only_trade,
    futures_price=Decimal("112.50"),
    conversion_factor=Decimal("0.89"),
    coupon_income=Decimal("1.50"),
    accrued_on_purchase=Decimal("0.80"),
    accrued_at_delivery=Decimal("1.20"),
)

assert invoice > Decimal("0")
assert rate == rate_from_trade
assert cash_only_rate == rate
```

The last assertion holds because `implied_repo_rate_from_trade` uses face amount
`100` when the trade has no `notional`. The implied rate is a ratio, so using
`100` face or `1000000` face gives the same rate when all price inputs are the
same.

## Specialness

Specialness measures how much cheaper it is to borrow cash against one specific
security than against general collateral. General collateral means ordinary,
non-special collateral.

`specialness_spread(general_collateral_rate, specific_collateral_rate)` returns:

```text
general_collateral_rate - specific_collateral_rate
```

The result is a raw decimal spread. Positive means the specific collateral rate
is lower than the general collateral rate.

`specialness_value(cash_amount, general_collateral_rate,
specific_collateral_rate, year_fraction)` returns:

```text
cash_amount * specialness_spread(...) * year_fraction
```

The result is a currency amount.

`is_special(general_collateral_rate, specific_collateral_rate)` returns `True`
when `specialness_spread(...) > 0`.

### Example

```python
from decimal import Decimal

from fuggers_py.funding import is_special, specialness_spread, specialness_value

gc_rate = Decimal("0.045")
specific_rate = Decimal("0.035")
cash_amount = Decimal("1000000")
year_fraction = Decimal("0.25")

spread = specialness_spread(
    general_collateral_rate=gc_rate,
    specific_collateral_rate=specific_rate,
)
value = specialness_value(
    cash_amount=cash_amount,
    general_collateral_rate=gc_rate,
    specific_collateral_rate=specific_rate,
    year_fraction=year_fraction,
)
special = is_special(
    general_collateral_rate=gc_rate,
    specific_collateral_rate=specific_rate,
)

assert spread == Decimal("0.010")
assert value == Decimal("2500.00000")
assert special is True
```

```{eval-rst}
.. automodule:: fuggers_py.funding
   :members:
   :member-order: bysource
```
