# Source Structure

`src/fuggers_py/` is the canonical implementation root for the library.

This page describes the current structure of the repo. It is not a promise
that every boundary is frozen. For the current readiness and pre-`1.0`
stability policy, see [STATUS.md](STATUS.md).

For the current package and directory map, use this page. [MODULE_REFERENCE.md](MODULE_REFERENCE.md) is kept only as an archived note from before the public API cutover.

```python
from fuggers_py import bonds, curves, portfolio, rates, vol_surfaces
from fuggers_py.bonds import FixedBondBuilder
from fuggers_py.curves import CurveSpec
from fuggers_py.portfolio import Portfolio
from fuggers_py.rates import SwapPricer
from fuggers_py.vol_surfaces import VolatilitySurface
```

## Root package files

- `__init__.py`: top-level package exports and runtime version import.
- `_version.py`: generated version metadata for builds; not handwritten library code.
- `py.typed`: typing marker for downstream users.

## Directory map

### `_runtime/`

- Internal runtime orchestration and market input records.
- This package is not public API. It owns engine assembly, scheduling,
  reactive execution, market-data listeners, routing, and typed runtime inputs
  or outputs.
- `builder.py`, `config.py`, and `coordination.py`: engine assembly, runtime
  config, and service coordination.
- `calc_graph.py`, `reactive.py`, and `scheduler.py`: dependency tracking,
  update propagation, and scheduling.
- `pricing_specs.py`, `pricing_router.py`, and `output.py`: typed engine
  requests, pricing routing, and output records or publishers.
- `quotes.py`, `snapshot.py`, `sources.py`, and `state.py`: shared quote
  records, market-data snapshots, source protocols, and runtime market state.

### `_storage/`

- Internal storage, file, transport, and codec helpers.
- This package is not public API. It is the internal home for storage-facing
  infrastructure that should not sit in the main public story.
- `file.py`: file-backed loaders, file-backed market-data sources, and no-op output publishers.
- `json_codec.py`: JSON codecs used at the library boundary.
- `storage.py`, `sqlite_storage.py`, `portfolio_store.py`: persistence protocols and concrete stores for market data, config, audits, and portfolios.
- `transport.py`: transport and caching interfaces for remote or deferred IO.

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
- `types/`: bond-local type records such as identifiers, quote conventions,
  rating or sector metadata, embedded-option schedules, and amortization
  schedules.
- `instruments/`, `cashflows/`, `options/`, `conventions/`, and `rv/`: bond
  implementation subpackages used behind the public `fuggers_py.bonds`
  surface.

### `rates/`

- First-layer public home for swaps, basis structures, FRA, futures, swaptions, cap or floor products, rates quotes, fixing storage, and rates pricing or risk helpers.
- `products.py`, `quotes.py`, `pricing.py`, and `indices.py`: the domain bundles that feed the one-layer `fuggers_py.rates` surface.

### `inflation/`

- First-layer public home for CPI history, reference CPI helpers, index-ratio helpers, inflation swaps, and inflation analytics.
- `conventions.py`, `history.py`, `reference.py`, `swaps.py`, `pricing.py`, and `analytics.py`: the domain bundles that feed the one-layer `fuggers_py.inflation` surface.

### `credit/`

- First-layer public home for CDS instruments, CDS quotes, CDS pricing, and bond-CDS basis analytics.
- `instruments.py`, `quotes.py`, `pricing.py`, `risk.py`, and `analytics.py`: the domain bundles that feed the one-layer `fuggers_py.credit` surface.

### `funding/`

- First-layer public home for repo trades, repo or haircut quotes, implied repo, and financing analytics.
- `products.py`, `quotes.py`, and `analytics.py`: the domain bundles that feed the one-layer `fuggers_py.funding` surface.

### `_math/`

- Internal numerical infrastructure.
- This package is not public API. Domain modules and `curves` depend on it for shared numerical routines.
- `interpolation/` and `extrapolation/`: interpolation schemes and extrapolation policies used by numerical routines across the library.
- `solvers/`: root finders and generic solver interfaces.
- `optimization/`: lightweight optimizers and fit result records.
- `linear_algebra/`: small linear-algebra helpers used by numerical routines.
- `errors.py`: numerical error hierarchy for convergence, dimensionality, and invalid-input failures.

### `portfolio/`

- First-layer public home for portfolio containers, holdings, portfolio
  analytics, benchmark comparison, contribution and attribution, bucketing,
  stress results, and ETF workflows.
- `portfolio.py`: the main portfolio container and builder.
- `types/`: holdings, classifications, rating or sector metadata, stress results, and weighting config records.
- `analytics/` and `risk/`: aggregate portfolio analytics, weighted measures, and portfolio risk summaries.
- `benchmark/`, `bucketing/`, `contribution/`: benchmark comparison, bucketed summaries, and attribution or contribution helpers.
- `etf/`, `liquidity/`, `stress/`: ETF workflows, liquidity analysis, and portfolio scenario or shock analysis.
- Portfolio may combine objects from the other first-layer public packages, such
  as `bonds`, `curves`, `credit`, `rates`, `inflation`, `funding`, and
  `vol_surfaces`.
- Other first-layer public packages should not import from `portfolio`.

## Notable subdirectories

### `rates/indices.py`

- Bond-index and fixing-store infrastructure plus overnight index conventions.

### `curves/`

- First-layer public home for fitted curve objects.
- Read [docs/api/curves.md](api/curves.md) for the public curve story.
- The public surface is `CurveSpec`, `YieldCurve`, `RatesTermStructure`,
  `DiscountingCurve`, `CalibrationReport`, `CalibrationPoint`,
  and `STANDARD_KEY_RATE_TENORS`.
- Curve moves live as `DiscountingCurve.shifted(...)` and
  `DiscountingCurve.bumped(...)`.
- Advanced fit controls such as `KernelSpec` and `CalibrationSpec` live in the
  `curves.kernels` and `curves.calibrators` submodules.
- `CalibrationReport` is the single public fit-report record.
- Domain quotes still come from their owning modules, such as `fuggers_py.bonds` and `fuggers_py.rates`.
- `curves/date_support.py` carries the date-based bridge helpers used by bond and portfolio code that still price from dates.
- `base.py`, `spec.py`, `reports.py`, `conversion.py`, `movements.py`,
  `calibrators/`, `kernels/`, and `multicurve/` are the live curve
  implementation files.

### `vol_surfaces/`

- First-layer public home for volatility surface records and surface source protocols.
- Read [docs/api/vol_surfaces.md](api/vol_surfaces.md) for the public surface story.
- `VolatilitySurface`, `VolPoint`, `VolQuoteType`, `VolSurfaceType`, and `VolSurfaceSourceType` are the current public surface records.
- `VolatilitySource` and `InMemoryVolatilitySource` are the current public source interfaces.
- The package is intentionally small today. It does not yet cover full smile fitting or cube construction.
- `surface.py` and `sources.py` are the live implementation files.

### `rates/`

- Rates contracts, quotes, futures, options, valuation helpers, risk helpers, and index/fixing support.
- Inflation-swap products and pricing live under `fuggers_py.inflation`.

### `portfolio/types/`

- Portfolio value objects such as holdings, classifications, maturity buckets, and weighting/config helpers.

## Error placement rules

- `_core/errors.py` owns `FuggersError` and only the shared primitive exceptions used by core value types, calendars, and day-count logic.
- Package-specific failures live in that package's `errors.py`, or in a focused subpackage `errors.py` when the error boundary is narrower than the package, such as `_math/errors.py` or `bonds/options/errors.py`.
- All library-defined exceptions must subclass `FuggersError`, either directly or through a package-specific root such as `BondError`, `MathError`, `AnalyticsError`, or `EngineError`.
- Feature modules raise exceptions imported from their package error module. They should not define new exception classes inline when the package already has an error namespace.
- If a package does not need a stable package-specific error surface, do not add an `errors.py` file just for symmetry.

## Reading order

1. Start with `_core/` for shared types and conventions.
2. Read the first-layer public packages `bonds/`, `rates/`, `inflation/`, `credit/`, `funding/`, `curves/`, `vol_surfaces/`, and `portfolio/`.
3. Read internal infrastructure only when you are changing implementation
   details. These folders are not the user-facing import story.
