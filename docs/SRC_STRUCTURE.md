# Source Structure

`src/fuggers_py/` is the canonical implementation root for the library.

This page describes the current structure of the repo. It is not a promise
that every boundary is frozen. For the current readiness and pre-`1.0`
stability policy, see [STATUS.md](STATUS.md).

For the current package and directory map, use this page. [MODULE_REFERENCE.md](MODULE_REFERENCE.md) is kept only as an archived note from before the public API cutover.

```python
from fuggers_py import bonds, curves, rates, vol_surfaces
from fuggers_py.bonds import FixedBondBuilder
from fuggers_py.curves import CurveSpec
from fuggers_py.rates import SwapPricer
from fuggers_py.vol_surfaces import VolatilitySurface
```

## Root package files

- `__init__.py`: top-level package exports and runtime version import.
- `_version.py`: generated version metadata for builds; not handwritten library code.
- `py.typed`: typing marker for downstream users.

## Directory map

### `_runtime/`

- Internal runtime helpers.
- `quotes.py`: shared quote plumbing used inside curve fitting and related runtime paths.

### `_storage/`

- Internal storage and boundary helpers.
- This package is the internal home for storage-facing infrastructure that should not sit in the main public story.

### `_adapters/`

- Internal boundary and persistence helpers.
- This package is not public API. It is where the remaining file, storage, transport, and codec helpers now live.
- `file.py`: file-backed loaders, file-backed market-data sources, and no-op output publishers.
- `json_codec.py`: JSON codecs used at the library boundary.
- `storage.py`, `sqlite_storage.py`, `portfolio_store.py`: persistence protocols and concrete stores for market data, config, audits, and portfolios.
- `transport.py`: transport and caching interfaces for remote or deferred IO.

### `_calc/`

- Internal orchestration and runtime wiring.
- This package is not public API. It is the home for engine and scheduling work that should not sit in the main package story.
- `pricing_specs.py` and `output.py`: typed engine inputs and outputs.
- `pricing_router.py`: routing from product and market inputs into pricers.
- `market_data_listener.py`, `calc_graph.py`, `reactive.py`, `scheduler.py`: reactive runtime, update propagation, and scheduling.
- `builder.py`, `config.py`, `coordination.py`: engine assembly and runtime config or service coordination.

### `_core/`

- Internal shared primitives used everywhere else.
- This package is not public API. The `fuggers_py` root re-exports the selected shared names that users should import.
- `types.py`: dates, currencies, prices, yields, spreads, cashflow records, and other shared value objects.
- `ids.py`: canonical identifiers such as `InstrumentId`, `PortfolioId`, and `VolSurfaceId`.
- `calendars.py` and `daycounts.py`: date adjustment, holiday logic, and accrual conventions.
- `traits.py`: low-level protocols used across pricing and analytics layers.
- `errors.py`: the common exception root and only the truly shared primitive exceptions.

### `bonds/`

- First-layer public home for bond instruments, quotes, pricing, risk, spreads, yields, and YAS-style bond analytics.
- `products.py`, `quotes.py`, `pricing.py`, `risk.py`, `spreads.py`, `yields.py`, and `yas.py`: the domain bundles that feed the one-layer `fuggers_py.bonds` surface.

### `rates/`

- First-layer public home for swaps, basis structures, FRA, futures, swaptions, cap or floor products, rates quotes, fixing storage, and rates pricing or risk helpers.
- `products.py`, `quotes.py`, `pricing.py`, and `indices.py`: the domain bundles that feed the one-layer `fuggers_py.rates` surface.

### `inflation/`

- First-layer public home for CPI history, reference CPI helpers, index-ratio helpers, inflation swaps, and inflation analytics.
- `reference.py` and `analytics.py`: the domain bundles that feed the one-layer `fuggers_py.inflation` surface.

### `credit/`

- First-layer public home for CDS instruments, CDS quotes, CDS pricing, and bond-CDS basis analytics.
- `products.py`, `quotes.py`, `pricing.py`, and `analytics.py`: the domain bundles that feed the one-layer `fuggers_py.credit` surface.

### `funding/`

- First-layer public home for repo trades, repo or haircut quotes, implied repo, and financing analytics.
- `products.py`, `quotes.py`, and `analytics.py`: the domain bundles that feed the one-layer `fuggers_py.funding` surface.

### `_market/`

- Internal market inputs and runtime market state.
- In this repo, `market` means observed market data and assembled pricing state. This package is not public API anymore.
- `curve_support.py`: internal market-state helpers. The date-based curve bridge now lives under `curves/date_support.py`.
- `snapshot.py`: immutable market-data snapshots that bundle fixings, raw quote records, FX rates, ETF records, and volatility surfaces. Typed instrument quotes now live with their first-layer domain modules instead of under the old public `market` namespace.
- `sources.py`: market-data provider protocols and in-memory source implementations for quotes, fixings, FX, inflation, and ETFs.
- `state.py`: runtime market-state bundles passed into pricing and analytics. The main discounting-style curve slots are now typed to the public curve contracts instead of plain `object`.
- `indices/`: fixing stores, index conventions, overnight compounding helpers, and bond-index wrappers.
- Curve and volatility-surface implementation no longer lives in a public market namespace. Curve internals now live directly under `curves/`, and the volatility-surface records now live directly under `vol_surfaces/`.

### `_math/`

- Internal numerical infrastructure.
- This package is not public API. Domain modules and `curves` depend on it for shared numerical routines.
- `interpolation/` and `extrapolation/`: interpolation schemes and extrapolation policies used by numerical routines across the library.
- `solvers/`: root finders and generic solver interfaces.
- `optimization/`: lightweight optimizers and fit result records.
- `linear_algebra/`: small linear-algebra helpers used by numerical routines.
- `errors.py`: numerical error hierarchy for convergence, dimensionality, and invalid-input failures.

### `_measures/`

- Internal analytics and report-style calculations.
- This package is not public API. Domain-first packages such as `fuggers_py.bonds` and `fuggers_py.credit` are the public homes for these analytics.
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

### `_pricers/`

- Internal valuation and risk engines.
- This package is not public API. Public pricing entrypoints now sit with the owning domains.
- `bonds/`: bond pricing, accrued-interest logic, bond option models, and bond risk helpers.
- `rates/`: swap, FRA, futures, and rates-option pricers plus rates risk modules.
- `credit/`: credit default swap pricing and related credit valuation helpers.

### `_products/`

- Internal contract definitions and product-level structures.
- This package is not public API. The public homes are the first-layer domain modules.
- `bonds/`: fixed, floating, inflation-linked, callable, future, and bond-option product definitions, with cashflow and trait helpers below the package.
- `credit/`: CDS and related credit contract definitions.
- `funding/`: repo and funding contract structures.
- `rates/`: swaps, FRAs, basis structures, inflation-linked rate contracts, and rates futures or options.
- `instruments/`: shared instrument-level wrappers and generic product records used across product families.

### `_reference/`

- Internal reference and convention data.
- This package is not public API. Shared language that users should import now comes from `fuggers_py` root or from the owning first-layer domain modules.
- `reference_data.py` and `base.py`: shared reference-data records, provider protocols, and resolvable-reference helpers.
- `bonds/`: bond conventions, quote rules, lifecycle metadata, schedules, and type definitions such as `RateIndex` and `Tenor`.
- `inflation/`: inflation-index metadata, lag rules, and related reference helpers.

## Notable subdirectories

### `_market/indices/`

- Bond-index and fixing-store infrastructure plus overnight index conventions.

### `curves/`

- First-layer public home for fitted curve objects.
- Read [docs/api/curves.md](api/curves.md) for the public curve story.
- The public surface starts with `RatesTermStructure`, `DiscountingCurve`, `YieldCurve`, and `RelativeRateCurve`.
- `CurveSpec`, `KernelSpec`, and `CalibrationSpec` are the main curve config records exposed from this package.
- `CalibrationReport` and `GlobalFitReport` are the current public fit-report records.
- Domain quotes still come from their owning modules, such as `fuggers_py.bonds` and `fuggers_py.rates`.
- `date_support.py` carries the date-based bridge helpers used by bond and portfolio code that still price from dates.
- `base.py`, `spec.py`, `enums.py`, `reports.py`, `conversion.py`, `calibrators/`, `kernels/`, and `multicurve/` are the live curve implementation files.

### `vol_surfaces/`

- First-layer public home for volatility surface records and surface source protocols.
- Read [docs/api/vol_surfaces.md](api/vol_surfaces.md) for the public surface story.
- `VolatilitySurface`, `VolPoint`, `VolQuoteType`, and `VolSurfaceType` are the current public surface records.
- `VolatilitySource` and `InMemoryVolatilitySource` are the current public source interfaces.
- The package is intentionally small today. It does not yet cover full smile fitting or cube construction.
- `surface.py` and `sources.py` are the live implementation files.

### `_measures/risk/`

- Rate, spread, convexity, hedging, and value-at-risk analytics split into focused subpackages.

### `_pricers/rates/`

- Rates valuation logic, futures and option pricers, risk helpers, and the market-input resolution code that binds market state into the pricing models.

### `_products/rates/`

- Rates contracts, including swaps, FRAs, basis structures, and inflation-swap products.

### `_products/bonds/`

- Bond-family contracts, cashflow records, and bond-specific traits or helpers used by pricers and measures.

### `portfolio/types/`

- Portfolio value objects such as holdings, classifications, maturity buckets, and weighting/config helpers.

### `_reference/bonds/`

- Static bond conventions, metadata, quote inputs, and type definitions shared across products and analytics.

## Error placement rules

- `_core/errors.py` owns `FuggersError` and only the shared primitive exceptions used by core value types, calendars, and day-count logic.
- Package-specific failures live in that package's `errors.py`, or in a focused subpackage `errors.py` when the error boundary is narrower than the package, such as `_reference/bonds/errors.py`, `_math/errors.py`, and `_pricers/bonds/options/errors.py`.
- All library-defined exceptions must subclass `FuggersError`, either directly or through a package-specific root such as `BondError`, `MathError`, `AnalyticsError`, or `EngineError`.
- Feature modules raise exceptions imported from their package error module. They should not define new exception classes inline when the package already has an error namespace.
- If a package does not need a stable package-specific error surface, do not add an `errors.py` file just for symmetry.

## Reading order

1. Start with `_core/` for shared types and conventions.
2. Read the first-layer public packages `bonds/`, `rates/`, `inflation/`, `credit/`, `funding/`, `curves/`, `vol_surfaces/`, and `portfolio/`.
3. Read `_market/` for dynamic market inputs and runtime state.
4. Read `_products/`, `_pricers/`, `_measures/`, and `_reference/` when you need implementation details behind the public surface.
5. Read `_math/`, `_calc/`, and `_adapters/` only when you are working on numerical internals, engine wiring, persistence, or transport details. They are internal infrastructure layers, not the main user-facing story.
