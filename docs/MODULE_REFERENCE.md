# Module Reference

This document inventories the Python modules under `src/fuggers_py/` from the live source tree.

For each module, it records:

- the canonical module path
- a module description taken from the module docstring when present
- the top-level classes and functions defined in that file

Use [SRC_STRUCTURE.md](SRC_STRUCTURE.md) for the package/directory map and this document for the file-level reference.

Curve-related module entries are intentionally omitted while that part of the library is being rewritten.

## Root package files

Root package metadata, version plumbing, and top-level exports.

### `__init__.py`

Public package roots for the :mod:`fuggers_py` fixed-income library.

- Module path: `__init__.py`
- Top-level classes/functions: none; this module primarily defines exports, imports, or package-level constants.

### `_version.py`

No module docstring.

- Module path: `_version.py`
- Top-level classes/functions: none; this module primarily defines exports, imports, or package-level constants.

## `adapters/`

External-boundary modules for files, storage, serialization, and transport.

### `adapters/__init__.py`

External-boundary adapters for files, storage, codecs, and transport.

- Module path: `adapters/__init__.py`
- Top-level classes/functions: `__getattr__`, `__dir__`

### `adapters/file.py`

File-backed adapters for market data, reference data, and outputs.

- Module path: `adapters/file.py`
- Top-level classes/functions: `_as_path`, `_read_rows`, `_decimal_or_none`, `_date_or_none`, `_datetime_or_none`, `_currency_or_none`, `_frequency_or_none`, `_bond_type`, `_issuer_type`, `_load_schedule`, `_load_curve_inputs_payload`, `CSVQuoteSource`, `JSONCurveInputSource`, `CSVIndexFixingSource`, `CSVEtfQuoteSource`, `CSVBondReferenceSource`, `CSVIssuerReferenceSource`, `CSVRatingSource`, `CSVEtfHoldingsSource`, `EmptyBondReferenceSource`, `EmptyIssuerReferenceSource`, `EmptyRatingSource`, `EmptyEtfHoldingsSource`, `create_file_market_data`, `create_file_reference_data`, `NoOpQuotePublisher`, `NoOpCurvePublisher`, `NoOpEtfPublisher`, `NoOpAnalyticsPublisher`, `NoOpAlertPublisher`, `create_empty_output`

### `adapters/json_codec.py`

JSON codec adapters for trait-layer transports and storage.

- Module path: `adapters/json_codec.py`
- Top-level classes/functions: `_qualified_name`, `_resolve_qualified_name`, `_to_jsonable`, `_from_jsonable`, `JsonCodec`, `PrettyJsonCodec`

### `adapters/portfolio_store.py`

In-memory portfolio storage adapters.

- Module path: `adapters/portfolio_store.py`
- Top-level classes/functions: `_portfolio_sort_key`, `InMemoryPortfolioStore`

### `adapters/sqlite_storage.py`

SQLite-backed storage adapters for the trait-layer store protocols.

- Module path: `adapters/sqlite_storage.py`
- Top-level classes/functions: `_utc_now`, `_as_text`, `_ensure_parent`, `_ensure_schema`, `_SQLiteStoreBase`, `SQLiteAuditStore`, `SQLiteBondStore`, `SQLiteCurveStore`, `SQLiteConfigStore`, `SQLiteOverrideStore`, `SQLiteStorageAdapter`

### `adapters/storage.py`

Storage-oriented protocols and lightweight records.

- Module path: `adapters/storage.py`
- Top-level classes/functions: `_to_decimal`, `Pagination`, `Page`, `CurveConfig`, `CurveSnapshot`, `PricingConfig`, `OverrideRecord`, `StoredPosition`, `StoredPortfolio`, `PortfolioFilter`, `AuditEntry`, `BondStore`, `CurveStore`, `ConfigStore`, `OverrideStore`, `AuditStore`, `PortfolioStore`, `StorageAdapter`

### `adapters/transport.py`

Transport and codec contracts for remote trait adapters.

- Module path: `adapters/transport.py`
- Top-level classes/functions: `Codec`, `Transport`, `AsyncTransport`, `RemoteStorageTransport`, `CacheTransport`

## `calc/`

Calculation orchestration, routing, runtime config, and execution wiring.

### `calc/__init__.py`

Calculation requests, result DTOs, orchestration, and execution wiring.

- Module path: `calc/__init__.py`
- Top-level classes/functions: `__getattr__`, `__dir__`

### `calc/builder.py`

Builder helpers for composing calc-layer orchestration components.

- Module path: `calc/builder.py`
- Top-level classes/functions: `_iter_curve_inputs`, `_default_etf_pricer`, `_default_portfolio_analyzer`, `PricingEngine`, `PricingEngineBuilder`

### `calc/calc_graph.py`

Deterministic calculation-graph helpers for reactive orchestration.

- Module path: `calc/calc_graph.py`
- Top-level classes/functions: `_normalize`, `NodeId`, `NodeValue`, `ShardStrategy`, `ShardAssignment`, `ShardConfig`, `_GraphNode`, `_hash_to_int`, `CalculationGraph`

### `calc/config.py`

Serializable configuration records for engine orchestration.

- Module path: `calc/config.py`
- Top-level classes/functions: `_normalize_text`, `UpdateFrequency`, `NodeConfig`, `EngineConfig`

### `calc/coordination.py`

Coordination protocols and deterministic in-memory helpers.

- Module path: `calc/coordination.py`
- Top-level classes/functions: `_normalize_text`, `ServiceRegistration`, `PartitionAssignment`, `ServiceRegistry`, `PartitionRegistry`, `LeaderElection`, `InMemoryServiceRegistry`, `InMemoryPartitionRegistry`, `InMemoryLeaderElection`

### `calc/errors.py`

Exceptions raised by calc-layer routing, scheduling, and orchestration.

- Module path: `calc/errors.py`
- Top-level classes/functions: `EngineError`, `CurveNotFoundError`, `RoutingError`, `EngineConfigurationError`, `SchedulerError`

### `calc/funding_pricing_router.py`

Funding-specific calc-layer pricing router.

- Module path: `calc/funding_pricing_router.py`
- Top-level classes/functions: `RepoPricingResult`, `FundingPricingRouter`

### `calc/market_data_listener.py`

Async market-data fanout and graph integration helpers.

- Module path: `calc/market_data_listener.py`
- Top-level classes/functions: `_now`, `MarketDataUpdate`, `QuoteUpdate`, `CurveInputUpdate`, `CurveUpdate`, `IndexFixingUpdate`, `InflationFixingUpdate`, `FxRateUpdate`, `VolSurfaceUpdate`, `MarketDataPublisher`, `MarketDataListener`

### `calc/output.py`

Typed engine outputs and publisher contracts.

- Module path: `calc/output.py`
- Top-level classes/functions: `_to_decimal`, `_coerce_decimal_fields`, `BondQuoteOutput`, `SwapQuoteOutput`, `BasisSwapQuoteOutput`, `FutureQuoteOutput`, `CdsQuoteOutput`, `RvSignalOutput`, `EtfAnalyticsOutput`, `PortfolioAnalyticsOutput`, `QuotePublisher`, `CurvePublisher`, `EtfPublisher`, `AnalyticsPublisher`, `AlertPublisher`, `OutputPublisher`

### `calc/pricing_router.py`

Research-facing bond pricing router for the calc layer.

- Module path: `calc/pricing_router.py`
- Top-level classes/functions: `_to_decimal`, `PricingInput`, `PricingFailure`, `BatchPricingResult`, `PricingRouter`

### `calc/pricing_specs.py`

Research-facing pricing specifications.

- Module path: `calc/pricing_specs.py`
- Top-level classes/functions: `_to_decimal`, `BenchmarkReference`, `BidAskSpreadConfig`, `PricingSpec`

### `calc/rates_pricing_router.py`

Rates-specific pricing router for calc-layer dispatch.

- Module path: `calc/rates_pricing_router.py`
- Top-level classes/functions: `_to_decimal`, `RoutedFraPricingResult`, `RatesPricingRouter`

### `calc/reactive.py`

Reactive engine helpers that coexist with the existing sync APIs.

- Module path: `calc/reactive.py`
- Top-level classes/functions: `_as_analytics_curves`, `_OverlayMarketDataProvider`, `_ReferenceDataCache`, `ReactiveEngine`

### `calc/scheduler.py`

Async scheduler helpers for reactive engine orchestration.

- Module path: `calc/scheduler.py`
- Top-level classes/functions: `_now`, `_next_cron_run`, `UpdateSource`, `NodeUpdate`, `_AsyncFanout`, `ThrottleManager`, `_BaseScheduler`, `IntervalScheduler`, `EodScheduler`, `CronScheduler`

## `core/`

Shared primitives, conventions, traits, and low-level value types.

### `core/__init__.py`

Shared primitives for the fixed-income library.

- Module path: `core/__init__.py`
- Top-level classes/functions: none; this module primarily defines exports, imports, or package-level constants.

### `core/calendars.py`

Business-day calendars and holiday generation utilities.

- Module path: `core/calendars.py`
- Top-level classes/functions: `BusinessDayConvention`, `WeekendType`, `easter_sunday`, `last_weekday_of_month`, `nth_weekday_of_month`, `observed_date`, `Calendar`, `WeekendCalendar`, `_sifma_holidays_for_year`, `SIFMACalendar`, `USGovernmentCalendar`, `USCalendar`, `_target2_holidays_for_year`, `Target2Calendar`, `_uk_holidays_for_year`, `UKCalendar`, `_japan_vernal_equinox`, `_japan_autumnal_equinox`, `_japan_holidays_for_year`, `JapanCalendar`, `JointCalendar`, `HolidayBitmap`, `HolidayCalendarBuilder`, `CalendarData`, `DynamicCalendar`, `CustomCalendarBuilder`

### `core/daycounts.py`

Day-count conventions.

- Module path: `core/daycounts.py`
- Top-level classes/functions: `_normalize_interval`, `_includes_feb29`, `_is_last_day_of_feb`, `DayCount`, `Act360`, `Act365Fixed`, `Act365Leap`, `ActActIsda`, `ActActAfb`, `ActActIcma`, `Thirty360E`, `Thirty360EIsda`, `Thirty360German`, `Thirty360US`, `DayCountConvention`

### `core/errors.py`

Core exception hierarchy for `fuggers_py`.

- Module path: `core/errors.py`
- Top-level classes/functions: `FuggersError`, `InvalidDateError`, `InvalidYieldError`, `InvalidPriceError`, `InvalidSpreadError`, `InvalidCashFlowError`, `DayCountError`, `CalendarError`

### `core/ids.py`

Foundational typed identifiers shared across the library.

- Module path: `core/ids.py`
- Top-level classes/functions: `_normalize`, `_normalize_currency`, `InstrumentId`, `CurveId`, `PortfolioId`, `EtfId`, `VolSurfaceId`, `CurrencyPair`, `YearMonth`

### `core/traits.py`

Abstract interfaces ("traits") for `fuggers_py.core`.

- Module path: `core/traits.py`
- Top-level classes/functions: `YieldCurve`, `PricingEngine`, `RiskCalculator`, `Discountable`, `SpreadCalculator`

### `core/types.py`

Fundamental value types for fixed-income analytics.

- Module path: `core/types.py`
- Top-level classes/functions: `_to_decimal`, `Currency`, `Frequency`, `Compounding`, `SpreadType`, `CashFlowType`, `Date`, `Price`, `Yield`, `Spread`, `CashFlow`, `CashFlowSchedule`

## `market/`

Dynamic market-state objects, market data records, and indices.

### `market/__init__.py`

Market-layer state, quotes, providers, fixings, and indices.

- Module path: `market/__init__.py`
- Top-level classes/functions: `__getattr__`, `__dir__`

### `market/indices/__init__.py`

Market fixing stores, floating-index conventions, and rate-index wrappers.

- Module path: `market/indices/__init__.py`
- Top-level classes/functions: none; this module primarily defines exports, imports, or package-level constants.

### `market/indices/bond_index.py`

Bond index definitions with fixing support.

- Module path: `market/indices/bond_index.py`
- Top-level classes/functions: `BondIndex`

### `market/indices/conventions.py`

Index conventions for FRNs and overnight instruments.

- Module path: `market/indices/conventions.py`
- Top-level classes/functions: `ArrearConvention`, `ObservationShiftType`, `LookbackDays`, `LockoutDays`, `IndexConventions`

### `market/indices/fixing_store.py`

Historical fixing storage and overnight compounding helpers.

- Module path: `market/indices/fixing_store.py`
- Top-level classes/functions: `_to_decimal`, `IndexSource`, `IndexFixing`, `IndexFixingStore`

### `market/indices/overnight.py`

Overnight fixing conventions and compounding helpers.

- Module path: `market/indices/overnight.py`
- Top-level classes/functions: `_to_decimal`, `OvernightCompounding`, `PublicationTime`, `_business_accrual_schedule`, `observation_date`, `_observed_schedule_date`, `publication_date`, `overnight_factor`, `_lookup_or_project_rate`

### `market/quotes.py`

Canonical quote protocols and concrete quote records.

- Module path: `market/quotes.py`
- Top-level classes/functions: `SourceType`, `RawQuote`, `BondQuote`, `RepoQuote`, `SwapQuote`, `BasisSwapQuote`, `BondFutureQuote`, `FxForwardQuote`, `CdsQuote`, `HaircutQuote`, `InstrumentQuote`, `ScalarQuote`, `AnyInstrumentQuote`

### `market/snapshot.py`

Canonical snapshot records, stored fixings, and market-data bundles.

- Module path: `market/snapshot.py`
- Top-level classes/functions: `CurveInstrumentType`, `VolSurfaceType`, `VolQuoteType`, `InflationInterpolation`, `CurvePoint`, `CurveInput`, `CurveInputs`, `CurveData`, `IndexFixing`, `VolPoint`, `VolatilitySurface`, `FxRate`, `InflationFixing`, `EtfHolding`, `EtfQuote`, `MarketDataSnapshot`, `CurveInputSet`
- Notes: `VolSurfaceType`, `VolQuoteType`, `VolPoint`, and `VolatilitySurface` are re-exported from `market/vol_surfaces/` for compatibility.

### `market/sources.py`

Canonical market-data source protocols and in-memory providers.

- Module path: `market/sources.py`
- Top-level classes/functions: `QuoteSource`, `CurveInputSource`, `IndexFixingSource`, `ReferenceCurveSource`, `VolatilitySource`, `FxRateSource`, `InflationFixingSource`, `EtfQuoteSource`, `PricingDataProvider`, `CurveSource`, `FixingSource`, `InMemoryQuoteSource`, `InMemoryCurveSource`, `InMemoryFixingSource`, `InMemoryVolatilitySource`, `InMemoryFxRateSource`, `InMemoryInflationFixingSource`, `InMemoryEtfQuoteSource`, `MarketDataProvider`
- Notes: `VolatilitySource` and `InMemoryVolatilitySource` are re-exported from `market/vol_surfaces/` for compatibility.

### `market/state.py`

Shared market-state value objects.

- Module path: `market/state.py`
- Top-level classes/functions: `QuoteSide`, `AnalyticsCurves`

### `market/vol_surfaces/__init__.py`

Volatility surface records and source helpers.

- Module path: `market/vol_surfaces/__init__.py`
- Top-level classes/functions: none; this module primarily defines exports, imports, or package-level constants.

### `market/vol_surfaces/sources.py`

Volatility surface source protocols and in-memory providers.

- Module path: `market/vol_surfaces/sources.py`
- Top-level classes/functions: `VolatilitySource`, `InMemoryVolatilitySource`

### `market/vol_surfaces/surface.py`

Volatility surface records and quote conventions.

- Module path: `market/vol_surfaces/surface.py`
- Top-level classes/functions: `VolSurfaceType`, `VolQuoteType`, `VolPoint`, `VolatilitySurface`

## `math/`

Numerical infrastructure used by interpolation, fitting, solving, and optimization code.

### `math/__init__.py`

Float- and NumPy-oriented numerical utilities for ``fuggers_py``.

- Module path: `math/__init__.py`
- Top-level classes/functions: none; this module primarily defines exports, imports, or package-level constants.

### `math/errors.py`

Exception hierarchy for :mod:`fuggers_py.math`.

- Module path: `math/errors.py`
- Top-level classes/functions: `MathError`, `ConvergenceFailed`, `InvalidBracket`, `DivisionByZero`, `SingularMatrix`, `DimensionMismatch`, `ExtrapolationNotAllowed`, `InsufficientData`, `InvalidInput`, `MathOverflow`, `MathUnderflow`

### `math/extrapolation/__init__.py`

Extrapolation helpers used by the curve and math layers.

- Module path: `math/extrapolation/__init__.py`
- Top-level classes/functions: none; this module primarily defines exports, imports, or package-level constants.

### `math/extrapolation/base.py`

Extrapolation interfaces and method enum.

- Module path: `math/extrapolation/base.py`
- Top-level classes/functions: `Extrapolator`, `ExtrapolationMethod`

### `math/extrapolation/flat.py`

Flat (constant) extrapolation.

- Module path: `math/extrapolation/flat.py`
- Top-level classes/functions: `FlatExtrapolator`

### `math/extrapolation/linear.py`

Linear extrapolation from a reference point and slope.

- Module path: `math/extrapolation/linear.py`
- Top-level classes/functions: `LinearExtrapolator`

### `math/extrapolation/smith_wilson.py`

Smith-Wilson extrapolation for discount factors.

- Module path: `math/extrapolation/smith_wilson.py`
- Top-level classes/functions: `_wilson_kernel`, `SmithWilson`

### `math/interpolation/__init__.py`

Interpolation models used throughout the fixed-income stack.

- Module path: `math/interpolation/__init__.py`
- Top-level classes/functions: none; this module primarily defines exports, imports, or package-level constants.

### `math/interpolation/base.py`

Interpolation interfaces and shared helpers.

- Module path: `math/interpolation/base.py`
- Top-level classes/functions: `Interpolator`, `_SegmentedInterpolatorMixin`

### `math/interpolation/cubic_spline.py`

Natural cubic spline interpolation.

- Module path: `math/interpolation/cubic_spline.py`
- Top-level classes/functions: `CubicSpline`

### `math/interpolation/flat_forward.py`

Flat-forward interpolation for zero rates with piecewise-constant forwards.

- Module path: `math/interpolation/flat_forward.py`
- Top-level classes/functions: `FlatForward`

### `math/interpolation/linear.py`

Piecewise-linear interpolation on strictly increasing knots.

- Module path: `math/interpolation/linear.py`
- Top-level classes/functions: `LinearInterpolator`

### `math/interpolation/log_linear.py`

Log-linear interpolation on strictly positive values.

- Module path: `math/interpolation/log_linear.py`
- Top-level classes/functions: `LogLinearInterpolator`

### `math/interpolation/monotone_convex.py`

Monotone-convex interpolation for zero-rate curves.

- Module path: `math/interpolation/monotone_convex.py`
- Top-level classes/functions: `MonotoneConvex`

### `math/interpolation/parametric.py`

Parametric yield curve families (Nelson-Siegel and Svensson).

- Module path: `math/interpolation/parametric.py`
- Top-level classes/functions: `_a`, `_da_dx`, `_b`, `_db_dx`, `NelsonSiegel`, `Svensson`

### `math/linear_algebra/__init__.py`

Linear algebra helpers used by the numerical routines in ``fuggers_py``.

- Module path: `math/linear_algebra/__init__.py`
- Top-level classes/functions: none; this module primarily defines exports, imports, or package-level constants.

### `math/linear_algebra/lu.py`

LU decomposition with partial pivoting.

- Module path: `math/linear_algebra/lu.py`
- Top-level classes/functions: `lu_decomposition`

### `math/linear_algebra/solve.py`

Dense linear system helpers built on LU factorization.

- Module path: `math/linear_algebra/solve.py`
- Top-level classes/functions: `_forward_substitution`, `_back_substitution`, `solve_linear_system`

### `math/linear_algebra/tridiagonal.py`

Tridiagonal linear system solver (Thomas algorithm).

- Module path: `math/linear_algebra/tridiagonal.py`
- Top-level classes/functions: `solve_tridiagonal`

### `math/numerical.py`

Finite-difference helpers built on ``float`` and ``numpy`` arrays.

- Module path: `math/numerical.py`
- Top-level classes/functions: `finite_difference_derivative`, `finite_difference_gradient`, `finite_difference_jacobian`

### `math/optimization/__init__.py`

Optimization routines for fitting parameters and least-squares systems.

- Module path: `math/optimization/__init__.py`
- Top-level classes/functions: none; this module primarily defines exports, imports, or package-level constants.

### `math/optimization/gradient_descent.py`

Gradient descent with Armijo backtracking line search.

- Module path: `math/optimization/gradient_descent.py`
- Top-level classes/functions: `gradient_descent`

### `math/optimization/least_squares.py`

Least-squares routines (Gauss-Newton and a small Levenberg-Marquardt).

- Module path: `math/optimization/least_squares.py`
- Top-level classes/functions: `_residuals_and_jacobian`, `gauss_newton`, `levenberg_marquardt`

### `math/optimization/types.py`

Configuration and result types for the optimization helpers.

- Module path: `math/optimization/types.py`
- Top-level classes/functions: `OptimizationConfig`, `OptimizationResult`

### `math/solvers/__init__.py`

Scalar root-finding algorithms and their configuration/result types.

- Module path: `math/solvers/__init__.py`
- Top-level classes/functions: none; this module primarily defines exports, imports, or package-level constants.

### `math/solvers/bisection.py`

Bisection root solver.

- Module path: `math/solvers/bisection.py`
- Top-level classes/functions: `bisection`, `BisectionSolver`

### `math/solvers/brent.py`

Brent's method root solver with bracketing safeguards.

- Module path: `math/solvers/brent.py`
- Top-level classes/functions: `brent`, `BrentSolver`

### `math/solvers/hybrid.py`

Bracketed hybrid root solvers combining Newton and bisection steps.

- Module path: `math/solvers/hybrid.py`
- Top-level classes/functions: `hybrid`, `hybrid_numerical`, `HybridSolver`

### `math/solvers/newton.py`

Newton-Raphson root solvers.

- Module path: `math/solvers/newton.py`
- Top-level classes/functions: `newton_raphson`, `newton_raphson_numerical`, `NewtonSolver`

### `math/solvers/secant.py`

Secant root solver.

- Module path: `math/solvers/secant.py`
- Top-level classes/functions: `secant`, `SecantSolver`

### `math/solvers/types.py`

Root-finding interfaces and result/config types.

- Module path: `math/solvers/types.py`
- Top-level classes/functions: `SolverConfig`, `SolverResult`, `RootFinder`

### `math/utils.py`

Small validation and indexing helpers for :mod:`fuggers_py.math`.

- Module path: `math/utils.py`
- Top-level classes/functions: `assert_finite`, `assert_finite_array`, `assert_strictly_increasing`, `assert_same_length`, `assert_all_positive`, `clamp`, `bisect_segment`

## `measures/`

User-facing analytics, desk-style measures, and reporting helpers.

### `measures/__init__.py`

User-facing analytics, desk measures, and report-oriented helpers.

- Module path: `measures/__init__.py`
- Top-level classes/functions: none; this module primarily defines exports, imports, or package-level constants.

### `measures/cashflows/__init__.py`

Analytics cashflow helpers and settlement utilities.

- Module path: `measures/cashflows/__init__.py`
- Top-level classes/functions: none; this module primarily defines exports, imports, or package-level constants.

### `measures/cashflows/irregular.py`

Irregular-period helpers for analytics.

- Module path: `measures/cashflows/irregular.py`
- Top-level classes/functions: `IrregularPeriodHandler`

### `measures/cashflows/settlement.py`

Analytics settlement helpers.

- Module path: `measures/cashflows/settlement.py`
- Top-level classes/functions: `SettlementStatus`, `SettlementCalculator`, `settlement_status`

### `measures/credit/__init__.py`

Credit desk analytics and named measures.

- Module path: `measures/credit/__init__.py`
- Top-level classes/functions: none; this module primarily defines exports, imports, or package-level constants.

### `measures/credit/adjusted_cds.py`

Adjusted CDS spread helpers.

- Module path: `measures/credit/adjusted_cds.py`
- Top-level classes/functions: `_to_decimal`, `AdjustedCdsBreakdown`, `adjusted_cds_breakdown`, `adjusted_cds_spread`

### `measures/credit/bond_cds_basis.py`

Bond-versus-CDS basis helpers.

- Module path: `measures/credit/bond_cds_basis.py`
- Top-level classes/functions: `_to_decimal`, `BondCdsBasisBreakdown`, `bond_cds_basis_breakdown`, `bond_cds_basis`

### `measures/credit/risk_free_proxy.py`

CDS-adjusted proxy risk-free helpers.

- Module path: `measures/credit/risk_free_proxy.py`
- Top-level classes/functions: `_to_decimal`, `RiskFreeProxyBreakdown`, `proxy_risk_free_breakdown`, `cds_adjusted_risk_free_rate`

### `measures/errors.py`

Analytics-layer exception hierarchy.

- Module path: `measures/errors.py`
- Top-level classes/functions: `AnalyticsError`, `InvalidInput`, `InvalidSettlement`, `YieldSolverError`, `PricingError`, `SpreadError`

### `measures/functions.py`

Standalone analytics helpers.

- Module path: `measures/functions.py`
- Top-level classes/functions: `_core_compounding`, `yield_to_maturity`, `yield_to_maturity_with_convention`, `dirty_price_from_yield`, `clean_price_from_yield`, `macaulay_duration`, `modified_duration`, `effective_duration`, `convexity`, `effective_convexity`, `dv01`, `dv01_notional`, `estimate_price_change`, `price_change_from_duration`, `parse_day_count`, `calculate_accrued_interest`, `calculate_macaulay_duration`, `calculate_modified_duration`, `calculate_yield_to_maturity`, `calculate_z_spread`

### `measures/funding/__init__.py`

Funding desk analytics and carry measures.

- Module path: `measures/funding/__init__.py`
- Top-level classes/functions: none; this module primarily defines exports, imports, or package-level constants.

### `measures/funding/carry.py`

Carry helpers for repo trades.

- Module path: `measures/funding/carry.py`
- Top-level classes/functions: `_to_decimal`, `repo_financing_cost`, `repo_net_carry`, `repo_carry_return`

### `measures/funding/haircuts.py`

Haircut financing helpers.

- Module path: `measures/funding/haircuts.py`
- Top-level classes/functions: `_to_decimal`, `haircut_amount`, `financed_cash`, `haircut_financing_cost`, `all_in_financing_cost`, `haircut_drag`

### `measures/funding/implied_repo.py`

Implied-repo analytics from futures and cash-bond primitives.

- Module path: `measures/funding/implied_repo.py`
- Top-level classes/functions: `_to_decimal`, `futures_invoice_amount`, `implied_repo_rate`, `implied_repo_rate_from_trade`

### `measures/funding/specialness.py`

Specialness helpers with an explicit sign convention.

- Module path: `measures/funding/specialness.py`
- Top-level classes/functions: `_to_decimal`, `specialness_spread`, `specialness_value`, `is_special`

### `measures/inflation/__init__.py`

Inflation and linker relative-value helpers.

- Module path: `measures/inflation/__init__.py`
- Top-level classes/functions: `_to_decimal`, `LinkerSwapParityCheck`, `breakeven_inflation_rate`, `nominal_real_yield_basis`, `nominal_real_yield_spread`, `linker_swap_parity_check`

### `measures/options/__init__.py`

Option analytics helpers for the analytics layer.

- Module path: `measures/options/__init__.py`
- Top-level classes/functions: none; this module primarily defines exports, imports, or package-level constants.

### `measures/options/greeks.py`

Helpers for option Greeks aggregation and scaling.

- Module path: `measures/options/greeks.py`
- Top-level classes/functions: `_to_decimal`, `extract_option_greeks`, `scale_option_greeks`, `add_option_greeks`, `aggregate_option_greeks`

### `measures/options/rv.py`

Basic relative-value helpers for options.

- Module path: `measures/options/rv.py`
- Top-level classes/functions: `_to_decimal`, `OptionRvSignal`, `implied_minus_realized_volatility`, `vega_notional`, `option_rv_signal`

### `measures/pricing/__init__.py`

Analytics pricing helpers.

- Module path: `measures/pricing/__init__.py`
- Top-level classes/functions: `PriceResult`, `BondPricer`, `TipsPricer`

### `measures/risk/__init__.py`

Risk analytics (`fuggers_py.measures.risk`).

- Module path: `measures/risk/__init__.py`
- Top-level classes/functions: none; this module primarily defines exports, imports, or package-level constants.

### `measures/risk/calculator.py`

Risk calculators (`fuggers_py.measures.risk.calculator`).

- Module path: `measures/risk/calculator.py`
- Top-level classes/functions: `BondRiskMetrics`, `EffectiveDurationCalculator`, `BondRiskCalculator`

### `measures/risk/convexity/__init__.py`

Convexity analytics (`fuggers_py.measures.risk.convexity`).

- Module path: `measures/risk/convexity/__init__.py`
- Top-level classes/functions: `_to_decimal`, `Convexity`, `price_change_with_convexity`

### `measures/risk/convexity/analytical.py`

Analytical convexity (`fuggers_py.measures.risk.convexity.analytical`).

- Module path: `measures/risk/convexity/analytical.py`
- Top-level classes/functions: `analytical_convexity`

### `measures/risk/convexity/effective.py`

Effective convexity (`fuggers_py.measures.risk.convexity.effective`).

- Module path: `measures/risk/convexity/effective.py`
- Top-level classes/functions: `effective_convexity`

### `measures/risk/duration/__init__.py`

Duration analytics (`fuggers_py.measures.risk.duration`).

- Module path: `measures/risk/duration/__init__.py`
- Top-level classes/functions: `Duration`

### `measures/risk/duration/effective.py`

Effective duration (`fuggers_py.measures.risk.duration.effective`).

- Module path: `measures/risk/duration/effective.py`
- Top-level classes/functions: `effective_duration`

### `measures/risk/duration/key_rate.py`

Key-rate duration helpers (`fuggers_py.measures.risk.duration.key_rate`).

- Module path: `measures/risk/duration/key_rate.py`
- Top-level classes/functions: `_tenor_years`, `KeyRateDuration`, `KeyRateDurations`, `KeyRateDurationCalculator`, `key_rate_duration_at_tenor`

### `measures/risk/duration/macaulay.py`

Macaulay duration (`fuggers_py.measures.risk.duration.macaulay`).

- Module path: `measures/risk/duration/macaulay.py`
- Top-level classes/functions: `macaulay_duration`

### `measures/risk/duration/modified.py`

Modified duration (`fuggers_py.measures.risk.duration.modified`).

- Module path: `measures/risk/duration/modified.py`
- Top-level classes/functions: `modified_duration`, `modified_from_macaulay`

### `measures/risk/duration/spread_duration.py`

Spread duration helpers (`fuggers_py.measures.risk.duration.spread_duration`).

- Module path: `measures/risk/duration/spread_duration.py`
- Top-level classes/functions: `_to_decimal`, `_spread_duration_from_curve`, `spread_duration`

### `measures/risk/dv01.py`

DV01 helpers (`fuggers_py.measures.risk.dv01`).

- Module path: `measures/risk/dv01.py`
- Top-level classes/functions: `_to_decimal`, `DV01`, `dv01_from_duration`, `dv01_from_prices`, `dv01_per_100_face`, `notional_from_dv01`

### `measures/risk/hedging/__init__.py`

Hedging helpers (`fuggers_py.measures.risk.hedging`).

- Module path: `measures/risk/hedging/__init__.py`
- Top-level classes/functions: none; this module primarily defines exports, imports, or package-level constants.

### `measures/risk/hedging/hedge_ratio.py`

Hedge ratio helpers (`fuggers_py.measures.risk.hedging.hedge_ratio`).

- Module path: `measures/risk/hedging/hedge_ratio.py`
- Top-level classes/functions: `_to_decimal`, `HedgeDirection`, `HedgeRecommendation`, `duration_hedge_ratio`, `dv01_hedge_ratio`

### `measures/risk/hedging/portfolio.py`

Portfolio risk aggregation (`fuggers_py.measures.risk.hedging.portfolio`).

- Module path: `measures/risk/hedging/portfolio.py`
- Top-level classes/functions: `_to_decimal`, `Position`, `PortfolioRisk`, `aggregate_portfolio_risk`

### `measures/risk/var/__init__.py`

Value-at-risk helpers (`fuggers_py.measures.risk.var`).

- Module path: `measures/risk/var/__init__.py`
- Top-level classes/functions: none; this module primarily defines exports, imports, or package-level constants.

### `measures/risk/var/historical.py`

Historical VaR (`fuggers_py.measures.risk.var.historical`).

- Module path: `measures/risk/var/historical.py`
- Top-level classes/functions: `_validate_confidence`, `_left_tail_quantile`, `historical_var`

### `measures/risk/var/parametric.py`

Parametric VaR (`fuggers_py.measures.risk.var.parametric`).

- Module path: `measures/risk/var/parametric.py`
- Top-level classes/functions: `_validate_confidence`, `parametric_var`, `parametric_var_from_dv01`

### `measures/risk/var/types.py`

VaR result types (`fuggers_py.measures.risk.var.types`).

- Module path: `measures/risk/var/types.py`
- Top-level classes/functions: `VaRMethod`, `VaRResult`

### `measures/rv/__init__.py`

Relative-value analytics for bond and cross-asset workflows.

- Module path: `measures/rv/__init__.py`
- Top-level classes/functions: none; this module primarily defines exports, imports, or package-level constants.

### `measures/rv/asw_basis_cds_links.py`

Explicit ASW / basis / adjusted-CDS link decomposition.

- Module path: `measures/rv/asw_basis_cds_links.py`
- Top-level classes/functions: `_to_decimal`, `AswBasisCdsLinkBreakdown`, `decompose_asw_basis_cds_links`, `decompose_floating_view_links`

### `measures/rv/basis_swapped_bonds.py`

Bond transformations through asset-swap, basis, and CCBS chains.

- Module path: `measures/rv/basis_swapped_bonds.py`
- Top-level classes/functions: `CommonCurrencyFloatingBondView`, `CommonCurrencyFixedBondView`, `_same_index`, `bond_to_common_currency_floating`, `bond_to_common_currency_fixed`

### `measures/rv/bond_switch.py`

Bond-switch construction from local rich/cheap signals.

- Module path: `measures/rv/bond_switch.py`
- Top-level classes/functions: `_to_decimal`, `_yield_from_decimal`, `BondSwitchTrade`, `construct_bond_switch`

### `measures/rv/butterfly.py`

Butterfly construction from bond residual signals.

- Module path: `measures/rv/butterfly.py`
- Top-level classes/functions: `_yield_from_decimal`, `ButterflyTrade`, `construct_butterfly`

### `measures/rv/constant_maturity.py`

Constant-maturity benchmark generation.

- Module path: `measures/rv/constant_maturity.py`
- Top-level classes/functions: `_to_decimal`, `ConstantMaturityBenchmark`, `generate_constant_maturity_benchmark`

### `measures/rv/global_bond_rv.py`

Global bond RV workflows built on basis-swapped bond views.

- Module path: `measures/rv/global_bond_rv.py`
- Top-level classes/functions: `_to_decimal`, `_classification`, `GlobalFixedCashflowRvResult`, `GlobalUsdSofrRvResult`, `global_fixed_cashflow_rv`, `global_usd_sofr_rv`

### `measures/rv/neutrality.py`

Deterministic neutrality helpers for RV trades.

- Module path: `measures/rv/neutrality.py`
- Top-level classes/functions: `_to_decimal`, `_yield_from_decimal`, `NeutralityTarget`, `TradeLeg`, `NeutralizedTradeExpression`, `_point_risk`, `_point_from_choice`, `_trade_leg`, `neutralize_choices`, `neutralize_bond_pair`

### `measures/rv/new_issue.py`

Hypothetical new-issue fair-value estimation.

- Module path: `measures/rv/new_issue.py`
- Top-level classes/functions: `_to_decimal`, `NewIssueRequest`, `NewIssueFairValue`, `estimate_new_issue_fair_value`

### `measures/rv/rich_cheap.py`

Local rich/cheap ranking from bond residual signals.

- Module path: `measures/rv/rich_cheap.py`
- Top-level classes/functions: `_to_decimal`, `RichCheapSignal`, `rank_rich_cheap`

### `measures/rv/selection.py`

Deterministic hooks from external signals into RV choices.

- Module path: `measures/rv/selection.py`
- Top-level classes/functions: `_to_decimal`, `SignalDirection`, `_resolved_direction`, `_point_metadata`, `MaturitySignal`, `BondSignal`, `MaturityChoice`, `BondChoice`, `_eligible_points`, `select_maturity_choice`, `select_maturity_choices`, `select_bond_choice`, `select_bond_choices`

### `measures/rv/usd_sofr_yardstick.py`

USD SOFR yardstick comparisons for global bond RV.

- Module path: `measures/rv/usd_sofr_yardstick.py`
- Top-level classes/functions: `_to_decimal`, `UsdSofrAdjustedRvMeasure`, `usd_sofr_adjusted_rv_measure`, `usd_sofr_adjusted_rv_from_links`

### `measures/rv/workflow.py`

Workflow hooks from external signals into deterministic RV trades.

- Module path: `measures/rv/workflow.py`
- Top-level classes/functions: `_pick_long_signal`, `_pick_short_signal`, `RvWorkflowResult`, `maturity_signal_workflow`, `bond_signal_workflow`, `maturity_pair_trade`, `bond_pair_trade`

### `measures/spreads/__init__.py`

Spread analytics for the analytics layer.

- Module path: `measures/spreads/__init__.py`
- Top-level classes/functions: `SecurityId`

### `measures/spreads/adjustments/__init__.py`

Spread-adjustment overlays for balance-sheet, capital, haircut, and shadow-cost effects.

- Module path: `measures/spreads/adjustments/__init__.py`
- Top-level classes/functions: none; this module primarily defines exports, imports, or package-level constants.

### `measures/spreads/adjustments/balance_sheet.py`

Composable balance-sheet spread overlays.

- Module path: `measures/spreads/adjustments/balance_sheet.py`
- Top-level classes/functions: `_to_decimal`, `SpreadAdjustmentBreakdown`, `SpreadAdjustment`, `BaseSpreadAdjustment`, `SpreadAdjustmentSummary`, `FundingSpreadOverlayResult`, `compose_spread_adjustments`, `BalanceSheetSpreadOverlay`, `apply_balance_sheet_overlays`, `apply_funding_spread_overlays`

### `measures/spreads/adjustments/capital.py`

Capital-charge spread overlays.

- Module path: `measures/spreads/adjustments/capital.py`
- Top-level classes/functions: `_to_decimal`, `CapitalAdjustmentBreakdown`, `capital_adjustment_breakdown`, `capital_spread_adjustment`, `CapitalSpreadAdjustment`

### `measures/spreads/adjustments/haircuts.py`

Haircut-driven spread overlays.

- Module path: `measures/spreads/adjustments/haircuts.py`
- Top-level classes/functions: `_to_decimal`, `HaircutAdjustmentBreakdown`, `haircut_adjustment_breakdown`, `haircut_spread_adjustment`, `HaircutSpreadAdjustment`

### `measures/spreads/adjustments/shadow_cost.py`

Shadow-cost spread overlays.

- Module path: `measures/spreads/adjustments/shadow_cost.py`
- Top-level classes/functions: `_to_decimal`, `ShadowCostAdjustmentBreakdown`, `utilization_ratio`, `shadow_cost_adjustment_breakdown`, `shadow_cost_spread_adjustment`, `ShadowCostSpreadAdjustment`

### `measures/spreads/asw/__init__.py`

Asset-swap helpers exposed through the analytics spread surface.

- Module path: `measures/spreads/asw/__init__.py`
- Top-level classes/functions: none; this module primarily defines exports, imports, or package-level constants.

### `measures/spreads/asw/par_par.py`

Par-par asset-swap spread helpers.

- Module path: `measures/spreads/asw/par_par.py`
- Top-level classes/functions: `ParParAssetSwap`

### `measures/spreads/asw/proceeds.py`

Proceeds asset-swap spread helpers.

- Module path: `measures/spreads/asw/proceeds.py`
- Top-level classes/functions: `ProceedsAssetSwap`

### `measures/spreads/benchmark.py`

Benchmark specification (`fuggers_py.measures.spreads.benchmark`).

- Module path: `measures/spreads/benchmark.py`
- Top-level classes/functions: `_to_decimal`, `BenchmarkKind`, `BenchmarkSpec`

### `measures/spreads/compounding_convexity.py`

Compounding and convexity adjustment helpers for reference-rate ladders.

- Module path: `measures/spreads/compounding_convexity.py`
- Top-level classes/functions: `_to_decimal`, `simple_to_compounded_equivalent_rate`, `CompoundingConvexityBreakdown`, `compounding_convexity_breakdown`, `adjusted_term_rate`

### `measures/spreads/discount_margin.py`

Discount-margin helpers.

- Module path: `measures/spreads/discount_margin.py`
- Top-level classes/functions: `_to_decimal`, `DiscountMarginCalculator`, `simple_margin`, `z_discount_margin`

### `measures/spreads/gspread.py`

G-spread helpers.

- Module path: `measures/spreads/gspread.py`
- Top-level classes/functions: `g_spread`, `g_spread_with_benchmark`, `GSpreadCalculator`

### `measures/spreads/ispread.py`

I-spread helpers.

- Module path: `measures/spreads/ispread.py`
- Top-level classes/functions: `i_spread`, `ISpreadCalculator`

### `measures/spreads/oas.py`

Option-adjusted spread helpers.

- Module path: `measures/spreads/oas.py`
- Top-level classes/functions: `_to_decimal`, `OASCalculator`

### `measures/spreads/reference_rates.py`

Reference-rate ladder decomposition helpers.

- Module path: `measures/spreads/reference_rates.py`
- Top-level classes/functions: `_to_decimal`, `ReferenceRateBreakdown`, `reference_rate_decomposition`

### `measures/spreads/secured_unsecured_basis.py`

Secured-versus-unsecured overnight basis helpers.

- Module path: `measures/spreads/secured_unsecured_basis.py`
- Top-level classes/functions: `_to_decimal`, `SecuredUnsecuredBasisModel`, `GQDSecuredUnsecuredBasisModel`, `secured_unsecured_overnight_basis`

### `measures/spreads/sovereign.py`

Sovereign issuer labels used by spread analytics.

- Module path: `measures/spreads/sovereign.py`
- Top-level classes/functions: `Sovereign`, `SupranationalIssuer`

### `measures/spreads/zspread.py`

Z-spread helpers.

- Module path: `measures/spreads/zspread.py`
- Top-level classes/functions: `_to_float`, `_prepare_cashflows`, `z_spread_from_curve`, `z_spread`, `ZSpreadCalculator`

### `measures/yas/__init__.py`

YAS analytics (`fuggers_py.measures.yas`).

- Module path: `measures/yas/__init__.py`
- Top-level classes/functions: none; this module primarily defines exports, imports, or package-level constants.

### `measures/yas/analysis.py`

YAS analysis containers (`fuggers_py.measures.yas.analysis`).

- Module path: `measures/yas/analysis.py`
- Top-level classes/functions: `_to_decimal`, `ValidationFailure`, `BloombergReference`, `YasAnalysis`, `YasAnalysisBuilder`

### `measures/yas/calculator.py`

YAS calculator (`fuggers_py.measures.yas.calculator`).

- Module path: `measures/yas/calculator.py`
- Top-level classes/functions: `_to_decimal`, `YASCalculator`, `BatchYASCalculator`

### `measures/yas/invoice.py`

Settlement invoice (`fuggers_py.measures.yas.invoice`).

- Module path: `measures/yas/invoice.py`
- Top-level classes/functions: `_to_decimal`, `calculate_accrued_amount`, `calculate_proceeds`, `calculate_settlement_date`, `SettlementInvoice`, `SettlementInvoiceBuilder`

### `measures/yields/__init__.py`

Yield analytics (`fuggers_py.measures.yields`).

- Module path: `measures/yields/__init__.py`
- Top-level classes/functions: none; this module primarily defines exports, imports, or package-level constants.

### `measures/yields/bond.py`

Bond-layer yield helpers shared by bonds and analytics.

- Module path: `measures/yields/bond.py`
- Top-level classes/functions: `_to_decimal`, `current_yield`, `current_yield_from_amount`, `current_yield_from_bond`, `current_yield_simple`, `YieldResult`, `YieldSolver`

### `measures/yields/current.py`

Current yield helpers (`fuggers_py.measures.yields.current`).

- Module path: `measures/yields/current.py`
- Top-level classes/functions: `_raise_invalid_input`, `current_yield`, `current_yield_from_amount`, `current_yield_from_bond`, `current_yield_simple`

### `measures/yields/engine.py`

Yield engine (`fuggers_py.measures.yields.engine`).

- Module path: `measures/yields/engine.py`
- Top-level classes/functions: `YieldEngineResult`, `YieldEngine`, `StandardYieldEngine`, `discount_yield_simple`, `bond_equivalent_yield_simple`, `current_yield_simple`

### `measures/yields/money_market.py`

Money-market yield helpers (`fuggers_py.measures.yields.money_market`).

- Module path: `measures/yields/money_market.py`
- Top-level classes/functions: `_to_decimal`, `discount_yield`, `bond_equivalent_yield`, `cd_equivalent_yield`, `money_market_yield`, `money_market_yield_with_horizon`

### `measures/yields/short_date.py`

Short-dated yield helpers (`fuggers_py.measures.yields.short_date`).

- Module path: `measures/yields/short_date.py`
- Top-level classes/functions: `RollForwardMethod`, `ShortDateCalculator`

### `measures/yields/simple.py`

Simple yield helpers (`fuggers_py.measures.yields.simple`).

- Module path: `measures/yields/simple.py`
- Top-level classes/functions: `_to_decimal`, `simple_yield`, `simple_yield_f64`

### `measures/yields/solver.py`

Yield solver (`fuggers_py.measures.yields.solver`).

- Module path: `measures/yields/solver.py`
- Top-level classes/functions: `YieldSolver`

### `measures/yields/street.py`

Street-convention yield (`fuggers_py.measures.yields.street`).

- Module path: `measures/yields/street.py`
- Top-level classes/functions: `street_convention_yield`

### `measures/yields/true_yield.py`

True yield helpers (`fuggers_py.measures.yields.true_yield`).

- Module path: `measures/yields/true_yield.py`
- Top-level classes/functions: `_to_decimal`, `settlement_adjustment`, `true_yield`

## `portfolio/`

Portfolio containers, aggregation, attribution, stress, ETF, and result types.

### `portfolio/__init__.py`

Fixed-income portfolio analytics and typed public result surfaces.

- Module path: `portfolio/__init__.py`
- Top-level classes/functions: none; this module primarily defines exports, imports, or package-level constants.

### `portfolio/_analytics_utils.py`

Shared portfolio analytics helpers.

- Module path: `portfolio/_analytics_utils.py`
- Top-level classes/functions: `_cash_position_analytics`, `_clean_price_for`, `_weight_base`, `_weighted_optional_average`, `position_analytics`, `aggregate_metrics`

### `portfolio/analytics/__init__.py`

Portfolio analytics package.

- Module path: `portfolio/analytics/__init__.py`
- Top-level classes/functions: `_metrics`, `aggregate_key_rate_profile`, `partial_dv01s`, `calculate_nav_breakdown`, `weighted_duration`, `weighted_convexity`, `total_dv01`, `total_cs01`, `weighted_spreads`, `weighted_ytm`, `weighted_ytw`, `weighted_ytc`, `weighted_current_yield`

### `portfolio/analytics/base.py`

Base portfolio analytics class.

- Module path: `portfolio/analytics/base.py`
- Top-level classes/functions: `PortfolioAnalytics`

### `portfolio/analytics/credit.py`

Credit-quality aggregation.

- Module path: `portfolio/analytics/credit.py`
- Top-level classes/functions: `_holding_weight`, `_rating_for`, `_sector_for`, `_nearest_rating`, `calculate_credit_quality`

### `portfolio/analytics/quote_outputs.py`

Portfolio aggregation on top of instrument quote outputs.

- Module path: `portfolio/analytics/quote_outputs.py`
- Top-level classes/functions: `PortfolioPosition`, `_as_position`, `PortfolioAnalyzer`

### `portfolio/analytics/summary.py`

High-level portfolio summary helpers.

- Module path: `portfolio/analytics/summary.py`
- Top-level classes/functions: `calculate_portfolio_analytics`

### `portfolio/benchmark/__init__.py`

Benchmark and tracking analytics.

- Module path: `portfolio/benchmark/__init__.py`
- Top-level classes/functions: none; this module primarily defines exports, imports, or package-level constants.

### `portfolio/benchmark/comparison.py`

Benchmark comparison helpers.

- Module path: `portfolio/benchmark/comparison.py`
- Top-level classes/functions: `ActiveWeight`, `ActiveWeights`, `DurationComparison`, `RiskComparison`, `YieldComparison`, `SpreadComparison`, `SectorComparison`, `RatingComparison`, `BenchmarkComparison`, `_active_weights_from_maps`, `_bucket_weights`, `active_weights`, `compare_portfolios`, `benchmark_comparison`, `PortfolioBenchmark`

### `portfolio/benchmark/tracking.py`

Benchmark tracking helpers.

- Module path: `portfolio/benchmark/tracking.py`
- Top-level classes/functions: `TrackingErrorEstimate`, `estimate_tracking_error`

### `portfolio/bucketing/__init__.py`

Portfolio bucketing helpers.

- Module path: `portfolio/bucketing/__init__.py`
- Top-level classes/functions: `Bucketing`, `summarize_bucket_assignments`, `sector_bucket_metrics`, `rating_bucket_metrics`, `maturity_bucket_metrics`

### `portfolio/bucketing/custom.py`

Custom-field bucketing.

- Module path: `portfolio/bucketing/custom.py`
- Top-level classes/functions: `bucket_by_custom_field`, `_normalize_bucket_key`, `_classifier_value`, `bucket_by_classifier`, `_bucket_by_attr`, `bucket_by_country`, `bucket_by_currency`, `bucket_by_issuer`, `bucket_by_region`

### `portfolio/bucketing/maturity.py`

Maturity bucketing.

- Module path: `portfolio/bucketing/maturity.py`
- Top-level classes/functions: `bucket_by_maturity`

### `portfolio/bucketing/rating.py`

Rating bucketing.

- Module path: `portfolio/bucketing/rating.py`
- Top-level classes/functions: `bucket_by_rating`

### `portfolio/bucketing/sector.py`

Sector bucketing.

- Module path: `portfolio/bucketing/sector.py`
- Top-level classes/functions: `bucket_by_sector`

### `portfolio/contribution/__init__.py`

Contribution analytics.

- Module path: `portfolio/contribution/__init__.py`
- Top-level classes/functions: `Contribution`

### `portfolio/contribution/attribution.py`

Contribution and attribution helpers.

- Module path: `portfolio/contribution/attribution.py`
- Top-level classes/functions: `_to_decimal`, `_effective_assumptions`, `_position_name`, `_sector_name`, `_weighted_metric_by_sector`, `_sector_difference`, `attribution_summary`, `calculate_attribution`, `estimate_income_returns`, `estimate_rate_returns`, `estimate_spread_returns`, `duration_difference_by_sector`, `spread_difference_by_sector`, `aggregated_attribution`, `weights_sum_check`

### `portfolio/contribution/risk.py`

Risk contribution helpers.

- Module path: `portfolio/contribution/risk.py`
- Top-level classes/functions: `_position_groups`, `duration_contributions`, `dv01_contributions`, `spread_contributions`, `cs01_contributions`, `contribution_by_sector`, `contribution_by_rating`, `top_contributors`

### `portfolio/contribution/types.py`

Typed contribution and attribution results.

- Module path: `portfolio/contribution/types.py`
- Top-level classes/functions: `HoldingContribution`, `_ContributionCollection`, `DurationContributions`, `Dv01Contributions`, `Cs01Contributions`, `HoldingAttribution`, `PortfolioAttribution`, `AttributionInput`, `BucketContribution`, `SectorAttribution`, `AggregatedAttribution`

### `portfolio/etf/__init__.py`

ETF analytics helpers.

- Module path: `portfolio/etf/__init__.py`
- Top-level classes/functions: none; this module primarily defines exports, imports, or package-level constants.

### `portfolio/etf/basket.py`

ETF basket analytics.

- Module path: `portfolio/etf/basket.py`
- Top-level classes/functions: `BasketAnalysis`, `BasketComponent`, `BasketFlowSummary`, `CreationBasket`, `_validate_share_counts`, `_position_name`, `_sector_name`, `build_creation_basket`, `analyze_etf_basket`

### `portfolio/etf/nav.py`

ETF NAV helpers.

- Module path: `portfolio/etf/nav.py`
- Top-level classes/functions: `PremiumDiscountStats`, `PremiumDiscountPoint`, `EtfNavMetrics`, `_validate_shares_outstanding`, `_per_share_risk`, `calculate_etf_nav`, `calculate_inav`, `dv01_per_share`, `cs01_per_share`, `premium_discount_stats`, `premium_discount`, `arbitrage_opportunity`, `calculate_etf_nav_metrics`

### `portfolio/etf/pricing.py`

ETF-style aggregation on top of instrument quote outputs.

- Module path: `portfolio/etf/pricing.py`
- Top-level classes/functions: `_holding_value`, `EtfPricer`

### `portfolio/etf/sec.py`

ETF SEC/distribution yield helpers.

- Module path: `portfolio/etf/sec.py`
- Top-level classes/functions: `SecYieldInput`, `SecYield`, `ExpenseMetrics`, `ComplianceSeverity`, `ComplianceCheck`, `EtfComplianceReport`, `_annualize_sec_yield`, `approximate_sec_yield`, `calculate_sec_yield`, `calculate_sec_yield`, `calculate_sec_yield`, `calculate_distribution_yield`, `estimate_yield_from_holdings`, `etf_compliance_checks`

### `portfolio/liquidity/__init__.py`

Typed liquidity analytics and compatibility helpers.

- Module path: `portfolio/liquidity/__init__.py`
- Top-level classes/functions: `_MetricMapping`, `LiquidityBucket`, `LiquidityDistribution`, `DaysToLiquidate`, `LiquidityMetrics`, `_bucket_for`, `_days_to_liquidate`, `weighted_liquidity_score`, `weighted_bid_ask_spread`, `liquidity_distribution`, `estimate_days_to_liquidate`, `calculate_liquidity_metrics`

### `portfolio/portfolio.py`

Portfolio container types.

- Module path: `portfolio/portfolio.py`
- Top-level classes/functions: `Portfolio`, `PortfolioBuilder`

### `portfolio/results.py`

Typed public result records for the portfolio package.

- Module path: `portfolio/results.py`
- Top-level classes/functions: `_EntryMapping`, `KeyRateProfile`, `NavBreakdown`, `_DistributionBase`, `CustomDistribution`, `ClassifierDistribution`, `MaturityDistribution`, `RatingDistribution`, `SectorDistribution`, `DistributionYield`

### `portfolio/risk/__init__.py`

Typed public risk, yield, spread, and credit metrics.

- Module path: `portfolio/risk/__init__.py`
- Top-level classes/functions: `_QualityTiersRaw`, `_MigrationRiskRaw`, `_CreditQualityRaw`, `QualityTiers`, `FallenAngelRisk`, `RisingStarRisk`, `MigrationRisk`, `CreditQualityMetrics`, `YieldMetrics`, `SpreadMetrics`, `RiskMetrics`, `_metrics`, `_position_weight`, `_position_market_value`, `_position_rating`, `_build_quality_tiers`, `calculate_migration_risk`, `calculate_credit_quality`, `calculate_credit_metrics`, `calculate_yield_metrics`, `calculate_spread_metrics`, `weighted_z_spread`, `weighted_oas`, `weighted_g_spread`, `weighted_i_spread`, `weighted_asw`, `weighted_best_spread`, `weighted_spread_duration`, `calculate_risk_metrics`, `weighted_modified_duration`, `weighted_effective_duration`, `weighted_macaulay_duration`, `weighted_effective_convexity`, `weighted_best_yield`, `weighted_best_duration`

### `portfolio/stress/__init__.py`

Stress-testing helpers.

- Module path: `portfolio/stress/__init__.py`
- Top-level classes/functions: `Stress`

### `portfolio/stress/impact.py`

Stress impact helpers.

- Module path: `portfolio/stress/impact.py`
- Top-level classes/functions: `_run_stress_result`, `rate_shock_impact`, `parallel_shift_impact`, `spread_shock_impact`, `key_rate_shift_impact`, `spread_shock_result`, `key_rate_shift_result`, `run_stress_scenarios`, `run_stress_scenario`, `stress_scenarios`

### `portfolio/stress/scenarios.py`

Stress scenario definitions.

- Module path: `portfolio/stress/scenarios.py`
- Top-level classes/functions: `StressScenario`, `RateShockScenario`, `SpreadShockScenario`, `TenorShift`, `KeyRateShiftScenario`, `StressSummary`, `standard_scenarios`, `summarize_results`, `best_case`, `worst_case`

### `portfolio/types/__init__.py`

Typed portfolio domain objects used by the analytics layer.

- Module path: `portfolio/types/__init__.py`
- Top-level classes/functions: `RatingBucket`, `BucketResult`, `StressResult`, `PortfolioMetrics`

### `portfolio/types/cash.py`

Cash position types.

- Module path: `portfolio/types/cash.py`
- Top-level classes/functions: `_to_decimal`, `CashPosition`

### `portfolio/types/classification.py`

Classification metadata attached to holdings for aggregation.

- Module path: `portfolio/types/classification.py`
- Top-level classes/functions: `Classification`

### `portfolio/types/config.py`

Analytics configuration objects.

- Module path: `portfolio/types/config.py`
- Top-level classes/functions: `AnalyticsConfig`

### `portfolio/types/holding.py`

Holding and analytics types.

- Module path: `portfolio/types/holding.py`
- Top-level classes/functions: `_to_decimal`, `HoldingAnalytics`, `Holding`, `HoldingBuilder`

### `portfolio/types/maturity.py`

Maturity bucketing compatibility types.

- Module path: `portfolio/types/maturity.py`
- Top-level classes/functions: `MaturityBucket`

### `portfolio/types/weighting.py`

Weighting schemes for portfolio analytics.

- Module path: `portfolio/types/weighting.py`
- Top-level classes/functions: `WeightingMethod`

## `pricers/`

Low-level valuation engines and risk algorithms.

### `pricers/__init__.py`

Canonical namespace for moved valuation and risk algorithms.

- Module path: `pricers/__init__.py`
- Top-level classes/functions: none; this module primarily defines exports, imports, or package-level constants.

### `pricers/bonds/__init__.py`

Bond valuation engines and low-level risk metrics.

- Module path: `pricers/bonds/__init__.py`
- Top-level classes/functions: none; this module primarily defines exports, imports, or package-level constants.

### `pricers/bonds/options/__init__.py`

Bond option pricing models and short-rate tree helpers.

- Module path: `pricers/bonds/options/__init__.py`
- Top-level classes/functions: none; this module primarily defines exports, imports, or package-level constants.

### `pricers/bonds/options/binomial_tree.py`

Recombining binomial tree utilities for callable bond pricing.

- Module path: `pricers/bonds/options/binomial_tree.py`
- Top-level classes/functions: `BinomialTree`

### `pricers/bonds/options/bond_option.py`

Bond option pricing built on the short-rate tree utilities.

- Module path: `pricers/bonds/options/bond_option.py`
- Top-level classes/functions: `_to_decimal`, `OptionType`, `ExerciseStyle`, `BondOption`

### `pricers/bonds/options/errors.py`

Error hierarchy for bond-option models and tree pricing helpers.

- Module path: `pricers/bonds/options/errors.py`
- Top-level classes/functions: `ModelError`

### `pricers/bonds/options/models/__init__.py`

Short-rate models for bond options.

- Module path: `pricers/bonds/options/models/__init__.py`
- Top-level classes/functions: none; this module primarily defines exports, imports, or package-level constants.

### `pricers/bonds/options/models/base.py`

Short-rate model protocols for bond-option pricing.

- Module path: `pricers/bonds/options/models/base.py`
- Top-level classes/functions: `ShortRateModel`

### `pricers/bonds/options/models/hull_white.py`

Minimal Hull-White short-rate model support for callable bond OAS.

- Module path: `pricers/bonds/options/models/hull_white.py`
- Top-level classes/functions: `_to_decimal`, `HullWhiteModel`

### `pricers/bonds/pricer.py`

Bond pricer (`fuggers_py.pricers.bonds.pricer`).

- Module path: `pricers/bonds/pricer.py`
- Top-level classes/functions: `_core_compounding_for`, `PriceResult`, `YieldResult`, `TipsPricer`, `BondPricer`

### `pricers/bonds/risk/__init__.py`

Bond yield-risk algorithms.

- Module path: `pricers/bonds/risk/__init__.py`
- Top-level classes/functions: none; this module primarily defines exports, imports, or package-level constants.

### `pricers/bonds/risk/metrics.py`

Bond risk measures (`fuggers_py.pricers.bonds.risk.metrics`).

- Module path: `pricers/bonds/risk/metrics.py`
- Top-level classes/functions: `_AnalyticalRiskComponents`, `_discount_factor_second_derivative`, `_analytical_risk_components`, `RiskMetrics`

### `pricers/bonds/yield_engine.py`

Bond yield engine.

- Module path: `pricers/bonds/yield_engine.py`
- Top-level classes/functions: `CashFlowData`, `YieldEngineResult`, `_to_float`, `_pv_at_yield`, `_pv_derivative`, `_prepare_cashflows`, `_estimate_initial_yield`, `_solve_with_brent`, `StandardYieldEngine`

### `pricers/credit/__init__.py`

Credit valuation engines.

- Module path: `pricers/credit/__init__.py`
- Top-level classes/functions: none; this module primarily defines exports, imports, or package-level constants.

### `pricers/credit/cds_pricer.py`

Credit-default swap pricing helpers.

- Module path: `pricers/credit/cds_pricer.py`
- Top-level classes/functions: `_to_decimal`, `_curve_supports_discounting`, `_curve_supports_credit`, `_resolve_discount_curve`, `_resolve_credit_curve`, `CdsPricingResult`, `CdsPricer`

### `pricers/rates/__init__.py`

Rates valuation engines and low-level risk algorithms.

- Module path: `pricers/rates/__init__.py`
- Top-level classes/functions: none; this module primarily defines exports, imports, or package-level constants.

### `pricers/rates/asset_swap.py`

Full asset-swap pricing helpers.

- Module path: `pricers/rates/asset_swap.py`
- Top-level classes/functions: `_to_decimal`, `AssetSwapBreakdown`, `AssetSwapPricingResult`, `AssetSwapPricer`

### `pricers/rates/basis_swap_pricer.py`

Basis-swap pricing helpers.

- Module path: `pricers/rates/basis_swap_pricer.py`
- Top-level classes/functions: `BasisSwapPricingResult`, `BasisSwapPricer`

### `pricers/rates/cross_currency_basis.py`

Cross-currency basis-swap pricing helpers.

- Module path: `pricers/rates/cross_currency_basis.py`
- Top-level classes/functions: `_to_decimal`, `_pair`, `_curve_value_at_date`, `_call_fx_method`, `_forward_rate_from_explicit_curve`, `CrossCurrencyBasisSwapPricingResult`, `CrossCurrencyBasisSwapPricer`

### `pricers/rates/fra_pricer.py`

FRA pricing helpers.

- Module path: `pricers/rates/fra_pricer.py`
- Top-level classes/functions: `FraPricingResult`, `FraPricer`

### `pricers/rates/futures/__init__.py`

Rates futures valuation and delivery-option algorithms.

- Module path: `pricers/rates/futures/__init__.py`
- Top-level classes/functions: none; this module primarily defines exports, imports, or package-level constants.

### `pricers/rates/futures/basis.py`

Basis helpers for government bond futures.

- Module path: `pricers/rates/futures/basis.py`
- Top-level classes/functions: `_to_decimal`, `FuturesBasis`, `gross_basis`, `net_basis`, `basis_metrics`

### `pricers/rates/futures/conversion_factor.py`

Conversion-factor helpers for government bond futures.

- Module path: `pricers/rates/futures/conversion_factor.py`
- Top-level classes/functions: `ConversionFactorResult`, `theoretical_conversion_factor`, `conversion_factor`

### `pricers/rates/futures/ctd.py`

Cheapest-to-deliver helpers for government bond futures.

- Module path: `pricers/rates/futures/ctd.py`
- Top-level classes/functions: `_to_decimal`, `DeliverableCandidate`, `CheapestToDeliverResult`, `delivery_payoff`, `cheapest_to_deliver`

### `pricers/rates/futures/delivery_option.py`

Delivery-option interfaces and deterministic CTD-switch models.

- Module path: `pricers/rates/futures/delivery_option.py`
- Top-level classes/functions: `_to_decimal`, `DeliveryOptionScenario`, `DeliveryOptionResult`, `_ScenarioCandidate`, `_scenario_equivalent_prices`, `DeliveryOptionModel`, `NoDeliveryOptionModel`, `YieldGridCTDSwitchModel`

### `pricers/rates/futures/delivery_option_models/__init__.py`

Stochastic delivery-option models for government bond futures.

- Module path: `pricers/rates/futures/delivery_option_models/__init__.py`
- Top-level classes/functions: none; this module primarily defines exports, imports, or package-level constants.

### `pricers/rates/futures/delivery_option_models/multi_factor.py`

Multi-factor stochastic delivery-option model.

- Module path: `pricers/rates/futures/delivery_option_models/multi_factor.py`
- Top-level classes/functions: `MultiFactorScenario`, `_ScenarioCandidate`, `_normalized_scenarios`, `_scenario_candidates_with_instrument_shifts`, `MultiFactorDeliveryOptionModel`

### `pricers/rates/futures/delivery_option_models/one_factor.py`

One-factor stochastic delivery-option model.

- Module path: `pricers/rates/futures/delivery_option_models/one_factor.py`
- Top-level classes/functions: `_normalize_probabilities`, `OneFactorDeliveryOptionModel`

### `pricers/rates/futures/invoice.py`

Invoice-price helpers for government bond futures.

- Module path: `pricers/rates/futures/invoice.py`
- Top-level classes/functions: `_to_decimal`, `InvoiceBreakdown`, `invoice_clean_price`, `invoice_price`, `invoice_amount`, `invoice_breakdown`

### `pricers/rates/futures/oabpv.py`

Option-adjusted fair-price and OABPV helpers for government bond futures.

- Module path: `pricers/rates/futures/oabpv.py`
- Top-level classes/functions: `_to_decimal`, `FairFuturesPriceResult`, `fair_futures_price`, `oabpv`

### `pricers/rates/inflation_swap_pricer.py`

Inflation swap pricing helpers.

- Module path: `pricers/rates/inflation_swap_pricer.py`
- Top-level classes/functions: `_to_decimal`, `InflationProjection`, `ZeroCouponInflationSwapPricingResult`, `StandardCouponInflationSwapPeriodPricing`, `StandardCouponInflationSwapPricingResult`, `InflationSwapPricer`

### `pricers/rates/options/__init__.py`

Rates option pricers and closed-form models.

- Module path: `pricers/rates/options/__init__.py`
- Top-level classes/functions: none; this module primarily defines exports, imports, or package-level constants.

### `pricers/rates/options/_common.py`

Shared helpers for rates option pricing.

- Module path: `pricers/rates/options/_common.py`
- Top-level classes/functions: `_year_fraction`, `_normal_cdf`, `_normal_pdf`, `_surface_from_inputs`, `_month_distance`, `_strike_distance`, `_resolve_surface_volatility`, `_time_to_expiry`, `_scale_greeks`, `_sum_greeks`, `OptionGreeks`, `OptionFormulaResult`, `SwaptionPricingResult`, `CapFloorletPricingResult`, `CapFloorPricingResult`, `FuturesOptionPricingResult`, `_CapFloorletInputs`, `swaption_context`, `cap_floor_context`, `futures_option_context`, `swaption_option_type`

### `pricers/rates/options/bachelier.py`

Bachelier option pricing for rates options.

- Module path: `pricers/rates/options/bachelier.py`
- Top-level classes/functions: `_intrinsic_value`, `_bachelier_price`, `bachelier_formula`, `BachelierPricer`

### `pricers/rates/options/black76.py`

Black-76 option pricing for rates options.

- Module path: `pricers/rates/options/black76.py`
- Top-level classes/functions: `_intrinsic_value`, `_black76_price`, `black76_formula`, `Black76Pricer`

### `pricers/rates/options/hull_white.py`

Transparent Hull-White style approximations for rates options.

- Module path: `pricers/rates/options/hull_white.py`
- Top-level classes/functions: `hull_white_normal_volatility`, `HullWhiteRateOptionModel`, `HullWhiteOptionPricer`

### `pricers/rates/risk/__init__.py`

Rates PV01 and key-rate algorithms.

- Module path: `pricers/rates/risk/__init__.py`
- Top-level classes/functions: none; this module primarily defines exports, imports, or package-level constants.

### `pricers/rates/risk/bpv.py`

Finite-difference PV01 helpers for rates products.

- Module path: `pricers/rates/risk/bpv.py`
- Top-level classes/functions: `_relevant_currency_and_indices`, `_pv`, `pv01`, `swap_pv01`, `fra_pv01`, `basis_swap_pv01`

### `pricers/rates/risk/key_rate.py`

Finite-difference key-rate helpers for rates products.

- Module path: `pricers/rates/risk/key_rate.py`
- Top-level classes/functions: `_coerce_tenor_grid`, `key_rate_risk`, `swap_key_rate_risk`, `fra_key_rate_risk`, `basis_swap_key_rate_risk`

### `pricers/rates/swap_pricer.py`

Swap pricing helpers.

- Module path: `pricers/rates/swap_pricer.py`
- Top-level classes/functions: `SwapPricingResult`, `SwapPricer`

## `products/`

Contract definitions and product-side domain objects.

### `products/__init__.py`

Primary product namespace for contract definitions.

- Module path: `products/__init__.py`
- Top-level classes/functions: none; this module primarily defines exports, imports, or package-level constants.

### `products/bonds/__init__.py`

Bond contract definitions, builders, and shared product-side helpers.

- Module path: `products/bonds/__init__.py`
- Top-level classes/functions: none; this module primarily defines exports, imports, or package-level constants.

### `products/bonds/cashflows/__init__.py`

Coupon schedule, accrued interest, and settlement helpers for bonds.

- Module path: `products/bonds/cashflows/__init__.py`
- Top-level classes/functions: none; this module primarily defines exports, imports, or package-level constants.

### `products/bonds/cashflows/accrued.py`

Accrued interest calculations (`fuggers_py.products.bonds.cashflows.accrued`).

- Module path: `products/bonds/cashflows/accrued.py`
- Top-level classes/functions: `AccruedInterestInputs`, `AccruedInterestCalculator`

### `products/bonds/cashflows/generator.py`

Cashflow generators (`fuggers_py.products.bonds.cashflows.generator`).

- Module path: `products/bonds/cashflows/generator.py`
- Top-level classes/functions: `CashFlowGenerator`

### `products/bonds/cashflows/schedule.py`

Coupon schedule generation (`fuggers_py.products.bonds.cashflows.schedule`).

- Module path: `products/bonds/cashflows/schedule.py`
- Top-level classes/functions: `ScheduleConfig`, `Schedule`, `_generate_backward`, `_generate_forward`

### `products/bonds/cashflows/settlement.py`

Settlement helpers (`fuggers_py.products.bonds.cashflows.settlement`).

- Module path: `products/bonds/cashflows/settlement.py`
- Top-level classes/functions: `SettlementCalculator`

### `products/bonds/instruments/__init__.py`

Bond instrument implementations and builders.

- Module path: `products/bonds/instruments/__init__.py`
- Top-level classes/functions: none; this module primarily defines exports, imports, or package-level constants.

### `products/bonds/instruments/callable.py`

Callable and puttable bond instruments.

- Module path: `products/bonds/instruments/callable.py`
- Top-level classes/functions: `_to_decimal`, `CallType`, `CallEntry`, `CallSchedule`, `CallableBond`, `CallableBondBuilder`

### `products/bonds/instruments/fixed.py`

Fixed-rate coupon bond (`fuggers_py.products.bonds.instruments.fixed`).

- Module path: `products/bonds/instruments/fixed.py`
- Top-level classes/functions: `_to_decimal`, `_shift_reference_date`, `_reference_period_bounds`, `FixedBond`, `FixedBondBuilder`

### `products/bonds/instruments/floating_rate.py`

Floating-rate note instruments.

- Module path: `products/bonds/instruments/floating_rate.py`
- Top-level classes/functions: `_to_decimal`, `ForwardRateSource`, `FloatingRateNote`, `FloatingRateNoteBuilder`

### `products/bonds/instruments/sinking_fund.py`

Sinking-fund bond instruments.

- Module path: `products/bonds/instruments/sinking_fund.py`
- Top-level classes/functions: `_to_decimal`, `SinkingFundEntry`, `SinkingFundSchedule`, `SinkingFundBond`, `SinkingFundBondBuilder`

### `products/bonds/instruments/tips.py`

Treasury Inflation-Protected Security instrument.

- Module path: `products/bonds/instruments/tips.py`
- Top-level classes/functions: `_inflation_index_type`, `TipsBond`

### `products/bonds/instruments/zero_coupon.py`

Zero-coupon bond instruments.

- Module path: `products/bonds/instruments/zero_coupon.py`
- Top-level classes/functions: `ZeroCouponBond`

### `products/bonds/traits/__init__.py`

Abstract bond interfaces and analytics mixins.

- Module path: `products/bonds/traits/__init__.py`
- Top-level classes/functions: none; this module primarily defines exports, imports, or package-level constants.

### `products/bonds/traits/analytics.py`

Analytics mixins (`fuggers_py.products.bonds.traits.analytics`).

- Module path: `products/bonds/traits/analytics.py`
- Top-level classes/functions: `BondAnalytics`

### `products/bonds/traits/bond.py`

Bond trait (`fuggers_py.products.bonds.traits.bond`).

- Module path: `products/bonds/traits/bond.py`
- Top-level classes/functions: `Bond`

### `products/bonds/traits/cashflow.py`

Bond cash-flow primitives (`fuggers_py.products.bonds.traits.cashflow`).

- Module path: `products/bonds/traits/cashflow.py`
- Top-level classes/functions: `CashFlowType`, `BondCashFlow`

### `products/bonds/traits/instruments.py`

Analytics-layer bond protocols.

- Module path: `products/bonds/traits/instruments.py`
- Top-level classes/functions: `FixedCouponBond`, `FloatingCouponBond`, `AmortizingBond`, `EmbeddedOptionBond`, `InflationLinkedBond`

### `products/credit/__init__.py`

Credit product definitions.

- Module path: `products/credit/__init__.py`
- Top-level classes/functions: none; this module primarily defines exports, imports, or package-level constants.

### `products/credit/cds.py`

Credit-default swap instruments.

- Module path: `products/credit/cds.py`
- Top-level classes/functions: `_to_decimal`, `_coerce_currency`, `_coerce_frequency`, `_coerce_day_count`, `_coerce_calendar`, `_coerce_business_day_convention`, `ProtectionSide`, `CdsPremiumPeriod`, `CreditDefaultSwap`

### `products/funding/__init__.py`

Funding product definitions.

- Module path: `products/funding/__init__.py`
- Top-level classes/functions: none; this module primarily defines exports, imports, or package-level constants.

### `products/funding/repo.py`

Repo trade instruments.

- Module path: `products/funding/repo.py`
- Top-level classes/functions: `_to_decimal`, `_coerce_day_count`, `RepoTrade`

### `products/rates/__init__.py`

Rates product definitions for swaps, FRAs, futures, and options.

- Module path: `products/rates/__init__.py`
- Top-level classes/functions: none; this module primarily defines exports, imports, or package-level constants.

### `products/rates/asset_swap.py`

Full asset-swap product definitions.

- Module path: `products/rates/asset_swap.py`
- Top-level classes/functions: `_to_decimal`, `AssetSwap`

### `products/rates/basis_swap.py`

Tradable same-currency basis swaps.

- Module path: `products/rates/basis_swap.py`
- Top-level classes/functions: `BasisSwap`

### `products/rates/common.py`

Common leg specifications for tradable rates products.

- Module path: `products/rates/common.py`
- Top-level classes/functions: `_to_decimal`, `_coerce_frequency`, `_coerce_calendar`, `_coerce_business_day_convention`, `_coerce_day_count`, `_coerce_currency`, `_coerce_tenor`, `PayReceive`, `AccrualPeriod`, `ScheduleDefinition`, `FixedLegSpec`, `FloatingLegSpec`

### `products/rates/cross_currency_basis.py`

Tradable cross-currency basis swaps.

- Module path: `products/rates/cross_currency_basis.py`
- Top-level classes/functions: `_to_decimal`, `CrossCurrencyBasisSwap`

### `products/rates/fixed_float_swap.py`

Tradable fixed-float swaps.

- Module path: `products/rates/fixed_float_swap.py`
- Top-level classes/functions: `FixedFloatSwap`

### `products/rates/fra.py`

Tradable forward-rate agreements.

- Module path: `products/rates/fra.py`
- Top-level classes/functions: `_to_decimal`, `_coerce_day_count`, `Fra`

### `products/rates/futures/__init__.py`

Rates futures product definitions.

- Module path: `products/rates/futures/__init__.py`
- Top-level classes/functions: none; this module primarily defines exports, imports, or package-level constants.

### `products/rates/futures/deliverable_basket.py`

Deliverable basket objects for government bond futures.

- Module path: `products/rates/futures/deliverable_basket.py`
- Top-level classes/functions: `_to_decimal`, `_coerce_currency`, `_coerce_frequency`, `_yield_compounding`, `DeliverableBond`, `DeliverableBasket`

### `products/rates/futures/government_bond_future.py`

Government bond futures contract objects.

- Module path: `products/rates/futures/government_bond_future.py`
- Top-level classes/functions: `_to_decimal`, `_coerce_frequency`, `GovernmentBondFuture`

### `products/rates/ois.py`

Tradable overnight indexed swaps.

- Module path: `products/rates/ois.py`
- Top-level classes/functions: `Ois`

### `products/rates/options/__init__.py`

Rates options product definitions.

- Module path: `products/rates/options/__init__.py`
- Top-level classes/functions: none; this module primarily defines exports, imports, or package-level constants.

### `products/rates/options/_common.py`

Shared option-domain helpers for rates options.

- Module path: `products/rates/options/_common.py`
- Top-level classes/functions: `_to_decimal`, `OptionType`

### `products/rates/options/cap_floor.py`

Cap/floor product definitions.

- Module path: `products/rates/options/cap_floor.py`
- Top-level classes/functions: `CapFloorType`, `CapFloor`

### `products/rates/options/futures_option.py`

Options on government bond futures.

- Module path: `products/rates/options/futures_option.py`
- Top-level classes/functions: `FuturesOption`

### `products/rates/options/swaption.py`

Swaption product definitions.

- Module path: `products/rates/options/swaption.py`
- Top-level classes/functions: `Swaption`

### `products/rates/standard_coupon_inflation_swap.py`

Standard coupon inflation swaps.

- Module path: `products/rates/standard_coupon_inflation_swap.py`
- Top-level classes/functions: `_to_decimal`, `_default_schedule_definition`, `StandardCouponInflationSwap`

### `products/rates/zero_coupon_inflation_swap.py`

Zero-coupon inflation swaps.

- Module path: `products/rates/zero_coupon_inflation_swap.py`
- Top-level classes/functions: `_to_decimal`, `ZeroCouponInflationSwap`

## `reference/`

Static reference data, conventions, metadata, and contract specifications.

### `reference/__init__.py`

Static reference data, conventions, metadata, and contract specs.

- Module path: `reference/__init__.py`
- Top-level classes/functions: `__getattr__`, `__dir__`

### `reference/bonds/__init__.py`

Bond reference conventions, identifiers, and classification types.

- Module path: `reference/bonds/__init__.py`
- Top-level classes/functions: none; this module primarily defines exports, imports, or package-level constants.

### `reference/bonds/conventions/__init__.py`

Bond market convention objects and registries.

- Module path: `reference/bonds/conventions/__init__.py`
- Top-level classes/functions: none; this module primarily defines exports, imports, or package-level constants.

### `reference/bonds/conventions/bond_conventions.py`

Bond market conventions (`fuggers_py.reference.bonds.conventions.bond_conventions`).

- Module path: `reference/bonds/conventions/bond_conventions.py`
- Top-level classes/functions: `BondConventions`

### `reference/bonds/conventions/eurobond.py`

Eurobond conventions.

- Module path: `reference/bonds/conventions/eurobond.py`
- Top-level classes/functions: `eurobond_rules`

### `reference/bonds/conventions/german_bund.py`

German Bund conventions.

- Module path: `reference/bonds/conventions/german_bund.py`
- Top-level classes/functions: `german_bund_rules`

### `reference/bonds/conventions/japanese_jgb.py`

Japanese JGB conventions.

- Module path: `reference/bonds/conventions/japanese_jgb.py`
- Top-level classes/functions: `japanese_jgb_rules`

### `reference/bonds/conventions/market.py`

Bond market identifiers for convention lookup.

- Module path: `reference/bonds/conventions/market.py`
- Top-level classes/functions: `BondMarket`

### `reference/bonds/conventions/registry.py`

Convention registry and builder helpers.

- Module path: `reference/bonds/conventions/registry.py`
- Top-level classes/functions: `BondConventionRegistry`, `BondConventionsBuilder`

### `reference/bonds/conventions/uk_gilt.py`

UK gilt conventions.

- Module path: `reference/bonds/conventions/uk_gilt.py`
- Top-level classes/functions: `uk_gilt_rules`

### `reference/bonds/conventions/us_corporate.py`

US corporate bond conventions.

- Module path: `reference/bonds/conventions/us_corporate.py`
- Top-level classes/functions: `us_corporate_rules`

### `reference/bonds/conventions/us_treasury.py`

US Treasury conventions.

- Module path: `reference/bonds/conventions/us_treasury.py`
- Top-level classes/functions: `us_treasury_rules`

### `reference/bonds/errors.py`

Bond-layer exceptions (`fuggers_py.reference.bonds.errors`).

- Module path: `reference/bonds/errors.py`
- Top-level classes/functions: `BondError`, `IdentifierError`, `InvalidIdentifier`, `InvalidBondSpec`, `MissingRequiredField`, `BondPricingError`, `YieldConvergenceFailed`, `ScheduleError`, `SettlementError`

### `reference/bonds/types/__init__.py`

Bond-domain enums, identifiers, and rule objects.

- Module path: `reference/bonds/types/__init__.py`
- Top-level classes/functions: none; this module primarily defines exports, imports, or package-level constants.

### `reference/bonds/types/amortization.py`

Amortization schedule helpers.

- Module path: `reference/bonds/types/amortization.py`
- Top-level classes/functions: `_to_decimal`, `AmortizationType`, `AmortizationEntry`, `AmortizationSchedule`

### `reference/bonds/types/asw.py`

Shared asset-swap enum types.

- Module path: `reference/bonds/types/asw.py`
- Top-level classes/functions: `ASWType`

### `reference/bonds/types/bond_type.py`

Bond type enum (`fuggers_py.reference.bonds.types.bond_type`).

- Module path: `reference/bonds/types/bond_type.py`
- Top-level classes/functions: `BondType`

### `reference/bonds/types/compounding.py`

Compounding methods for yield engines (`fuggers_py.reference.bonds.types.compounding`).

- Module path: `reference/bonds/types/compounding.py`
- Top-level classes/functions: `CompoundingKind`, `CompoundingMethod`

### `reference/bonds/types/ex_dividend.py`

Ex-dividend rules (`fuggers_py.reference.bonds.types.ex_dividend`).

- Module path: `reference/bonds/types/ex_dividend.py`
- Top-level classes/functions: `ExDividendRules`

### `reference/bonds/types/identifiers.py`

Identifiers and calendar ids (`fuggers_py.reference.bonds.types.identifiers`).

- Module path: `reference/bonds/types/identifiers.py`
- Top-level classes/functions: `_base36_value`, `_luhn_is_valid`, `_isin_digits`, `_cusip_check_digit`, `_sedol_check_digit`, `_normalize_calendar_id`, `_clean_id`, `Isin`, `Cusip`, `Sedol`, `Figi`, `BondIdentifiers`, `CalendarId`

### `reference/bonds/types/inflation.py`

Inflation-linked bond compatibility surface.

- Module path: `reference/bonds/types/inflation.py`
- Top-level classes/functions: `InflationIndexType`, `InflationIndexReference`

### `reference/bonds/types/options.py`

Embedded put option schedule helpers.

- Module path: `reference/bonds/types/options.py`
- Top-level classes/functions: `_to_decimal`, `PutType`, `PutEntry`, `PutSchedule`

### `reference/bonds/types/price_quote.py`

Price quotes (`fuggers_py.reference.bonds.types.price_quote`).

- Module path: `reference/bonds/types/price_quote.py`
- Top-level classes/functions: `PriceQuoteConvention`, `PriceQuote`

### `reference/bonds/types/rate_index.py`

Reference rate indices (`fuggers_py.reference.bonds.types.rate_index`).

- Module path: `reference/bonds/types/rate_index.py`
- Top-level classes/functions: `RateIndex`

### `reference/bonds/types/rating.py`

Credit rating compatibility types.

- Module path: `reference/bonds/types/rating.py`
- Top-level classes/functions: `CreditRating`, `RatingInfo`

### `reference/bonds/types/sector.py`

Sector compatibility types.

- Module path: `reference/bonds/types/sector.py`
- Top-level classes/functions: `Sector`, `SectorInfo`

### `reference/bonds/types/seniority.py`

Seniority compatibility types.

- Module path: `reference/bonds/types/seniority.py`
- Top-level classes/functions: `Seniority`, `SeniorityInfo`

### `reference/bonds/types/settlement_rules.py`

Settlement rules (`fuggers_py.reference.bonds.types.settlement_rules`).

- Module path: `reference/bonds/types/settlement_rules.py`
- Top-level classes/functions: `SettlementAdjustment`, `SettlementRules`

### `reference/bonds/types/sofr_convention.py`

SOFR-specific convention helpers.

- Module path: `reference/bonds/types/sofr_convention.py`
- Top-level classes/functions: `SOFRConvention`

### `reference/bonds/types/stub_rules.py`

Stub period rules (`fuggers_py.reference.bonds.types.stub_rules`).

- Module path: `reference/bonds/types/stub_rules.py`
- Top-level classes/functions: `StubType`, `StubPeriodRules`

### `reference/bonds/types/tenor.py`

Tenor helpers (`fuggers_py.reference.bonds.types.tenor`).

- Module path: `reference/bonds/types/tenor.py`
- Top-level classes/functions: `TenorUnit`, `Tenor`

### `reference/bonds/types/yield_convention.py`

Yield and accrued conventions (`fuggers_py.reference.bonds.types.yield_convention`).

- Module path: `reference/bonds/types/yield_convention.py`
- Top-level classes/functions: `YieldConvention`, `AccruedConvention`, `RoundingKind`, `RoundingConvention`

### `reference/bonds/types/yield_rules.py`

Yield calculation rules (`fuggers_py.reference.bonds.types.yield_rules`).

- Module path: `reference/bonds/types/yield_rules.py`
- Top-level classes/functions: `_day_count`, `YieldCalculationRules`

### `reference/inflation/__init__.py`

Inflation conventions, reference-index helpers, and Treasury data loaders.

- Module path: `reference/inflation/__init__.py`
- Top-level classes/functions: none; this module primarily defines exports, imports, or package-level constants.

### `reference/inflation/conventions.py`

Shared inflation-index definitions and built-in conventions.

- Module path: `reference/inflation/conventions.py`
- Top-level classes/functions: `_normalize_aliases`, `InflationConvention`

### `reference/inflation/errors.py`

Exception hierarchy for inflation reference-data and index-resolution helpers.

- Module path: `reference/inflation/errors.py`
- Top-level classes/functions: `InflationError`, `InvalidObservationLag`, `UnsupportedInflationInterpolation`, `MissingInflationFixing`

### `reference/inflation/reference_index.py`

Daily reference-index helpers built from monthly inflation fixings.

- Module path: `reference/inflation/reference_index.py`
- Top-level classes/functions: `_year_month`, `_resolve_fixing_source`, `_validate_observation_lag`, `_lookup_fixing`, `_require_fixings`, `reference_cpi`, `reference_index_ratio`

### `reference/inflation/treasury_auction_data.py`

Treasury auctioned-security adapters for TIPS instrument metadata.

- Module path: `reference/inflation/treasury_auction_data.py`
- Top-level classes/functions: `_normalize_key`, `_normalize_row`, `_require_value`, `_optional_value`, `_parse_date`, `_parse_decimal`, `_is_tips_row`, `TreasuryAuctionedTipsRow`, `_row_from_normalized_payload`, `parse_treasury_auctioned_tips_json`, `parse_treasury_auctioned_tips_csv`, `load_treasury_auctioned_tips_json`, `load_treasury_auctioned_tips_csv`, `tips_bond_from_treasury_auction_row`

### `reference/inflation/treasury_data.py`

Deterministic monthly CPI adapters for fixture-driven inflation workflows.

- Module path: `reference/inflation/treasury_data.py`
- Top-level classes/functions: `_normalize_key`, `_normalize_row`, `_resolve_month`, `_require_row_value`, `_fixing_from_normalized_row`, `parse_monthly_cpi_fixings_csv`, `parse_monthly_cpi_fixings_json`, `load_monthly_cpi_fixings_csv`, `load_monthly_cpi_fixings_json`, `parse_bls_cpi_json`, `parse_fred_cpi_csv`, `treasury_cpi_source_from_fixings`

### `reference/reference_data.py`

Reference-data records for research workflows.

- Module path: `reference/reference_data.py`
- Top-level classes/functions: `_to_decimal`, `_coerce_frequency`, `BondType`, `IssuerType`, `CallScheduleEntry`, `FloatingRateTerms`, `BondReferenceData`, `BondFutureReferenceData`, `DeliverableBondReference`, `SwapReferenceData`, `RepoReferenceData`, `CdsReferenceData`, `IssuerReferenceData`, `RatingRecord`, `BondReferenceSource`, `IssuerReferenceSource`, `RatingSource`, `EtfHoldingsSource`, `ReferenceDataProvider`
