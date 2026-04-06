# Changelog

## Unreleased

### Changed

- normalized public unsuffixed current yields, G-spreads, and I-spreads to raw decimal units and added explicit `_pct` and `_bps` display helpers
- made `dv01` the canonical first-order risk name across shared outputs while keeping symmetric `pv01` aliases and rates-side `bpv` compatibility
- corrected bond-router benchmark tenor handling, asset-swap spread scaling, and consolidated calc DTOs plus RTD/Sphinx documentation scaffolding
- added a plain-language project status note and documented that pre-`1.0` APIs are still allowed to change before the first `1.x` compatibility promise

## 0.2.0

First public inflation release for `fuggers-py`.

### Added

- `inflation`: shared USD CPI-U NSA conventions, daily reference-index plumbing, projected inflation-index curves, deterministic bootstrap from zero-coupon inflation swaps, official-data adapters for normalized monthly CPI history and Treasury auctioned TIPS metadata, and small linker breakeven/parity helpers
- `bonds`: `TipsBond` cashflow generation, real-yield pricing, accrued/clean/dirty handling, and real-yield risk analytics
- `rates`: zero-coupon and standard coupon inflation swaps with pricing, par-rate, and PV01 support
- end-to-end inflation router integration across bond and rates workflows

### Changed

- documentation, examples, and regression coverage now include CPI fixing ingestion, TIPS pricing, inflation swap pricing, inflation-curve bootstrap, and official-source adapter workflows
- inflation data adapters now distinguish normalized monthly CPI history from Treasury auctioned-security TIPS metadata instead of using one generic Treasury parser name
- public inflation examples are aligned with BLS/FRED CPI history inputs, Treasury auctioned-security metadata, Treasury nominal/real curve references, and FRED breakeven validation context

## 0.1.0

First public release of `fuggers-py`.

### Changed

- backfilled and normalized NumPy-style docstrings across the public Python package surface, making source docstrings the reference layer for autodoc and API discovery
- aligned package and module documentation across `core`, `math`, `curves`, `bonds`, `rates`, `funding`, `credit`, `analytics`, `portfolio`, `data`, `io`, and `engine`
- clarified library-wide conventions for raw decimals vs percent-of-par vs basis points, settlement-date semantics, clean vs dirty prices, curve/reference-date context, and risk/spread sign conventions
- hardened the release path around exact version provenance, editable-install smoke, build and wheel artifacts, sdist installs, and exact `v0.1.0` tag resolution
- refreshed the high-level guides in `README.md` and the domain docs under `docs/` so they stay consistent with the documented public API

## 0.1.0b2

Second beta cut focused on the expanded relative-value and cross-asset fixed-income stack, plus release engineering cleanup ahead of publication.

### Added

- expanded relative-value analytics across local RV, global RV, workflow hooks, and richer desk-style comparisons
- `funding`: repo trades, repo curves, implied repo, specialness, haircuts, and a dedicated funding pricing router
- `rates`: tradable IRS, OIS, FRAs, basis swaps, asset swaps, cross-currency basis swaps, and rates risk helpers
- government bond futures tooling covering contracts, deliverable baskets, conversion factors, CTD selection, invoice, basis, delivery-option models, and OABPV
- fitted-bond curve fitting, fair-value outputs, benchmark generation, bond switches, butterflies, and constant-maturity analytics
- `credit`: first-class CDS products, bootstrap, pricing, adjusted CDS helpers, bond/CDS basis, and proxy risk-free analytics
- options support for swaptions, cap/floors, futures options, Greeks, options RV, overlays, and optional advanced curve-model integrations

### Changed

- release engineering now tracks the current top-level package surface in the source-coverage policy
- supported local release builds are documented explicitly around `python -m build` and `pip wheel` from a normal git checkout
- packaging regression coverage now checks that build outputs, installed wheel metadata, installed sdist metadata, and `fuggers_py.__version__` stay aligned on supported local build paths

## 0.1.0b1

Initial release-focused cut of the Python analytics port.

### Added

- `core`: dates, prices, yields, spreads, calendars, day counts, and abstract curve/pricing/risk traits
- `math`: solvers, interpolation, extrapolation, optimization, and linear algebra helpers
- `curves`: discrete/wrapped curves, builders, calibration helpers, bumping, and multi-curve support
- `bonds`: fixed-rate, zero-coupon, callable/putable, floating-rate, sinking-fund, index/fixing, and option-model workflows
- `analytics`: yield, risk, spread, OAS, discount-margin, asset-swap, and YAS calculations
- `portfolio`: holdings, ETF helpers, aggregation, stress, benchmark, credit, and key-rate tooling
- `data`: typed ids, market/reference data, pricing specs, outputs, and in-memory research providers
- `io`: file-backed providers, JSON codecs, SQLite-backed embedded storage, and storage/transport interfaces
- `engine`: sync pricing router, batch pricing, curve builder, calculation graph, schedulers, market-data listener, builder, and reactive orchestration
- deterministic examples, golden validations, benchmark harness, and release smoke coverage

### Scope

- This package targets Python analytics and research orchestration workflows.
- Deterministic local adapters and notebook-friendly APIs are first-class.
- Server runtimes, WASM, FFI bindings, MCP surfaces, and distributed service infrastructure remain out of scope for this release.

### Changed

- historical compatibility namespaces such as `fuggers_py.prelude`, `fuggers_py.traits`, and `fuggers_py.ext` are removed from the current public surface
- removed the redundant top-level `fuggers_py.spreads` namespace
- `fuggers_py.measures.spreads` is the canonical spread namespace
