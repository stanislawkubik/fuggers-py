:orphan:

# Source Structure

`src/fuggers_py/` is the canonical implementation root for the library.

This page describes the current structure of the repo. It is not a promise
that every boundary is frozen. For the current readiness and pre-`1.0`
stability policy, see [STATUS.md](STATUS.md).

For the complete file-by-file module inventory, see [MODULE_REFERENCE.md](MODULE_REFERENCE.md).

```python
from fuggers_py import (
    adapters,
    calc,
    core,
    market,
    math,
    measures,
    portfolio,
    pricers,
    products,
    reference,
)
from fuggers_py.market.curves import DiscountCurveBuilder
from fuggers_py.products.bonds import FixedBondBuilder
```

## Root package files

- `__init__.py`: top-level package exports and runtime version import.
- `_version.py`: generated version metadata for builds; not handwritten library code.
- `py.typed`: typing marker for downstream users.

## Directory map

### `adapters/`

- External boundaries and persistence layers.
- `file.py`: file-backed loaders, file-backed market-data sources, and no-op output publishers.
- `json_codec.py`: JSON codecs used at the library boundary.
- `storage.py`, `sqlite_storage.py`, `portfolio_store.py`: persistence protocols and concrete stores for curves, config, audits, and portfolios.
- `transport.py`: transport and caching interfaces for remote or deferred IO.

### `calc/`

- Orchestration and runtime wiring.
- `pricing_specs.py` and `output.py`: typed engine inputs and outputs.
- `pricing_router.py`, `rates_pricing_router.py`, `funding_pricing_router.py`: routing from products and market inputs into pricers.
- `curve_builder.py`: runtime curve-building coordination that wraps the curve package for engine use.
- `market_data_listener.py`, `calc_graph.py`, `reactive.py`, `scheduler.py`: reactive runtime, update propagation, and scheduling.
- `builder.py`, `config.py`, `coordination.py`: engine assembly and runtime config or service coordination.

### `core/`

- Shared primitives used everywhere else.
- `types.py`: dates, currencies, prices, yields, spreads, cashflow records, and other shared value objects.
- `ids.py`: canonical identifiers such as `InstrumentId`, `CurveId`, and `VolSurfaceId`.
- `calendars.py` and `daycounts.py`: date adjustment, holiday logic, and accrual conventions.
- `traits.py`: low-level protocols used across pricing and analytics layers.
- `errors.py`: the common exception root and only the truly shared primitive exceptions.

### `market/`

- Dynamic market inputs and runtime market state.
- In this repo, `market` means observed market data and assembled pricing state. It does not mean every finance-related module.
- `quotes.py`: raw and typed market quote records for bonds, swaps, repos, FX, futures, CDS, and related instruments.
- `snapshot.py`: immutable market-data snapshots that bundle curves, fixings, FX rates, ETF records, and volatility surfaces.
- `sources.py`: market-data provider protocols and in-memory source implementations for quotes, curves, fixings, FX, inflation, and ETFs.
- `state.py`: runtime bundles of curves, projection sets, inflation curves, quote side, and optional vol surfaces passed into pricing and measures.
- `indices/`: fixing stores, index conventions, overnight compounding helpers, and bond-index wrappers.
- `curves/`: the full term-structure namespace, including base curve types, calibration, builders, bumping, multicurve, inflation, credit, funding, and fitted-bond tools.
- `vol_surfaces/`: volatility surface records, quote conventions, and in-memory volatility surface sources. This is the canonical volatility namespace now, but it is still an early-scope package rather than a full smile or cube modeling stack.

### `math/`

- Numerical infrastructure.
- `interpolation/` and `extrapolation/`: interpolation schemes and extrapolation policies used by curves and analytics.
- `solvers/`: root finders and generic solver interfaces.
- `optimization/`: lightweight optimizers and fit result records.
- `linear_algebra/`: small linear-algebra helpers used by numerical routines.
- `errors.py`: numerical error hierarchy for convergence, dimensionality, and invalid-input failures.

### `measures/`

- User-facing analytics and report-style calculations.
- `yields/`, `spreads/`, `pricing/`: yield, spread, and price-style desk analytics.
- `risk/`: duration, convexity, hedging, and value-at-risk style helpers.
- `rv/`: relative-value and basis-style analytics.
- `options/`, `credit/`, `funding/`, `inflation/`: domain-specific analytics grouped by product family.
- `cashflows/` and `yas/`: cashflow explainers and Bloomberg-style YAS helpers.
- `functions.py`: thin convenience entrypoints that expose common analytics without importing a whole subpackage.

### `portfolio/`

- Portfolio-level aggregation and workflow code.
- `portfolio.py`: the main portfolio container and builder.
- `types/`: holdings, classifications, rating or sector metadata, stress results, and weighting config records.
- `analytics/` and `risk/`: aggregate portfolio analytics, weighted measures, and portfolio risk summaries.
- `benchmark/`, `bucketing/`, `contribution/`: benchmark comparison, bucketed summaries, and attribution or contribution helpers.
- `etf/`, `liquidity/`, `stress/`: ETF workflows, liquidity analysis, and portfolio scenario or shock analysis.

### `pricers/`

- Low-level valuation and risk engines.
- `bonds/`: bond pricing, accrued-interest logic, bond option models, and bond risk helpers.
- `rates/`: swap, FRA, futures, and rates-option pricers plus curve-resolution helpers and rates risk modules.
- `credit/`: credit default swap pricing and related credit valuation helpers.

### `products/`

- Contract definitions and product-level structures only.
- `bonds/`: fixed, floating, inflation-linked, callable, future, and bond-option product definitions, with cashflow and trait helpers below the package.
- `credit/`: CDS and related credit contract definitions.
- `funding/`: repo and funding contract structures.
- `rates/`: swaps, FRAs, basis structures, inflation-linked rate contracts, and rates futures or options.
- `instruments/`: shared instrument-level wrappers and generic product records used across product families.

### `reference/`

- Reference and convention data.
- `reference_data.py` and `base.py`: shared reference-data records, provider protocols, and resolvable-reference helpers.
- `bonds/`: bond conventions, quote rules, lifecycle metadata, schedules, and type definitions such as `RateIndex` and `Tenor`.
- `inflation/`: inflation-index metadata, lag rules, and related reference helpers.

## Notable subdirectories

### `market/curves/`

- Single home for generic and specialized curve logic.
- Base term-structure types, conversion/value semantics, discrete/derived/forward/delegated/segmented curves, calibration helpers, builders, and specialized curve families.

### `market/indices/`

- Bond-index and fixing-store infrastructure plus overnight index conventions.

### `market/vol_surfaces/`

- Canonical home for volatility surface records, quote conventions, and in-memory surface providers used by option pricers and market snapshots.
- The package is intentionally narrow today. It does not yet cover full volatility fitting, smile modeling, cube construction, or interpolation policy.

### `measures/risk/`

- Rate, spread, convexity, hedging, and value-at-risk analytics split into focused subpackages.

### `pricers/rates/`

- Rates valuation logic, futures and option pricers, risk helpers, and the market-input resolution code that binds curves or vol surfaces into the pricing models.

### `products/rates/`

- Rates contracts, including swaps, FRAs, basis structures, and inflation-swap products.

### `products/bonds/`

- Bond-family contracts, cashflow records, and bond-specific traits or helpers used by pricers and measures.

### `portfolio/types/`

- Portfolio value objects such as holdings, classifications, maturity buckets, and weighting/config helpers.

### `reference/bonds/`

- Static bond conventions, metadata, quote inputs, and type definitions shared across products and analytics.

## Error placement rules

- `core/errors.py` owns `FuggersError` and only the shared primitive exceptions used by core value types, calendars, and day-count logic.
- Package-specific failures live in that package's `errors.py`, or in a public subpackage `errors.py` when the public error boundary is narrower than the package, such as `reference/bonds/errors.py`, `market/curves/errors.py`, and `pricers/bonds/options/errors.py`.
- All library-defined exceptions must subclass `FuggersError`, either directly or through a package-specific root such as `BondError`, `CurvesError`, `MathError`, `AnalyticsError`, or `EngineError`.
- Feature modules raise exceptions imported from their package error module. They should not define new exception classes inline when the package already has an error namespace.
- If a package does not need a stable package-specific error surface, do not add an `errors.py` file just for symmetry.

## Reading order

1. Start with `core/` for shared types and conventions.
2. Read `reference/` for static conventions and `market/` for dynamic market inputs and runtime state.
3. Read `products/` for contracts.
4. Read `pricers/` and `measures/` for calculations.
5. Read `portfolio/` and `calc/` for aggregate workflows and orchestration.
6. Read `adapters/` for file/storage/transport boundaries.
