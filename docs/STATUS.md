# Project Status

This page is the plain-language status note for `fuggers-py`.

It answers four questions:

- what is solid today
- what is usable but still moving
- what is only scaffolding so far
- what we still want to finish before `1.x`

## Stability policy

- `fuggers-py` is still pre-`1.0`.
- Public APIs are usable, but they are not frozen yet.
- Until the first `1.x` release, we may still rename modules, move types, remove compatibility shims, and simplify APIs without keeping full backwards compatibility.
- After `1.x`, the plan is to move to a normal deprecation policy instead of making direct breaking changes.

## Most ready today

- `_core/`: dates, prices, yields, spreads, identifiers, calendars, and day-count logic are central and well-covered.
- `fuggers_py.bonds` plus its internal `_products/`, `_pricers/`, and `_measures/` support: bond definitions, cash flows, accrued interest, price and yield work, and bond risk are among the most mature parts of the repo.
- `_market/`: quotes, fixings, indices, and market-state records are core parts of the library and already have broad test coverage.
- Domain-first public packages such as `bonds`, `rates`, `credit`, `funding`, and `inflation`: the main pricing, risk, and analytics story now lives here.
- Validation and packaging checks are already part of the repo: unit tests, integration tests, API contracts, docs checks, packaging checks, and CI workflows are all present.

## Usable, but still moving

- `_measures/rv/`: the RV tools are usable, but this surface is still being simplified and should still be treated as pre-`1.0`.
- `_calc/`: the engine, routing, scheduling, and reactive runtime are functional, but this layer is broader than the core analytics and is more likely to keep changing as integration patterns settle.
- `portfolio/`: the portfolio layer already covers holdings, attribution, ETF, stress, and risk workflows, but it is a large surface and should be treated as less settled than the core bond analytics.
- `_adapters/`: storage, file, and transport boundaries are useful and tested, but they are still infrastructure-facing surfaces rather than the most settled part of the analytics library.

## Scaffold in place, but not finished

- `fuggers_py.vol_surfaces`: the package now has canonical volatility surface records and in-memory providers. What it does not have yet is a full volatility modeling stack with smile models, cubes, interpolation policy, calibration, and fitting workflows. This is the clearest example of a deliberate scaffold.
- The repo still has internal implementation layers such as `_market/`, `_reference/`, and `_storage/`, but the old public compatibility roots are no longer part of the shipped API.
- Some adapter and calc helpers intentionally include no-op or empty implementations for local workflows, testing, or optional integration paths. They are useful, but they should not be mistaken for a complete external integration story.
- The example notebooks are real workflows, but they are still research-oriented examples. They are not a promise that every workflow surface is finalized.

## What still needs work before `1.x`

- Freeze the package boundaries and naming in the places that are still moving, especially around volatility and some larger portfolio or runtime surfaces.
- Decide which remaining internal boundaries should be formalized before the first compatibility promise.
- Expand the volatility stack beyond storage objects and add clearer support for smiles, cubes, interpolation, and calibration.
- Keep broadening validation and examples for options, RV, cross-market workflows, and the `_calc` runtime.
- Write down the `1.x` compatibility and deprecation policy in one short public document once the API surface is ready to freeze.

## Public repo readiness

- The repo is in a state that can be made public.
- The basics are already in place: license, changelog, contributing guide, CI, docs, examples, packaging metadata, and a broad automated test suite.
- The right public message is not "everything is finished." The right public message is "the core fixed-income analytics are already substantial, but the repo is still pre-`1.0` and some package boundaries are intentionally still moving."
- Before you announce a public release, make sure the current local source and docs changes are actually committed, because untracked local files will not appear in the public branch by themselves.
