# Developer Internal Modules

This page describes implementation modules that are not public API.

User code should import from the root package or from the first-layer public
packages listed in [API guide](../api/index.md). The modules listed here support
those public packages. They can move when the implementation changes.

## Public Boundary

The public import story has two levels:

- `fuggers_py` exposes shared language used across the whole library.
- `fuggers_py.<domain>` exposes one domain package, such as `bonds`, `rates`,
  `curves`, or `portfolio`.

Everything below is internal:

- Root packages whose names start with `_`, such as `fuggers_py._core`.
- Helper files or folders inside a public package whose names start with `_`,
  such as `bonds/_spreads/`.
- Generated support files such as `_version.py`.

Do not document internal modules as user-facing imports. Do not add wrappers
whose only job is to keep an old import path alive.

## Ownership Rules

Use the smallest owner that matches the code:

- Put shared fixed-income language in `_core`.
- Put generic numerical routines in `_math`.
- Put engine coordination and market-data runtime code in `_runtime`.
- Put persistence, codecs, and transport helpers in `_storage`.
- Put product-specific helpers inside the public package that owns the product.
- Put portfolio-only helpers inside `portfolio/`.

When a name becomes public, expose it through one public package only:

- `fuggers_py` for shared language used across the whole library.
- `fuggers_py.curves` for curve objects and curve fitting.
- `fuggers_py.vol_surfaces` for volatility surface records and sources.
- `fuggers_py.bonds` for bond instruments, reference data, analytics, and risk.
- `fuggers_py.rates` for rates instruments, rates quotes, fixing data, pricing, and risk.
- `fuggers_py.inflation` for CPI data, inflation products, and inflation analytics.
- `fuggers_py.credit` for CDS and bond-CDS analytics.
- `fuggers_py.funding` for repo, haircut, and financing analytics.
- `fuggers_py.portfolio` for holdings, portfolio analytics, and portfolio workflows.

## Module Hardening Standard

Use `fuggers_py.curves` as the current model for public package shape.

A hardened domain package should have:

- one small public root with the names users need most often
- private or focused submodules for advanced records and implementation details
- one obvious public workflow for the common task, such as `YieldCurve.fit(...)`
- clear ownership of quotes, products, pricing, risk, reports, and errors
- inheritance only where shared behavior is real and easy to follow
- no compatibility wrappers whose only job is to keep an old path alive
- no enum or type record unless it prevents unclear inputs or repeated checks

The next pre-`1.x` hardening pass should review `bonds`, `rates`, `funding`,
`credit`, `inflation`, and `portfolio` against this standard. These packages are
usable now, but they still carry broader public roots, older local type records,
and enum-heavy areas that should be simplified before the compatibility promise.

## Import Rules

Internal code can import inward to shared helpers. Public package entry points
should stay shallow.

- Public docs should show imports from `fuggers_py` or one first-layer public
  package.
- Public package `__init__.py` files should re-export concrete public names
  directly. They should not use lazy import routing.
- Domain modules can import from `_core` and `_math`.
- Domain modules should not import from `_runtime` or `_storage` unless the
  domain explicitly owns an engine or IO workflow.
- `portfolio` may combine objects from other public packages.
- Other public packages should not import from `portfolio`.
- Internal helpers inside one public package should not become cross-package
  utility buckets. Move shared non-domain code to `_core` or `_math`.

## Error Rules

Every library exception should inherit from the shared root exception in
`_core/errors.py`.

- Shared primitive errors live in `_core/errors.py`.
- Numerical errors live in `_math/errors.py`.
- Engine errors live in `_runtime/errors.py`.
- Package-specific errors live in that package's `errors.py`.
- Narrow subpackage errors can live in a focused `errors.py`, such as
  `bonds/options/errors.py`.
- Feature modules should import exception classes from an error module. They
  should not define library exception classes inline.

## Type And Value Rules

Use `_core` for values that appear across several public packages.

- Dates, currencies, identifiers, prices, yields, spreads, tenors, calendars,
  day-counts, and shared quote helpers belong in `_core`.
- Values tied to one product family belong in that product package.
- A type that starts as bond-only should stay in `bonds/` until another package
  needs the same concept.
- Do not duplicate shared value objects to avoid importing `_core`.

## Numerical Rules

Use `_math` for calculation machinery that has no product meaning by itself.

- Interpolation and extrapolation routines belong in `_math`.
- Solvers and optimizers belong in `_math`.
- Curve objects, curve specs, calibration records, and curve reports belong in
  `curves`, because those names are part of the public API.
- Product pricing logic belongs in the package that owns the product.

## Runtime And Storage Rules

Use `_runtime` for work coordination and `_storage` for IO.

- `_runtime` can assemble engines, track dependencies, schedule work, keep
  market state, and route pricing requests.
- `_storage` can load files, encode JSON, save to SQLite, store portfolios, and
  describe transport interfaces.
- Public packages should expose domain records and workflows, not storage
  internals.
- Keep file formats and persistence choices out of product constructors unless
  the product workflow needs them.

## Testing And Docs Rules

Internal modules need tests, but the public API docs should stay clean.

- Unit tests may import internal modules when they test internal behavior.
- Contract tests should assert the public API shape through first-layer
  packages.
- Public API docs live under `docs/api/`.
- Internal implementation docs live under `docs/dev/`.
- Source-tree inventory lives in `docs/SRC_STRUCTURE.md`.
- If a private helper becomes public, update the package API docs, export
  tests, typecheck files, and changelog in the same change.

## Internal Root Inventory

The four internal survivor roots are `_core`, `_math`, `_runtime`, and
`_storage`.

### `fuggers_py._core`

`_core` stores shared fixed-income language and primitive support code.

| Path | Purpose |
| --- | --- |
| `_core/__init__.py` | Internal aggregate for shared primitive names. |
| `_core/calendar_id.py` | Calendar identifiers used by calendars and schedules. |
| `_core/calendars.py` | Business-day calendars and date adjustment. |
| `_core/compounding.py` | Shared compounding convention values. |
| `_core/daycounts.py` | Day-count conventions and year fractions. |
| `_core/errors.py` | Shared exception root and primitive errors. |
| `_core/ex_dividend.py` | Ex-dividend convention values. |
| `_core/ids.py` | Shared typed identifiers for instruments, curves, portfolios, and surfaces. |
| `_core/option_type.py` | Shared option-side values. |
| `_core/pay_receive.py` | Shared pay/receive direction values. |
| `_core/quote_support.py` | Shared quote-side and quote-value helpers. |
| `_core/reference.py` | Shared reference-data base records and source interfaces. |
| `_core/settlement_rules.py` | Settlement lag and adjustment rules. |
| `_core/stub_rules.py` | Stub-period convention values. |
| `_core/tenor.py` | Tenor values and tenor parsing. |
| `_core/traits.py` | Shared structural protocols used by domains. |
| `_core/types.py` | Dates, currencies, prices, yields, spreads, and cashflow records. |
| `_core/yield_calculation_rules.py` | Shared yield calculation rule records. |
| `_core/yield_convention.py` | Shared yield convention values. |

### `fuggers_py._math`

`_math` stores numerical tools used by curves and product analytics.

| Path | Purpose |
| --- | --- |
| `_math/__init__.py` | Internal aggregate for numerical helpers. |
| `_math/errors.py` | Numerical exception hierarchy. |
| `_math/numerical.py` | Small numerical guard functions and constants. |
| `_math/utils.py` | Generic numerical utility helpers. |
| `_math/extrapolation/__init__.py` | Internal aggregate for extrapolation policies. |
| `_math/extrapolation/base.py` | Base extrapolation interface. |
| `_math/extrapolation/flat.py` | Flat extrapolation policy. |
| `_math/extrapolation/linear.py` | Linear extrapolation policy. |
| `_math/extrapolation/smith_wilson.py` | Smith-Wilson extrapolation support. |
| `_math/interpolation/__init__.py` | Internal aggregate for interpolation routines. |
| `_math/interpolation/base.py` | Base interpolation interface. |
| `_math/interpolation/cubic_spline.py` | Cubic-spline interpolation. |
| `_math/interpolation/flat_forward.py` | Flat-forward interpolation. |
| `_math/interpolation/linear.py` | Linear interpolation. |
| `_math/interpolation/log_linear.py` | Log-linear interpolation. |
| `_math/interpolation/monotone_convex.py` | Monotone-convex interpolation. |
| `_math/interpolation/parametric.py` | Parametric curve-shape helpers. |
| `_math/linear_algebra/__init__.py` | Internal aggregate for linear-algebra helpers. |
| `_math/linear_algebra/lu.py` | LU decomposition helpers. |
| `_math/linear_algebra/solve.py` | Small linear-system solve helpers. |
| `_math/linear_algebra/tridiagonal.py` | Tridiagonal-system helpers. |
| `_math/optimization/__init__.py` | Internal aggregate for optimizers. |
| `_math/optimization/gradient_descent.py` | Gradient-descent optimizer. |
| `_math/optimization/least_squares.py` | Least-squares optimizer. |
| `_math/optimization/types.py` | Optimizer input and result records. |
| `_math/solvers/__init__.py` | Internal aggregate for one-dimensional solvers. |
| `_math/solvers/bisection.py` | Bisection root solver. |
| `_math/solvers/brent.py` | Brent root solver. |
| `_math/solvers/hybrid.py` | Hybrid root solver. |
| `_math/solvers/newton.py` | Newton root solver. |
| `_math/solvers/secant.py` | Secant root solver. |
| `_math/solvers/types.py` | Solver input and result records. |

### `fuggers_py._runtime`

`_runtime` stores pricing-engine coordination code.

| Path | Purpose |
| --- | --- |
| `_runtime/__init__.py` | Internal aggregate for runtime helpers. |
| `_runtime/_shared.py` | Runtime-only shared helper records. |
| `_runtime/builder.py` | Engine assembly helpers. |
| `_runtime/calc_graph.py` | Dependency graph for calculated values. |
| `_runtime/config.py` | Runtime configuration records. |
| `_runtime/coordination.py` | Service coordination helpers. |
| `_runtime/errors.py` | Runtime exception hierarchy. |
| `_runtime/market_data_listener.py` | Market-data listener interfaces. |
| `_runtime/output.py` | Runtime output records and publishers. |
| `_runtime/pricing_router.py` | Routing from pricing requests to pricing functions. |
| `_runtime/pricing_specs.py` | Typed pricing request records. |
| `_runtime/quotes.py` | Runtime quote records. |
| `_runtime/reactive.py` | Reactive update propagation. |
| `_runtime/scheduler.py` | Scheduling helpers. |
| `_runtime/snapshot.py` | Market snapshot records. |
| `_runtime/sources.py` | Runtime market-data source interfaces. |
| `_runtime/state.py` | Runtime market state containers. |

### `fuggers_py._storage`

`_storage` stores persistence, file, codec, and transport helpers.

| Path | Purpose |
| --- | --- |
| `_storage/__init__.py` | Internal aggregate for storage helpers. |
| `_storage/file.py` | File-backed loaders, sources, and output publishers. |
| `_storage/json_codec.py` | JSON encoding and decoding helpers. |
| `_storage/portfolio_store.py` | Portfolio persistence helpers. |
| `_storage/sqlite_storage.py` | SQLite-backed storage implementation. |
| `_storage/storage.py` | Storage protocols and shared storage records. |
| `_storage/transport.py` | Transport and cache interfaces for remote or deferred IO. |

## Private Helpers Inside Public Packages

These helpers are private because the package exports the public names from its
first-layer package. Use paths in developer docs and tests. Do not tell users to
import these modules directly.

### Bonds helpers

| Path | Purpose |
| --- | --- |
| `bonds/_instrument_base.py` | Shared implementation for bond instrument classes. |
| `bonds/_pricing_pricer.py` | Bond pricing implementation behind `bonds/pricing.py`. |
| `bonds/_pricing_risk.py` | Bond risk implementation behind `bonds/risk.py`. |
| `bonds/_pricing_yield_engine.py` | Bond yield engine implementation. |
| `bonds/_spreads/adjustments/balance_sheet.py` | Balance-sheet spread adjustments. |
| `bonds/_spreads/adjustments/capital.py` | Capital spread adjustments. |
| `bonds/_spreads/adjustments/haircuts.py` | Haircut spread adjustments. |
| `bonds/_spreads/adjustments/shadow_cost.py` | Shadow-cost spread adjustments. |
| `bonds/_spreads/asw/par_par.py` | Par-par asset-swap implementation. |
| `bonds/_spreads/asw/proceeds.py` | Proceeds asset-swap implementation. |
| `bonds/_spreads/benchmark.py` | Benchmark selection for spread calculations. |
| `bonds/_spreads/compounding_convexity.py` | Compounding and convexity spread adjustments. |
| `bonds/_spreads/discount_margin.py` | Discount-margin calculations. |
| `bonds/_spreads/government_curve.py` | Government benchmark curve helpers. |
| `bonds/_spreads/gspread.py` | G-spread calculations. |
| `bonds/_spreads/ispread.py` | I-spread calculations. |
| `bonds/_spreads/oas.py` | Option-adjusted spread calculations. |
| `bonds/_spreads/reference_rates.py` | Reference-rate decomposition helpers. |
| `bonds/_spreads/secured_unsecured_basis.py` | Secured versus unsecured basis helpers. |
| `bonds/_spreads/sovereign.py` | Sovereign benchmark helpers. |
| `bonds/_spreads/zspread.py` | Z-spread calculations. |
| `bonds/_types/amortization.py` | Legacy-local amortization type support behind public bond exports. |
| `bonds/_types/asw.py` | Legacy-local asset-swap type support behind public bond exports. |
| `bonds/_types/compounding.py` | Legacy-local compounding type support behind public bond exports. |
| `bonds/_types/ex_dividend.py` | Legacy-local ex-dividend type support behind public bond exports. |
| `bonds/_types/identifiers.py` | Legacy-local identifier type support behind public bond exports. |
| `bonds/_types/inflation.py` | Legacy-local inflation-linked bond type support behind public bond exports. |
| `bonds/_types/options.py` | Legacy-local option type support behind public bond exports. |
| `bonds/_types/price_quote.py` | Legacy-local price quote type support behind public bond exports. |
| `bonds/_types/rate_index.py` | Legacy-local rate-index type support behind public bond exports. |
| `bonds/_types/rating.py` | Legacy-local rating type support behind public bond exports. |
| `bonds/_types/sector.py` | Legacy-local sector type support behind public bond exports. |
| `bonds/_types/seniority.py` | Legacy-local seniority type support behind public bond exports. |
| `bonds/_types/settlement_rules.py` | Legacy-local settlement-rule support behind public bond exports. |
| `bonds/_types/sofr_convention.py` | Legacy-local SOFR convention support behind public bond exports. |
| `bonds/_types/stub_rules.py` | Legacy-local stub-rule support behind public bond exports. |
| `bonds/_types/tenor.py` | Legacy-local tenor support behind public bond exports. |
| `bonds/_types/yield_convention.py` | Legacy-local yield convention support behind public bond exports. |
| `bonds/_types/yield_rules.py` | Legacy-local yield-rule support behind public bond exports. |
| `bonds/_yas/analysis.py` | YAS-style analysis implementation. |
| `bonds/_yas/calculator.py` | YAS-style calculator implementation. |
| `bonds/_yas/invoice.py` | YAS-style settlement invoice implementation. |
| `bonds/_yields/bond.py` | Bond yield helpers. |
| `bonds/_yields/current.py` | Current-yield helpers. |
| `bonds/_yields/engine.py` | Yield engine helpers. |
| `bonds/_yields/money_market.py` | Money-market yield helpers. |
| `bonds/_yields/short_date.py` | Short-date yield helpers. |
| `bonds/_yields/simple.py` | Simple-yield helpers. |
| `bonds/_yields/solver.py` | Yield solver helpers. |
| `bonds/_yields/street.py` | Street-convention yield helpers. |
| `bonds/_yields/true_yield.py` | True-yield helpers. |
| `bonds/rv/_fit_result.py` | Private fit result used by bond relative-value workflows. |

### Curves helpers

| Path | Purpose |
| --- | --- |
| `curves/_day_count.py` | Day-count lookup helper used by curve fitting and bond quote normalization. |
| `curves/calibrators/_quotes.py` | Quote normalization helpers used by curve calibrators. |

### Portfolio helpers

| Path | Purpose |
| --- | --- |
| `portfolio/_analytics_utils.py` | Shared helpers used by portfolio analytics modules. |

### Rates helpers

| Path | Purpose |
| --- | --- |
| `rates/_curve_resolver.py` | Curve lookup and fallback logic used by rates pricing. |
| `rates/options/_pricing_common.py` | Shared option pricing helpers. |
| `rates/options/_product_common.py` | Shared option product helpers. |

## Generated And Packaging Support

| Path | Purpose |
| --- | --- |
| `_version.py` | Generated package version metadata. Do not edit by hand. |
| `py.typed` | Marker file that tells type checkers this package ships type hints. |

## Change Checklist

Use this checklist before adding or moving internal code:

- The module has one clear owner.
- Public users can still import from the root package or one first-layer public package.
- No compatibility wrapper keeps an old path alive.
- Exceptions live in the right `errors.py` file.
- Shared value objects are not duplicated across packages.
- Product-specific code stays with the product package.
- Numerical machinery without product meaning stays in `_math`.
- Runtime coordination stays in `_runtime`.
- Persistence and IO helpers stay in `_storage`.
- Public docs, dev docs, contracts, typecheck files, and changelog stay aligned.
