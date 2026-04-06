# `fuggers_py.market`

Market state, quotes, fixings, indices, and curve abstractions.

Canonical market modules:

- `fuggers_py.market.state`
  - market state helpers such as `QuoteSide` and `AnalyticsCurves`
- `fuggers_py.market.quotes`
  - quote protocols and concrete quote families
- `fuggers_py.market.snapshot`
  - curve inputs, fixings, surfaces, ETF holdings, and `MarketDataSnapshot`
- `fuggers_py.market.sources`
  - source protocols, in-memory sources, and `MarketDataProvider`

```{automodule} fuggers_py.market
:members:
:member-order: bysource
```
