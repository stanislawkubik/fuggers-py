# Changelog

## Unreleased

No unreleased changes yet.

## 0.3.0 - 2026-04-26

### Breaking

- The public imports now use the first-layer packages:
  `curves`, `vol_surfaces`, `bonds`, `rates`, `inflation`, `credit`,
  `funding`, and `portfolio`.
- Removed the old public roots for market, product, pricer, measure,
  reference, engine, adapter, core, and math code.
- Shared types now come from `fuggers_py`. Domain objects come from their
  domain package. Internal math, runtime, and storage code stays private.
- Removed the temporary package buckets used during the API cleanup.

### Changed

- Documented the current project state. `fuggers_py.curves` and
  `YieldCurve.fit(...)` are closest to the intended `1.x` shape. The other
  domain packages are usable, but still need cleanup before `1.0`.
- Rewrote the public API docs around the first-layer package layout.
- Moved bond instruments, pricing, risk, spreads, yields, relative value, and
  YAS-style analytics under `fuggers_py.bonds`.
- Moved swaps, FRAs, bond futures, rates options, rate quotes, index rules,
  fixing stores, and rates risk under `fuggers_py.rates`.
- Moved CPI data, inflation swaps, inflation pricing, TIPS helpers, and
  inflation analytics under `fuggers_py.inflation`.
- Moved CDS instruments, CDS data, CDS quotes, CDS pricing, CDS risk, and
  bond-CDS basis analytics under `fuggers_py.credit`.
- Moved repo trades, repo data, repo quotes, haircut quotes, implied repo,
  carry, financing cost, haircut, and specialness helpers under
  `fuggers_py.funding`.
- Moved portfolio holdings, analytics, benchmarks, contribution, bucketing,
  ETF workflows, liquidity, and stress helpers under `fuggers_py.portfolio`.
- Kept the curve root focused on `CurveSpec`, `YieldCurve`, curve base types,
  calibration reports, and `STANDARD_KEY_RATE_TENORS`.
- Curve moves now live on `DiscountingCurve.shifted(...)` and
  `DiscountingCurve.bumped(...)`.
- Advanced curve fit settings now live in curve submodules.
- Kept volatility surface records, points, and data sources under
  `fuggers_py.vol_surfaces`.
- Replaced the temporary API cleanup tooling with normal tests and validation
  commands.
- Made `YieldCurve.fit(...)` the main public entry point for fitting curves
  from quotes.
- Added fitting support for `SwapQuote`, `BondQuote`, and `RepoQuote`.
- `BondQuote` now belongs to one concrete bond. It uses the bond id, bond
  currency, and `as_of` date during fitting.
- Refreshed the curve, bond, rates, funding, API index, source-structure, and
  validation docs.
- Trimmed the Treasury curve-fitting example so it focuses on curve recovery,
  curve moves, and regressor checks.

## 0.2.3

First public release of `fuggers-py`.

This release opens the repository to the public as a pre-`1.0` beta. The
library already covers a broad fixed-income surface, but some APIs may still
change before `1.0`.

### Changed

- Made the GitHub repository and Read the Docs site public.
- Linked the live docs from the README and package metadata.
- Expanded the published API docs for the main public packages.
- Improved docstrings for pricing outputs, routers, measures, portfolio
  analytics, and credit/rates risk.
- Made unsuffixed current yields, G-spreads, and I-spreads use raw decimal
  units. Added `_pct` and `_bps` helpers for display values.
- Made `dv01` the main first-order risk name. Kept `pv01` aliases and the
  rates-side `bpv` name for compatibility.
- Fixed bond-router benchmark tenor handling and asset-swap spread scaling.
- Cleaned up calculation output records and documentation setup.
- Added a plain-language project status note for the pre-`1.0` API state.

## 0.2.0

Internal milestone focused on inflation analytics before the public repository launch.

### Added

- `inflation`: USD CPI-U NSA rules, daily reference-index logic, projected
  inflation-index curves, zero-coupon inflation-swap bootstrap, CPI history
  adapters, TIPS metadata adapters, and small breakeven/parity helpers.
- `bonds`: `TipsBond` cash flows, real-yield pricing, clean/dirty price
  handling, accrued interest, and real-yield risk.
- `rates`: zero-coupon and coupon inflation swaps with pricing, par rate, and
  PV01 support.
- Inflation routing across bond and rates workflows.

### Changed

- Added docs, examples, and tests for CPI fixing data, TIPS pricing,
  inflation-swap pricing, inflation-curve bootstrap, and official-source data
  adapters.
- Split CPI history parsing from Treasury auctioned-security TIPS metadata
  parsing.
- Updated public inflation examples to use BLS/FRED CPI inputs, Treasury TIPS
  metadata, Treasury nominal/real curve references, and FRED breakeven data.

## 0.1.0

Internal milestone before the public repository launch.

### Changed

- Added and normalized NumPy-style docstrings across the public package.
- Aligned package docs for `core`, `math`, `curves`, `bonds`, `rates`,
  `funding`, `credit`, `analytics`, `portfolio`, `data`, `io`, and `engine`.
- Clarified shared conventions for decimals, percent-of-par values, basis
  points, settlement dates, clean/dirty prices, curve dates, and risk/spread
  signs.
- Hardened the release path for version checks, editable installs, build
  artifacts, wheels, source distributions, and the `v0.1.0` tag.
- Refreshed the README and domain docs so they match the public API.

## 0.1.0b2

Second beta cut focused on the expanded relative-value and cross-asset fixed-income stack, plus release engineering cleanup ahead of publication.

### Added

- Expanded relative-value analytics for local, global, and desk-style
  comparisons.
- `funding`: repo trades, repo curves, implied repo, specialness, haircuts,
  and a funding pricing router.
- `rates`: IRS, OIS, FRAs, basis swaps, asset swaps, cross-currency basis
  swaps, and rates risk helpers.
- Government bond futures tools for contracts, deliverable baskets, conversion
  factors, CTD selection, invoice, basis, delivery-option models, and OABPV.
- Fitted-bond curve fitting, fair-value outputs, benchmark generation, bond
  switches, butterflies, and constant-maturity analytics.
- `credit`: CDS products, bootstrap, pricing, adjusted CDS helpers, bond/CDS
  basis, and proxy risk-free analytics.
- Options support for swaptions, caps/floors, futures options, Greeks, options
  relative value, overlays, and advanced curve-model integrations.

### Changed

- Source-coverage checks now track the top-level package surface.
- Local release builds now document `python -m build` and `pip wheel`.
- Packaging tests now check that build outputs, installed package metadata, and
  `fuggers_py.__version__` stay aligned.

## 0.1.0b1

Initial release-focused cut of the Python analytics port.

### Added

- `core`: dates, prices, yields, spreads, calendars, day counts, and base
  curve/pricing/risk types.
- `math`: solvers, interpolation, extrapolation, optimization, and linear
  algebra helpers.
- `curves`: curve objects, builders, calibration helpers, bumping, and
  multi-curve support.
- `bonds`: fixed-rate, zero-coupon, callable/putable, floating-rate,
  sinking-fund, index/fixing, and option-model workflows.
- `analytics`: yield, risk, spread, OAS, discount-margin, asset-swap, and YAS
  calculations.
- `portfolio`: holdings, ETF helpers, aggregation, stress, benchmarks, credit,
  and key-rate tools.
- `data`: typed ids, market/reference data, pricing specs, outputs, and
  in-memory research providers.
- `io`: file-backed providers, JSON codecs, SQLite storage, and
  storage/transport interfaces.
- `engine`: pricing router, batch pricing, curve builder, calculation graph,
  schedulers, market-data listener, and builder workflows.
- Deterministic examples, validation fixtures, benchmarks, and release smoke
  tests.

### Scope

- This package targets Python analytics and research workflows.
- Deterministic local adapters and notebook-friendly APIs are first-class.
- Server runtimes, WASM, FFI bindings, MCP surfaces, and distributed services
  are out of scope for this release.

### Changed

- Removed old compatibility namespaces such as `fuggers_py.prelude`,
  `fuggers_py.traits`, and `fuggers_py.ext`.
- Removed the redundant top-level `fuggers_py.spreads` namespace.
- `fuggers_py.measures.spreads` is the spread namespace.
