# `fuggers_py.portfolio`

Portfolio construction, aggregation, benchmark comparison, contribution,
stress testing, liquidity summaries, and ETF-style outputs.

Use one-layer imports from `fuggers_py.portfolio`:

```python
from fuggers_py.portfolio import Portfolio, Holding, calculate_portfolio_analytics
```

The public contract for this page is the `fuggers_py.portfolio` export list in
`specs/public_api_surface.json` and `src/fuggers_py/portfolio/__init__.py`.
The root package currently imports `build_creation_basket`, so direct import can
work, but that name is not in `__all__` or the JSON contract. Treat it as an
importable helper outside the stable public surface.

## Core Rules

- A raw decimal means `Decimal("0.05")` for 5%.
- A basis point is 0.01 percentage point. Fields or parameters ending in
  `_bps` use basis points.
- Fields ending in `_pct` are percentage points. For example, `5` means 5%.
- Prices are usually percent-of-par. For example, a clean price of `99.5` means
  99.5% of par.
- Currency values are in the portfolio reporting currency unless a field says
  otherwise.
- DV01 and CS01 are currency changes for a one-basis-point move.
- Portfolio weighted averages use dirty-value weights by default. Override this
  with `AnalyticsConfig(weighting_method=...)`.
- Benchmark active values are always portfolio minus benchmark.
- In rate and spread return estimates, a positive shock means rates or spreads
  move up. The estimated return is usually negative when the portfolio has
  positive DV01 or CS01.
- Most result objects are immutable records with named fields. Some also behave
  like mappings or sequences.

Examples below assume `bond`, `second_bond`, `curve`, `settlement_date`,
`quote_outputs`, and identifier objects come from the relevant bond, curve, or
quote-output pages.

## Containers, Holdings, And Config

### `Holding`, `Position`, `HoldingAnalytics`, `PositionAnalytics`

`Holding` represents one bond position. Use it when you want to attach a bond,
quantity, price or market value, analytics, and classification data to a
portfolio row.

The constructor converts `quantity`, `market_value`, `accrued_interest`,
`liquidity_score`, and `fx_rate` to `Decimal`. `clean_price` may be a `Price`
object or a decimal percent-of-par value. If analytics need a price and neither
`clean_price` nor `market_value` is present, the analytics layer needs a curve.

Useful `Holding` members:

- `par_amount`: returns `quantity`.
- `market_price`: returns the clean price as a percent-of-par decimal, or
  `None`.
- `currency`: uses `classification.currency` when present, otherwise the bond
  currency.
- `name()`: returns `label`, then `id`, then the bond ISIN, then the bond class
  name.
- `market_value_amount`: returns explicit `market_value`, or
  `clean_price * quantity`, or zero.
- `dirty_market_value`: adds accrued interest times quantity to clean value.
- `base_currency_value`: returns `market_value_amount * fx_rate`.
- `weight_in_portfolio(total_market_value)`: returns clean-value weight, or
  zero when the total is zero.

`Position` is an alias for `Holding`. `HoldingAnalytics` is the per-holding
analytics record. `PositionAnalytics` is an alias for `HoldingAnalytics`.

`HoldingAnalytics` stores clean value, dirty value, accrued value, duration,
convexity, DV01, yields, spreads, CS01, key-rate profile, liquidity score,
weighted average life, and coupon. Values and PV fields are currency amounts.
Yields and spreads are raw decimals unless the field name says otherwise.

### `HoldingBuilder`

`HoldingBuilder` is a mutable helper for building a `Holding` step by step.
`build()` raises `ValueError` if no instrument has been set.

Useful builder methods:

- `with_instrument(instrument)`
- `with_quantity(quantity)`
- `with_par_amount(par_amount)`, an alias for `with_quantity()`
- `with_clean_price(clean_price)`
- `with_market_price(market_price)`, an alias for `with_clean_price()`
- `with_market_value(market_value)`
- `with_accrued_interest(accrued_interest)`
- `with_analytics(analytics)`
- `with_label(label)`
- `with_id(value)`
- `with_classification(classification)`
- `with_rating_info(rating_info)`
- `with_sector_info(sector_info)`
- `with_seniority_info(seniority_info)`
- `with_liquidity_score(liquidity_score)`
- `with_fx_rate(fx_rate)`
- `build()`

```python
from decimal import Decimal

from fuggers_py import Currency
from fuggers_py.portfolio import (
    Classification,
    CreditRating,
    HoldingBuilder,
    Sector,
)

classification = Classification(
    sector=Sector.CORPORATE,
    rating=CreditRating.BBB,
    country="US",
    currency=Currency.USD,
    issuer="Example Issuer",
)

holding = (
    HoldingBuilder()
    .with_instrument(bond)
    .with_quantity(Decimal("1000000"))
    .with_clean_price(Decimal("99.50"))
    .with_accrued_interest(Decimal("0.75"))
    .with_classification(classification)
    .with_liquidity_score(Decimal("0.80"))
    .with_label("EXAMPLE 5.00 2030")
    .build()
)

print(holding.name())
print(holding.market_price)
print(holding.market_value_amount)
print(holding.dirty_market_value)
```

### `CashPosition`

`CashPosition` represents cash inside a portfolio. `amount` and `fx_rate` are
converted to `Decimal`. Cash has no clean/dirty split.

Useful members:

- `market_value()`: returns the cash amount.
- `base_currency_value`: returns `amount * fx_rate`.

```python
from decimal import Decimal

from fuggers_py import Currency
from fuggers_py.portfolio import CashPosition

cash = CashPosition(
    amount=Decimal("250000"),
    currency=Currency.USD,
    label="operating cash",
)

print(cash.market_value())
print(cash.base_currency_value)
```

### `Portfolio`, `PortfolioBuilder`, `PortfolioMetrics`

`Portfolio` is an immutable collection of bond holdings and cash positions in
one reporting currency. It stores positions in input order.

Useful `Portfolio` members:

- `Portfolio.new(positions, currency)`: converts a mutable list into an
  immutable tuple.
- `total_quantity()`: sums quantities on positions that have a quantity. Cash is
  ignored.
- `holdings()`: returns all positions, including cash.
- `investable_holdings()`: returns bond holdings only.
- `cash_positions()`: returns cash positions only.
- `total_market_value()`: sums clean market value for bonds and amount for cash.

`PortfolioBuilder` lets you add positions before creating the immutable
portfolio. `with_currency()` sets the reporting currency. `add_position()` and
`add_holding()` append one item. `add_positions()` appends many items. If no
currency is set, the first added position can set it. `build()` raises
`ValueError` if no currency was set or inferred.

`PortfolioMetrics` is the full portfolio analytics record. It holds clean PV,
dirty PV, accrued value, weighted duration, convexity, DV01, weights, currency,
yields, spreads, CS01, liquidity score, key-rate profile, market-value totals,
cash value, counts, duration variants, weighted average maturity, and weighted
average coupon.

```python
from fuggers_py import Currency
from fuggers_py.portfolio import PortfolioBuilder

portfolio = (
    PortfolioBuilder()
    .with_currency(Currency.USD)
    .add_position(holding)
    .add_position(cash)
    .build()
)

print(portfolio.total_quantity())
print(portfolio.total_market_value())
print([item.name() for item in portfolio.investable_holdings()])
```

### `AnalyticsConfig` And `WeightingMethod`

`AnalyticsConfig` controls valuation date, weighting basis, key-rate tenors,
and default currency for portfolio analytics.

Fields:

- `settlement_date`: date used for accrued interest and valuation.
- `weighting_method`: one of `DIRTY_VALUE`, `CLEAN_VALUE`, `MARKET_VALUE`, or
  `EQUAL`.
- `key_rate_tenors`: tenors used to build key-rate profiles.
- `default_currency`: currency used when a default is needed.

The default weighting method is `WeightingMethod.DIRTY_VALUE`.

```python
from fuggers_py.portfolio import (
    AnalyticsConfig,
    PortfolioAnalytics,
    WeightingMethod,
)

config = AnalyticsConfig(
    settlement_date=settlement_date,
    weighting_method=WeightingMethod.CLEAN_VALUE,
)

metrics = PortfolioAnalytics(portfolio).metrics(
    curve,
    settlement_date,
    config=config,
)

print(metrics.weights)
print(metrics.duration)
```

### Classification Objects

These records attach grouping data to holdings.

- `Classification`: optional sector, rating, seniority, country, currency,
  issuer, region, and custom fields.
- `CreditRating`: enum values from `AAA` through `D`, plus `NR`.
- `RatingInfo`: rating plus optional agency and outlook.
- `Sector`: high-level sector enum, such as `GOVERNMENT`, `CORPORATE`, `ETF`,
  `CASH`, and `OTHER`.
- `SectorInfo`: sector plus optional issuer, country, region, and subsector.
- `Seniority`: seniority enum, such as `SENIOR_SECURED` or `SUBORDINATED`.
- `SeniorityInfo`: seniority plus `secured` boolean.
- `RatingBucket`: a label and tuple of `CreditRating` values.
- `MaturityBucket`: a half-open maturity range in years.

Useful methods and properties:

- `CreditRating.score()`: lower score means stronger credit. `NR` returns `99`.
- `MaturityBucket.contains(years_to_maturity)`: checks whether a maturity is in
  the bucket.

```python
from fuggers_py.portfolio import CreditRating, MaturityBucket

print(CreditRating.BBB.score())

bucket = MaturityBucket("2-5Y", 2.0, 5.0)
print(bucket.contains(3.25))
print(bucket.contains(5.0))
```

### Shared Result Records

- `BucketResult`: bucket-level clean PV, dirty PV, DV01, weight, market value,
  average YTM, average duration, average spread, and holding count.
- `StressResult`: base dirty PV, stressed dirty PV, signed `actual_change`,
  `dv01_approximation`, optional scenario name, and optional breakdown.
- `StressResult.shocked_pv`: alias for `stressed_dirty_pv`.
- `StressResult.pv_change`: alias for `actual_change`.

`actual_change` is stressed value minus base value. Negative values are losses.

## Portfolio Analytics And NAV

### `PortfolioAnalytics`

`PortfolioAnalytics` wraps a portfolio and runs valuation on each position.
`position_metrics(curve, settlement_date, ...)` returns one
`PositionAnalytics` record per portfolio position. `metrics(curve,
settlement_date, ...)` aggregates those records into `PortfolioMetrics`.

When a holding already has `analytics`, the analytics layer uses that record.
Otherwise it prices from `clean_price`, then from `market_value / quantity`, or
from `curve`. If no price or curve is available, analytics can raise
`ValueError`.

`calculate_portfolio_analytics(portfolio, curve=..., settlement_date=...)` is
the one-call version of `PortfolioAnalytics(portfolio).metrics(...)`.

```python
from fuggers_py.portfolio import (
    PortfolioAnalytics,
    calculate_portfolio_analytics,
)

analytics = PortfolioAnalytics(portfolio)

position_rows = analytics.position_metrics(curve, settlement_date)
for row in position_rows:
    print(row.name, row.clean_value, row.dirty_value, row.dv01)

metrics = calculate_portfolio_analytics(
    portfolio,
    curve=curve,
    settlement_date=settlement_date,
)

print(metrics.dirty_pv)
print(metrics.duration)
print(metrics.weights)
```

### NAV And Weighted Metric Helpers

These helpers return one field or one small result object from
`PortfolioMetrics`.

- `calculate_nav_breakdown`: returns `NavBreakdown`.
- `aggregate_key_rate_profile`: returns `KeyRateProfile`.
- `partial_dv01s`: alias for `aggregate_key_rate_profile`.
- `total_dv01`: total portfolio DV01.
- `total_cs01`: total portfolio CS01.
- `weighted_duration`: portfolio duration.
- `weighted_convexity`: portfolio convexity.
- `weighted_current_yield`: current yield.
- `weighted_spreads`: Z-spread.
- `weighted_ytm`: yield to maturity.
- `weighted_ytw`: yield to worst.
- `weighted_ytc`: yield to call.

`NavBreakdown` stores clean PV, dirty PV, accrued value, clean market value,
dirty market value, and cash value in currency units.

`KeyRateProfile` behaves like a mapping from tenor string to DV01. It supports
`keys()`, `values()`, `items()`, `get()`, `as_dict()`, `total_dv01`, and
`by_tenor(tenor)`.

```python
from fuggers_py.portfolio import (
    aggregate_key_rate_profile,
    calculate_nav_breakdown,
    total_dv01,
    weighted_ytm,
)

nav = calculate_nav_breakdown(
    portfolio,
    curve=curve,
    settlement_date=settlement_date,
)
print(nav.clean_pv, nav.dirty_pv, nav.cash_value)

profile = aggregate_key_rate_profile(
    portfolio,
    curve=curve,
    settlement_date=settlement_date,
)
print(profile.total_dv01)
print(profile.by_tenor("10Y"))

for tenor, dv01 in profile.items():
    print(tenor, dv01)

print(total_dv01(portfolio, curve=curve, settlement_date=settlement_date))
print(weighted_ytm(portfolio, curve=curve, settlement_date=settlement_date))
```

### Quote-Output Portfolio Analytics

`PortfolioPosition` is a light record with `instrument_id` and `quantity`.

`PortfolioAnalyzer` aggregates already-computed `BondQuoteOutput` records into
`PortfolioAnalyticsOutput`. It skips positions with no quote or no clean price.
It value-weights duration, convexity, and spreads by dirty value. If reference
data with `sector` and `rating` is supplied, it also returns sector and rating
breakdowns.

```python
from decimal import Decimal

from fuggers_py.portfolio import PortfolioAnalyzer, PortfolioPosition

positions = [
    PortfolioPosition(instrument_id=first_instrument_id, quantity=Decimal("1000")),
    PortfolioPosition(instrument_id=second_instrument_id, quantity=Decimal("500")),
]

output = PortfolioAnalyzer().analyze(
    portfolio_id="portfolio:demo",
    positions=positions,
    quote_outputs=quote_outputs,
)

print(output.total_market_value)
print(output.fully_priced)
```

## Risk, Yield, Spread, And Credit

### Risk And Duration

`RiskMetrics` stores duration, modified duration, effective duration, Macaulay
duration, best duration, convexity, effective convexity, DV01, and CS01.

Functions:

- `calculate_risk_metrics`: returns `RiskMetrics`.
- `weighted_modified_duration`: returns `PortfolioMetrics.modified_duration`.
- `weighted_effective_duration`: returns `PortfolioMetrics.effective_duration`.
- `weighted_macaulay_duration`: returns `PortfolioMetrics.macaulay_duration`.
- `weighted_effective_convexity`: returns effective convexity.
- `weighted_best_duration`: uses effective duration when present, otherwise
  modified duration, weighted by dirty value.

### Yield

`YieldMetrics` stores YTM, YTW, YTC, current yield, and best yield as raw
decimals.

Functions:

- `calculate_yield_metrics`: returns `YieldMetrics`.
- `weighted_best_yield`: returns the portfolio best yield.

### Spread

`SpreadMetrics` stores Z-spread, OAS, G-spread, I-spread, asset-swap spread,
best spread, spread duration, and CS01. Spreads are raw decimals.

Functions:

- `calculate_spread_metrics`: returns `SpreadMetrics`.
- `weighted_z_spread`, `weighted_oas`, `weighted_g_spread`,
  `weighted_i_spread`, and `weighted_asw`: return individual spread fields.
- `weighted_best_spread`: returns the best available spread.
- `weighted_spread_duration`: returns spread duration.

### Credit Quality

`CreditQualityMetrics` stores rating distribution, sector distribution, average
rating score, average rating, investment-grade weight, high-yield weight,
default weight, unrated weight, BBB weight, BB weight, crossover weight,
quality tiers, and migration risk.

`CreditMetrics` is an alias for `CreditQualityMetrics`.

`QualityTiers` stores investment-grade, high-yield, distressed, defaulted, and
unrated weights.

`FallenAngelRisk` stores BBB weight, market value at risk, and holding count.
Its `weight` property returns `bbb_weight`.

`RisingStarRisk` stores BB weight, market value potential, and holding count.
Its `weight` property returns `bb_weight`.

`MigrationRisk` combines fallen-angel and rising-star risk. Its
`crossover_weight` property returns BBB weight plus BB weight.

Functions:

- `calculate_credit_quality`: returns `CreditQualityMetrics`.
- `calculate_credit_metrics`: alias for `calculate_credit_quality`.
- `calculate_migration_risk`: returns `MigrationRisk`.

```python
from fuggers_py.portfolio import (
    calculate_credit_quality,
    calculate_risk_metrics,
    calculate_spread_metrics,
    calculate_yield_metrics,
    weighted_best_duration,
    weighted_oas,
)

risk = calculate_risk_metrics(
    portfolio,
    curve=curve,
    settlement_date=settlement_date,
)
print(risk.duration, risk.dv01)

yields = calculate_yield_metrics(
    portfolio,
    curve=curve,
    settlement_date=settlement_date,
)
print(yields.ytm, yields.best_yield)

spreads = calculate_spread_metrics(
    portfolio,
    curve=curve,
    settlement_date=settlement_date,
)
print(spreads.z_spread, spreads.cs01)

credit = calculate_credit_quality(portfolio)
print(credit.distribution)
print(credit.migration_risk.crossover_weight)

print(weighted_best_duration(portfolio, curve=curve, settlement_date=settlement_date))
print(weighted_oas(portfolio, curve=curve, settlement_date=settlement_date))
```

## Liquidity

Liquidity scores are expected to be 0-to-1 decimals. Higher is more liquid.
If a holding has no liquidity score, portfolio analytics treat it as `1`.

The bucket labels are fixed:

- `high`: score >= `0.75`
- `medium`: `0.50` <= score < `0.75`
- `limited`: `0.25` <= score < `0.50`
- `illiquid`: score < `0.25`

`estimate_days_to_liquidate` uses a simple formula:
`1 + (1 - liquidity_score) * 9`, then multiplies by
`liquidation_fraction`. `liquidation_fraction` must be between `0` and `1`.

Records:

- `LiquidityBucket`: label, min score, max score, weight, dirty PV, and holding
  count.
- `LiquidityDistribution`: mapping from bucket label to `LiquidityBucket`.
  It supports `keys()`, `values()`, `items()`, `total_weight`, and
  `total_dirty_pv`.
- `DaysToLiquidate`: days, liquidity score, and liquidation fraction. It also
  behaves like a mapping over its fields.
- `LiquidityMetrics`: liquidity score, bid-ask spread, days to liquidate, and
  distribution. It also behaves like a mapping over its fields.

Functions:

- `weighted_liquidity_score`: weighted portfolio liquidity score.
- `weighted_bid_ask_spread`: dirty-value-weighted bid-ask spread. It reads
  `bid_ask_spread`, `bid_ask`, or `bidask_spread` from holding custom fields
  when present.
- `liquidity_distribution`: fixed bucket distribution.
- `estimate_days_to_liquidate`: simple days estimate.
- `calculate_liquidity_metrics`: full liquidity record.

```python
from decimal import Decimal

from fuggers_py.portfolio import (
    calculate_liquidity_metrics,
    estimate_days_to_liquidate,
    liquidity_distribution,
)

liquidity = calculate_liquidity_metrics(
    portfolio,
    curve=curve,
    settlement_date=settlement_date,
)

print(liquidity["liquidity_score"])
print(liquidity.days_to_liquidate.days)

distribution = liquidity_distribution(
    portfolio,
    curve=curve,
    settlement_date=settlement_date,
)

for label, bucket in distribution.items():
    print(label, bucket.weight, bucket.holding_count)

half_sale = estimate_days_to_liquidate(
    portfolio,
    curve=curve,
    settlement_date=settlement_date,
    liquidation_fraction=Decimal("0.50"),
)
print(half_sale.days)
```

## Bucketing And Distributions

Bucketing helpers group holdings into named buckets. Cash is included only in
the maturity helper, where it is grouped under `Cash`.

Records:

- `MaturityDistribution`: mapping from maturity bucket label to positions. It
  also stores the bucket definition.
- `RatingDistribution`: mapping from rating label to positions.
- `SectorDistribution`: mapping from sector label to positions.
- `ClassifierDistribution`: mapping from a named classifier to positions.
- `CustomDistribution`: mapping from a custom field to positions.
- `BucketMetrics`: alias for `BucketResult`.
- `Bucketing`: wrapper with `bucket_dv01(curve, settlement_date, buckets=...)`.

Distribution objects support `keys()`, `values()`, `items()`, `get()`,
`as_dict()`, `bucket_count`, and `holding_count`.

Functions:

- `bucket_by_maturity`: buckets by years to maturity using `DEFAULT_BUCKETS`.
  Default buckets are `0-2Y`, `2-5Y`, `5-10Y`, and `10Y+`.
- `bucket_by_rating`: uses `rating_info`, then `classification.rating`, then
  `NR`.
- `bucket_by_sector`: uses `sector_info`, then `classification.sector`, then
  `OTHER`.
- `bucket_by_country`, `bucket_by_currency`, `bucket_by_issuer`, and
  `bucket_by_region`: return plain dictionaries keyed by classification field.
- `bucket_by_custom_field`: uses `holding.custom_fields`, then
  `classification.custom_fields`, then `UNKNOWN`.
- `bucket_by_classifier`: supports `rating`, `sector`, `seniority`, `country`,
  `region`, `issuer`, `currency`, custom fields, and other classification
  fields. Missing values use `UNKNOWN`.

```python
from fuggers_py.portfolio import (
    Bucketing,
    bucket_by_classifier,
    bucket_by_custom_field,
    bucket_by_maturity,
    bucket_by_rating,
    bucket_by_sector,
)

maturity = bucket_by_maturity(
    portfolio,
    settlement_date=settlement_date,
)
print(maturity.bucket_count)
print(maturity.holding_count)

rating = bucket_by_rating(portfolio)
for rating_label, positions in rating.items():
    print(rating_label, len(positions))

sector = bucket_by_sector(portfolio)
print(sector.as_dict())

custom = bucket_by_custom_field(portfolio, "strategy")
print(custom.keys())

issuer = bucket_by_classifier(portfolio, "issuer")
print(issuer.items())

bucket_metrics = Bucketing(portfolio).bucket_dv01(
    curve,
    settlement_date,
)
for bucket in bucket_metrics:
    print(bucket.label, bucket.dv01, bucket.average_duration)
```

## Benchmark Comparison

Benchmark helpers compare two portfolios on active weights, duration, yield,
spread, and risk. Active means portfolio minus benchmark.

Records:

- `ActiveWeight`: one named active weight. `value` returns `active_weight`.
  `as_dict()` returns a simple dictionary. `__getitem__` supports `name`,
  `portfolio_weight`, `benchmark_weight`, `active_weight`, and `value`.
- `ActiveWeights`: mapping from name to active weight. It supports `keys()`,
  `values()`, `items()`, `get()`, `by_name()`, `to_dict()`,
  `portfolio_weights`, `benchmark_weights`, and `net_active_weight`.
- `DurationComparison`: portfolio, benchmark, and active duration.
- `RiskComparison`: portfolio, benchmark, and active dirty PV and DV01.
- `YieldComparison`: portfolio, benchmark, and active current yield, YTM, and
  YTW.
- `SpreadComparison`: portfolio, benchmark, and active Z-spread and OAS.
- `SectorComparison`: portfolio, benchmark, and active sector weights.
- `RatingComparison`: portfolio, benchmark, and active rating weights.
- `BenchmarkComparison`: full comparison result. It exposes convenience
  properties for active dirty PV, duration, DV01, current yield, Z-spread, YTM,
  YTW, OAS, sector active weights, and rating active weights.
- `BenchmarkMetrics`: alias for `BenchmarkComparison`.
- `PortfolioBenchmark`: reusable pair of portfolio and benchmark.
- `TrackingErrorEstimate`: heuristic tracking-error result. It stores the total
  estimate and duration, spread, and dispersion components. It can be compared
  with decimals and has `as_decimal()`.

Functions:

- `active_weights`: active holding weights.
- `compare_portfolios`: full comparison.
- `benchmark_comparison`: alias for `compare_portfolios`.
- `estimate_tracking_error`: heuristic estimate from active duration, active
  spread, and active-weight dispersion. It is not a fitted statistical model.

Useful `PortfolioBenchmark` methods:

- `compare(curve, settlement_date)`
- `active_weights(curve, settlement_date)`
- `active_weights_by_holding(curve, settlement_date)`
- `active_weights_by_sector(curve, settlement_date)`
- `active_weights_by_rating(curve, settlement_date)`
- `aggregated_attribution(curve, settlement_date, assumptions=None)`
- `duration_difference_by_sector(curve, settlement_date)`
- `spread_difference_by_sector(curve, settlement_date)`
- `overweight_underweight_counts(curve, settlement_date)`
- `largest_active_positions(curve, settlement_date, limit=5)`
- `tracking_error_estimate(curve, settlement_date)`

```python
from fuggers_py.portfolio import (
    PortfolioBenchmark,
    active_weights,
    compare_portfolios,
    estimate_tracking_error,
)

comparison = compare_portfolios(
    portfolio,
    benchmark_portfolio,
    curve,
    settlement_date,
)
print(comparison.active_duration)
print(comparison.sector_active_weights.to_dict())

weights = active_weights(
    portfolio,
    benchmark_portfolio,
    curve,
    settlement_date,
)
for name, active_weight in weights.items():
    print(name, active_weight)

pair = PortfolioBenchmark(portfolio, benchmark_portfolio)
print(pair.largest_active_positions(curve, settlement_date, limit=3))
print(pair.overweight_underweight_counts(curve, settlement_date))

tracking = estimate_tracking_error(pair, curve, settlement_date)
print(tracking.as_decimal())
print(tracking.duration_component)
```

## Contribution And Attribution

Contribution helpers split portfolio values back to holdings or sectors.
Attribution helpers estimate return pieces from income, rate moves, and spread
moves.

The active convention is portfolio minus benchmark. Rate and spread return
estimates use this first-order formula:

- rate return: `-(portfolio DV01 * rate_change_bps) / dirty PV`
- spread return: `-(portfolio CS01 * spread_change_bps) / dirty PV`

Records:

- `Contribution`: wrapper for portfolio contribution helpers.
- `HoldingContribution`: one holding contribution. Properties include
  `contribution`, `duration_contribution`, `dv01_contribution`,
  `spread_contribution`, and `cs01_contribution`. It supports `as_dict()` and
  key lookup.
- `DurationContributions`: sequence of `HoldingContribution` records with
  `total`.
- `Dv01Contributions`: sequence of `HoldingContribution` records with `total`.
- `Cs01Contributions`: sequence of `HoldingContribution` records with `total`.
- `SpreadContributions`: alias for `Cs01Contributions`.
- `HoldingAttribution`: holding-level PV percent, DV01 percent, and duration
  contribution. It supports `as_dict()` and key lookup.
- `PortfolioAttribution`: sequence of `HoldingAttribution` records. It stores
  total PV percent, total DV01 percent, total duration contribution, and
  supports `by_name(name)`.
- `AttributionInput`: income horizon in years, rate shock in basis points, and
  spread shock in basis points. It converts values to `Decimal` and raises
  `ValueError` when `income_horizon_years` is negative. Its `aggregate()` method
  calls aggregated attribution.
- `BucketContribution`: portfolio value, benchmark value, active value, and
  weights for one bucket. `value` returns `active_value`.
- `SectorAttribution`: mapping from sector name to `BucketContribution`. It
  supports `keys()`, `values()`, `items()`, `by_name()`, and `total_active`.
- `AggregatedAttribution`: income, rate, spread, and total return estimates.
  When a benchmark is provided, benchmark and active fields are also populated.
  `from_portfolios()` is a constructor helper.

Functions:

- `duration_contributions`: holding duration contributions weighted by dirty PV.
- `dv01_contributions`: holding DV01 contributions.
- `spread_contributions`: holding CS01 contributions.
- `cs01_contributions`: alias for `spread_contributions`.
- `top_contributors`: sorts contribution records or dictionaries by a selected
  value key.
- `attribution_summary`: holding-level PV and DV01 attribution.
- `calculate_attribution`: alias for `attribution_summary`.
- `estimate_income_returns`: current yield times horizon.
- `estimate_rate_returns`: first-order rate return estimate.
- `estimate_spread_returns`: first-order spread return estimate.
- `duration_difference_by_sector`: sector duration difference versus benchmark.
- `spread_difference_by_sector`: sector spread difference versus benchmark.
- `aggregated_attribution`: combined income, rate, and spread attribution.

Useful `Contribution` methods:

- `by_position(curve, settlement_date)`
- `aggregate(curve, settlement_date, assumptions=None)`

```python
from decimal import Decimal

from fuggers_py.portfolio import (
    AttributionInput,
    Contribution,
    aggregated_attribution,
    attribution_summary,
    duration_contributions,
    dv01_contributions,
    estimate_rate_returns,
    top_contributors,
)

duration = duration_contributions(
    portfolio,
    curve=curve,
    settlement_date=settlement_date,
)
print(duration.total)
print(duration.by_name("EXAMPLE 5.00 2030"))

dv01 = dv01_contributions(
    portfolio,
    curve=curve,
    settlement_date=settlement_date,
)
leaders = top_contributors(
    dv01,
    value_key="dv01_contribution",
    limit=3,
    absolute=True,
)
for item in leaders:
    print(item.as_dict())

summary = attribution_summary(
    portfolio,
    curve=curve,
    settlement_date=settlement_date,
)
print(summary.total_pv_pct)
print(summary.by_name("EXAMPLE 5.00 2030"))

assumptions = AttributionInput(
    income_horizon_years=Decimal("1"),
    rate_change_bps=Decimal("25"),
    spread_change_bps=Decimal("50"),
)
aggregate = aggregated_attribution(
    portfolio,
    curve=curve,
    settlement_date=settlement_date,
    assumptions=assumptions,
    benchmark=benchmark_portfolio,
)
print(aggregate.active_total_return)

wrapper = Contribution(portfolio)
print(wrapper.aggregate(curve, settlement_date, assumptions=assumptions).total_return)

rate_return = estimate_rate_returns(
    portfolio,
    curve=curve,
    settlement_date=settlement_date,
    rate_change_bps=Decimal("10"),
)
print(rate_return)
```

## ETF Workflows

ETF helpers build basket summaries, NAV metrics, premium/discount metrics,
SEC-yield records, and simple compliance checks.

### Basket Records

- `BasketAnalysis`: high-level basket summary with number of positions, sector
  counts, and total quantity. `security_count` returns `num_positions`.
- `BasketComponent`: one security in a creation basket.
- `BasketFlowSummary`: security value, dirty value, accrued interest, cash,
  liabilities, total basket value, shares outstanding, and creation-unit shares.
  `basket_per_share` returns total basket value divided by creation-unit
  shares, or zero when creation-unit shares are zero.
- `CreationBasket`: ordered sequence of `BasketComponent` records plus a flow
  summary. It supports iteration, `len()`, indexing, `by_name(name)`,
  `component_count`, and `basket_per_share`.

Functions:

- `analyze_etf_basket`: counts portfolio positions, sector counts, and total
  quantity.
- `build_creation_basket`: importable from `fuggers_py.portfolio` today, but
  not listed in `__all__` or the JSON public contract. It scales portfolio
  holdings to a requested creation-unit share count and requires positive
  `shares_outstanding` and `creation_unit_shares`.

```python
from decimal import Decimal

from fuggers_py.portfolio import analyze_etf_basket, build_creation_basket

analysis = analyze_etf_basket(portfolio)
print(analysis.security_count)
print(analysis.sector_counts)

basket = build_creation_basket(
    portfolio,
    curve=curve,
    settlement_date=settlement_date,
    shares_outstanding=Decimal("1000000"),
    creation_unit_shares=Decimal("50000"),
)

print(basket.component_count)
print(basket.basket_per_share)

component = basket.by_name("EXAMPLE 5.00 2030")
if component is not None:
    print(component.quantity, component.weight)
```

### NAV And Premium/Discount

Records:

- `EtfNavMetrics`: total NAV, shares outstanding, NAV per share, DV01 per
  share, CS01 per share, security value, cash value, accrued interest,
  liabilities, optional iNAV, optional market price, and optional
  premium/discount fields.
- `PremiumDiscountStats`: raw premium/discount, basis points, and percentage
  points. `premium_discount_dollars` returns the raw premium/discount field.
  `is_premium` and `is_discount` show the sign.
- `PremiumDiscountPoint`: NAV, market price, shares, premium/discount, edge,
  direction, and action flag. `premium_discount_pct` and
  `premium_discount_bps` delegate to `PremiumDiscountStats`.

Useful `EtfNavMetrics` members:

- `premium_discount_pct`
- `premium_discount_bps`
- `is_premium()`
- `is_discount()`
- `abs_premium_discount()`

Functions:

- `calculate_etf_nav`: NAV per share.
- `calculate_inav`: indicative NAV per share.
- `calculate_etf_nav_metrics`: full NAV record.
- `dv01_per_share`: DV01 divided by shares outstanding.
- `cs01_per_share`: CS01 divided by shares outstanding.
- `premium_discount_stats`: premium/discount relative to NAV.
- `premium_discount`: alias for `premium_discount_stats`.
- `arbitrage_opportunity`: compares market price with NAV after transaction
  cost in basis points. Direction is `create`, `redeem`, or `none`.

`shares_outstanding` must be positive. `premium_discount_stats` requires
positive NAV. `transaction_cost_bps` cannot be negative.

```python
from decimal import Decimal

from fuggers_py.portfolio import (
    arbitrage_opportunity,
    calculate_etf_nav_metrics,
    premium_discount_stats,
)

nav = calculate_etf_nav_metrics(
    portfolio,
    curve=curve,
    settlement_date=settlement_date,
    shares_outstanding=Decimal("1000000"),
    liabilities=Decimal("10000"),
    market_price=Decimal("99.85"),
)

print(nav.nav_per_share)
print(nav.dv01_per_share)
print(nav.premium_discount_bps)
print(nav.is_discount())

stats = premium_discount_stats(
    nav=Decimal("100.00"),
    market_price=Decimal("99.85"),
)
print(stats.is_discount)
print(stats.premium_discount_bps)

arb = arbitrage_opportunity(
    portfolio,
    curve=curve,
    settlement_date=settlement_date,
    shares_outstanding=Decimal("1000000"),
    market_price=Decimal("99.85"),
    transaction_cost_bps=Decimal("2"),
)
print(arb.direction, arb.is_actionable)
```

### SEC Yield, Distribution Yield, Expenses, And Compliance

Records:

- `SecYieldInput`: inputs for standardized SEC-yield calculation.
- `SecYield`: standardized SEC-yield result. `fee_waiver_impact()` returns
  subsidized yield minus unsubsidized yield when both are available.
- `DistributionYield`: distribution yield as raw decimal, percentage points,
  and basis points. `yield_pct` returns `distribution_yield_pct`. It also
  delegates numeric operations to the raw decimal value.
- `ExpenseMetrics`: gross yield, net yield, expense ratios, fee waiver ratio,
  annual income estimate, annual expense amount, and net assets. Properties
  `expense_drag`, `yield_before_expenses`, and `yield_after_expenses` return
  the main yield pieces.
- `ComplianceSeverity`: `INFO`, `WARNING`, or `CRITICAL`.
- `ComplianceCheck`: one named compliance check.
- `EtfComplianceReport`: weight and issuer-limit checks. `passed` is true only
  when all checks pass. `by_name(name)` returns a check by name.

Functions:

- `calculate_sec_yield(SecYieldInput(...))`: returns a `SecYield` record.
- `calculate_sec_yield(net_investment_income, net_assets)`: legacy call form.
  It returns a raw decimal and emits a deprecation warning.
- `approximate_sec_yield`: historical approximation as a raw decimal.
- `calculate_distribution_yield`: annual distribution divided by market price.
- `estimate_yield_from_holdings`: estimates gross and net yield from portfolio
  YTM and expense ratios.
- `etf_compliance_checks`: checks whether weights sum to one and whether the
  largest issuer weight is at or below the fixed 25% limit.

Validation:

- SEC-yield average shares and maximum offering price must be positive.
- Approximate SEC-yield net assets must be positive.
- Distribution-yield market price must be positive.
- Gross expense ratio and fee waiver ratio cannot be negative.
- Issuer weight cannot be negative.
- Weight sum passes when it is within `0.0001` of one.

```python
from decimal import Decimal

from fuggers_py.portfolio import (
    SecYieldInput,
    calculate_distribution_yield,
    calculate_sec_yield,
    estimate_yield_from_holdings,
    etf_compliance_checks,
)

sec_input = SecYieldInput(
    net_investment_income=Decimal("250000"),
    average_shares_outstanding=Decimal("1000000"),
    max_offering_price=Decimal("100"),
    fee_waivers=Decimal("10000"),
)
sec_yield = calculate_sec_yield(sec_input)
print(sec_yield.sec_30_day_yield)
print(sec_yield.fee_waiver_impact())

distribution = calculate_distribution_yield(
    annual_distribution=Decimal("4.80"),
    market_price=Decimal("100"),
)
print(distribution.distribution_yield)
print(distribution.yield_pct)

expenses = estimate_yield_from_holdings(
    portfolio,
    curve=curve,
    settlement_date=settlement_date,
    gross_expense_ratio=Decimal("0.0040"),
    fee_waiver_ratio=Decimal("0.0010"),
)
print(expenses.expense_drag)
print(expenses.yield_after_expenses)

report = etf_compliance_checks(
    holdings_weight_sum=Decimal("1.0000"),
    max_issuer_weight=Decimal("0.20"),
)
print(report.passed)
print(report.by_name("issuer_limit_ok").severity)
```

### Quote-Output ETF Pricing

`EtfPricer` aggregates `EtfHolding` rows and `BondQuoteOutput` records into an
`EtfAnalyticsOutput`. It skips holdings without quotes, prices, or quantities.
It value-weights duration, convexity, and spreads by dirty value. `price()`
returns NAV, iNAV, per-share risk, counts, and weighted risk fields.

```python
from decimal import Decimal

from fuggers_py.portfolio import EtfPricer

etf_output = EtfPricer().price(
    etf_id="etf:demo",
    holdings=etf_holdings,
    quote_outputs=quote_outputs,
    shares_outstanding=Decimal("1000000"),
)

print(etf_output.nav)
print(etf_output.fully_priced)
```

## Stress

Stress helpers apply rate, spread, or tenor-specific shocks to portfolio
analytics and return dirty-PV changes.

Records and aliases:

- `StressScenario`: base named scenario.
- `RateShockScenario`: parallel rate shock in basis points.
- `RateScenario`: alias for `RateShockScenario`.
- `SpreadShockScenario`: parallel spread shock in basis points.
- `SpreadScenario`: alias for `SpreadShockScenario`.
- `TenorShift`: one tenor and one shock in basis points.
- `KeyRateShiftScenario`: name plus tenor-to-shock mapping. `tenor_shifts`
  returns typed `TenorShift` records. `from_tenor_shifts()` builds a scenario
  from typed shifts.
- `StressSummary`: mapping from scenario name to `StressResult`. It supports
  `from_results()`, `scenario_count`, `aggregate_change`, `worst_loss`,
  `best_gain`, `best_case()`, and `worst_case()`.
- `Stress`: wrapper with `parallel_shift(curve, settlement_date, bump_bps=...)`.

Functions:

- `rate_shock_impact`: typed result for a parallel rate shock.
- `parallel_shift_impact`: alias for `rate_shock_impact`.
- `spread_shock_impact`: decimal dirty-PV change for a spread shock.
- `spread_shock_result`: typed result for a spread shock.
- `key_rate_shift_impact`: decimal dirty-PV change for tenor shocks.
- `key_rate_shift_result`: typed result for tenor shocks.
- `run_stress_scenario`: runs one scenario and raises `TypeError` for
  unsupported scenario types.
- `run_stress_scenarios`: runs supported scenarios and returns `StressSummary`.
- `stress_scenarios`: alias for `run_stress_scenarios`.
- `standard_scenarios`: returns the package standard scenarios.
- `summarize_results`: normalizes mappings or iterables into `StressSummary`.
- `best_case`: best result from a result collection.
- `worst_case`: worst result from a result collection.

For rate and spread shocks, positive `bump_bps` usually produces a negative PV
change when the portfolio has positive DV01 or CS01.

```python
from decimal import Decimal

from fuggers_py.portfolio import (
    KeyRateShiftScenario,
    RateShockScenario,
    SpreadShockScenario,
    Stress,
    TenorShift,
    run_stress_scenario,
    run_stress_scenarios,
    standard_scenarios,
)

rate_up = RateShockScenario(
    name="+25 bps rates",
    bump_bps=Decimal("25"),
)
result = run_stress_scenario(
    portfolio,
    curve=curve,
    settlement_date=settlement_date,
    scenario=rate_up,
)
print(result.actual_change)
print(result.pv_change)

key_rate = KeyRateShiftScenario.from_tenor_shifts(
    name="curve twist",
    shifts=[
        TenorShift("2Y", Decimal("-10")),
        TenorShift("10Y", Decimal("15")),
    ],
)

summary = run_stress_scenarios(
    portfolio,
    curve=curve,
    settlement_date=settlement_date,
    scenarios=[
        rate_up,
        SpreadShockScenario(name="+50 bps spreads", bump_bps=Decimal("50")),
        key_rate,
    ],
)

print(summary.scenario_count)
print(summary.worst_loss)
print(summary.best_case())

wrapper_result = Stress(portfolio).parallel_shift(
    curve,
    settlement_date,
    bump_bps=Decimal("10"),
)
print(wrapper_result.shocked_pv)

for scenario in standard_scenarios():
    print(scenario.name)
```

## Public Submodules

The package exports these module objects for users who prefer grouped imports:

- `analytics`
- `benchmark`
- `bucketing`
- `contribution`
- `etf`
- `liquidity`
- `risk`
- `stress`
- `types`

User code should still prefer one-layer imports from `fuggers_py.portfolio`
unless it has a clear reason to import a submodule.

## Boundaries

- Bond instruments and bond analytics come from `fuggers_py.bonds`.
- Curves come from `fuggers_py.curves`.
- Credit instruments and CDS analytics come from `fuggers_py.credit`.
- Rates instruments come from `fuggers_py.rates`.
- Inflation data and inflation swaps come from `fuggers_py.inflation`.
- Funding trades and financing analytics come from `fuggers_py.funding`.

`portfolio` can depend on these packages because portfolio work combines many
domains. Those packages should not import from `portfolio`.

```{eval-rst}
.. automodule:: fuggers_py.portfolio
   :members:
   :member-order: bysource
```
