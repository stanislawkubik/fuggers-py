# Source Structure

`src/fuggers_py/` is the canonical implementation root for the library.

This page describes the current structure of the repo. It is not a promise
that every boundary is frozen. For the current readiness and pre-`1.0`
stability policy, see [STATUS.md](STATUS.md).

For the complete file-by-file module inventory, see [MODULE_REFERENCE.md](MODULE_REFERENCE.md).

```python
import fuggers_py
from fuggers_py import core, market, products
from fuggers_py.market.curves import CurveSpec
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
- `storage.py`, `sqlite_storage.py`, `portfolio_store.py`: persistence protocols and concrete stores for market data, config, audits, and portfolios.
- `transport.py`: transport and caching interfaces for remote or deferred IO.

### `calc/`

- Orchestration and runtime wiring.
- `pricing_specs.py` and `output.py`: typed engine inputs and outputs.
- `pricing_router.py`: routing from products and market inputs into pricers.
- `market_data_listener.py`, `calc_graph.py`, `reactive.py`, `scheduler.py`: reactive runtime, update propagation, and scheduling.
- `builder.py`, `config.py`, `coordination.py`: engine assembly and runtime config or service coordination.

### `core/`

- Shared primitives used everywhere else.
- `types.py`: dates, currencies, prices, yields, spreads, cashflow records, and other shared value objects.
- `ids.py`: canonical identifiers such as `InstrumentId`, `PortfolioId`, and `VolSurfaceId`.
- `calendars.py` and `daycounts.py`: date adjustment, holiday logic, and accrual conventions.
- `traits.py`: low-level protocols used across pricing and analytics layers.
- `errors.py`: the common exception root and only the truly shared primitive exceptions.

### `market/`

- Dynamic market inputs and runtime market state.
- In this repo, `market` means observed market data and assembled pricing state. It does not mean every finance-related module.
- `curve_support.py`: bridge helpers for date-based pricing code that now needs to consume the tenor-based public curve contract without changing `market.curves` again. It no longer exports a public curve-wrapper type; the only wrapper left there is a private scenario helper used by risk code.
- `quotes.py`: raw and typed market quote records for bonds, swaps, repos, FX, futures, CDS, and related instruments.
- `snapshot.py`: immutable market-data snapshots that bundle fixings, FX rates, ETF records, and volatility surfaces.
- `sources.py`: market-data provider protocols and in-memory source implementations for quotes, fixings, FX, inflation, and ETFs.
- `state.py`: runtime market-state bundles passed into pricing and measures. The main discounting-style curve slots are now typed to the public curve contracts instead of plain `object`.
- `curves/`: the current rates curve skeleton. The root package now exports `CurveSpec`, `CurveType`, `ExtrapolationPolicy`, `RateSpace`, `RatesTermStructure`, `DiscountingCurve`, `YieldCurve`, and `RelativeRateCurve`. `rates/__init__.py` now re-exports the public construction and report vocabulary needed by `YieldCurve.fit(...)`: `CurveKernelKind`, `KernelSpec`, `CalibrationMode`, `CalibrationObjective`, `BondFitTarget`, `CalibrationSpec`, `GlobalFitOptimizerKind`, `CalibrationReport`, and `GlobalFitReport`, plus `CurveKernel` for the advanced direct constructor path. `rates/spec.py` holds the curve identity record. `rates/base.py` defines the public roots: `rate_at(tenor)` returns the rate at a tenor in the curve's `rate_space`, `max_t()` gives the last supported tenor, and `validate_rate(tenor)` enforces the domain and finite-value rules. `DiscountingCurve` adds `discount_factor_at(tenor)`, `zero_rate_at(tenor)`, and `forward_rate_between(start_tenor, end_tenor)`. `YieldCurve` is now the concrete public discounting object: it wraps one internal kernel, fixes its public `rate_space` to `RateSpace.ZERO`, exposes the public zero-rate view through `rate_at(tenor)`, and now also provides `fit(quotes, spec=..., kernel_spec=..., calibration_spec=...)` as the shared public construction path for the live fitting methods. `rates/reports.py` now holds `CalibrationPoint`, `CalibrationReport`, `GlobalFitPoint`, and `GlobalFitReport`. `rates/kernels/base.py` now defines the shared internal kernel vocabulary: `CurveKernelKind`, `KernelSpec`, and `CurveKernel`. The shared kernel contract is now rate-first: kernels define the fitted rate curve and derive discount factors from it. `rates/kernels/nodes.py` now holds the node-based internal kernel family: linear-zero, log-linear-discount, piecewise-constant-zero, piecewise-flat-forward, and monotone-convex kernels. `rates/kernels/parametric.py` now holds the parametric internal kernel family: `NelsonSiegelKernel` and `SvenssonKernel`, each with an explicit finite `max_t` even though the underlying formulas can evaluate beyond it. `rates/kernels/spline.py` now holds the spline internal kernel family: `ExponentialSplineKernel` and the single production `CubicSplineKernel`, which means a natural cubic spline in zero-rate space on a fixed knot grid with knot zero values as parameters. `rates/calibrators/base.py` defines `BondFitTarget`, `CalibrationMode`, `CalibrationObjective`, `CalibrationSpec`, and `CurveCalibrator`. `CalibrationSpec` is now the single fit-control object for the live routes and for the direct calibrator constructors. `rates/calibrators/bootstrap.py` defines the exact sequential construction path: `BootstrapSolverKind` and `BootstrapCalibrator`. `BootstrapCalibrator` is now only the exact sequential construction route for the local node-style kernels, and it only accepts `CalibrationObjective.EXACT_FIT`. On that route, bond price quotes normalize to bond-implied YTM before exact matching. `rates/calibrators/global_fit.py` defines the imperfect global regression fit path: `GlobalFitOptimizerKind` and `GlobalFitCalibrator`, which fit `CUBIC_SPLINE`, `NELSON_SIEGEL`, `SVENSSON`, and `EXPONENTIAL_SPLINE` from the same quote-driven entry point. `GlobalFitCalibrator` currently only accepts `CalibrationObjective.WEIGHTED_L2`. On that route, bond price quotes stay in price space and use `CalibrationSpec.bond_fit_target`. `BondQuote.regressors` is the quote-level home for time-varying external variables such as `issue_size_bn`, `issue_age_years`, `deliverable_bpv`, and `repo_specialness_bp`. `BondQuote.fit_weight` is the quote-level weight used by `GlobalFitCalibrator` in the weighted-L2 objective. The fitted regressor coefficients in `GlobalFitReport` are additive target-space moves per one unit of the matching regressor, and bond price rows can also carry diagnostic price and YTM residual detail there. For the cubic-spline case, callers provide fixed `knots` in `KernelSpec.parameters`, and the calibrator fits the knot zero values on that fixed grid. That knot grid must be strictly increasing, contain at least three knots, and define valid front-end spacing. For the exponential-spline case, callers provide fixed `decay_factors` in `KernelSpec.parameters`, and the calibrator fits the spline coefficients against those fixed decay factors. `rates/calibrators/_quotes.py` is the private quote-normalization helper for those live fitting paths. `conversion.py` and `errors.py` are shared helpers, and `errors.py` still keeps a small set of legacy builder errors for older code paths. `multicurve/` currently holds identifiers such as `RateIndex` and `CurrencyPair`.
- `indices/`: fixing stores, index conventions, overnight compounding helpers, and bond-index wrappers.
- `vol_surfaces/`: volatility surface records, quote conventions, and in-memory volatility surface sources. This is the canonical volatility namespace now, but it is still an early-scope package rather than a full smile or cube modeling stack.

### `math/`

- Numerical infrastructure.
- `interpolation/` and `extrapolation/`: interpolation schemes and extrapolation policies used by numerical routines across the library.
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
- `rates/`: swap, FRA, futures, and rates-option pricers plus rates risk modules.
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

### `market/indices/`

- Bond-index and fixing-store infrastructure plus overnight index conventions.

### `market/curves/`

- The curves package is intentionally narrow right now.
- Read [docs/api/market_curves.md](api/market_curves.md) if you want the detailed narrative explanation of the current curve ontology.
- The public API is rates-specific. It starts with `RatesTermStructure`, not a generic term-structure type.
- `CurveSpec` identifies one curve snapshot by name, reference date, day-count rule, currency, economic curve type, optional reference label, and extrapolation policy.
- `RateSpace` tells you what `rate_at(tenor)` means. For example, the returned rate may be a zero rate, an instantaneous forward rate, a par yield, or a spread.
- `RatesTermStructure.rate_at(tenor)` returns the rate at a given tenor in the curve's `rate_space`.
- `RatesTermStructure.validate_rate(tenor)` checks the tenor domain and makes sure the returned rate is finite.
- `DiscountingCurve` is the branch for curves that can discount cash flows. It adds `discount_factor_at(tenor)`, `zero_rate_at(tenor)`, and `forward_rate_between(start_tenor, end_tenor)`.
- `YieldCurve` is now the public class name for discounting-style rates curves.
- `RelativeRateCurve` is the root for rate curves that are meaningful as rates or spreads but should not be used as discount curves.
- `rates/reports.py` now exists as the internal report layer home.
- `rates/kernels/` now exists as the internal mathematical-representation layer home, and `rates/kernels/base.py` already defines the shared internal kernel contract and config.
- That shared kernel contract is intentionally small. Kernels provide the fitted rate curve on a tenor domain, and discount factors are derived from that. They do not expose their internal storage format through the shared interface.
- `rates/calibrators/` now exists as the internal fitting-layer home.
- `multicurve/index.py` is separate from the public curve class tree. It only defines stable identifiers such as `RateIndex` and `CurrencyPair`.
- Date-based code outside this package now bridges through `market/curve_support.py` instead of asking the public curve objects to grow old date-based methods again.
- The rebuilt package still does not include breakeven curves or par-yield curves. It now does include one richer concrete fit report for the imperfect-fit path: `GlobalFitReport` extends `CalibrationReport` with fitted kernel parameters, regressor coefficients, objective value, and typed per-row residual diagnostics. The public ontology, the node kernels, the parametric kernels, the spline kernels, the bootstrap calibrator, and the global-fit calibrator now exist.

### `market/vol_surfaces/`

- Canonical home for volatility surface records, quote conventions, and in-memory surface providers used by option pricers and market snapshots.
- The package is intentionally narrow today. It does not yet cover full volatility fitting, smile modeling, cube construction, or interpolation policy.

### `measures/risk/`

- Rate, spread, convexity, hedging, and value-at-risk analytics split into focused subpackages.

### `pricers/rates/`

- Rates valuation logic, futures and option pricers, risk helpers, and the market-input resolution code that binds market state into the pricing models.

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
- Package-specific failures live in that package's `errors.py`, or in a public subpackage `errors.py` when the public error boundary is narrower than the package, such as `reference/bonds/errors.py`, `math/errors.py`, and `pricers/bonds/options/errors.py`.
- All library-defined exceptions must subclass `FuggersError`, either directly or through a package-specific root such as `BondError`, `MathError`, `AnalyticsError`, or `EngineError`.
- Feature modules raise exceptions imported from their package error module. They should not define new exception classes inline when the package already has an error namespace.
- If a package does not need a stable package-specific error surface, do not add an `errors.py` file just for symmetry.

## Reading order

1. Start with `core/` for shared types and conventions.
2. Read `reference/` for static conventions and `market/` for dynamic market inputs and runtime state.
3. Read `products/` for contracts.
4. Read `pricers/` and `measures/` for calculations.
5. Read `portfolio/` and `calc/` for aggregate workflows and orchestration.
6. Read `adapters/` for file/storage/transport boundaries.
