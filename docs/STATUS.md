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

- `core/`: dates, prices, yields, spreads, identifiers, calendars, and day-count logic are central and well-covered.
- `products/bonds/` and `pricers/bonds/`: bond definitions, cash flows, accrued interest, price and yield work, and bond risk are among the most mature parts of the repo.
- `market/curves/`: base curve types, wrappers, conversions, calibration helpers, inflation curves, credit curves, and multi-curve environments are core parts of the library and already have broad test coverage.
- `measures/`: the main yield, spread, pricing, risk, and inflation analytics are in active use and are part of the curated public API.
- Validation and packaging checks are already part of the repo: unit tests, integration tests, API contracts, docs checks, packaging checks, and CI workflows are all present.

## Usable, but still moving

- `market/curves/fitted_bonds/`: the fitted-bond stack is usable today and already has examples and tests, but the API is still being simplified. This is an area where names and object shapes may still change before `1.x`.
- `measures/rv/`: the fitted-curve RV tools are usable, but they depend on the fitted-bond surface, so they should also be treated as pre-`1.0` moving parts.
- `calc/`: the engine, routing, scheduling, and reactive runtime are functional, but this layer is broader than the core analytics and is more likely to keep changing as integration patterns settle.
- `portfolio/`: the portfolio layer already covers holdings, attribution, ETF, stress, and risk workflows, but it is a large surface and should be treated as less settled than the core bond analytics.
- `adapters/`: storage, file, and transport boundaries are useful and tested, but they are still infrastructure-facing surfaces rather than the most settled part of the analytics library.

## Scaffold in place, but not finished

- `market/vol_surfaces/`: the package now has canonical volatility surface records and in-memory providers. What it does not have yet is a full volatility modeling stack with smile models, cubes, interpolation policy, calibration, and fitting workflows. This is the clearest example of a deliberate scaffold.
- Some compatibility layers are still present while the package layout settles. Examples include re-exports in `market/snapshot.py` and `market/sources.py`, and several small compatibility type modules in `reference/` and `portfolio/`.
- Some adapter and calc helpers intentionally include no-op or empty implementations for local workflows, testing, or optional integration paths. They are useful, but they should not be mistaken for a complete external integration story.
- The example notebooks are real workflows, but they are still research-oriented examples. They are not a promise that every workflow surface is finalized.

## What still needs work before `1.x`

- Freeze the package boundaries and naming in the places that are still moving, especially around fitted-bond workflows, market-data organization, and volatility.
- Decide which compatibility shims should remain and which should be removed before the first compatibility promise.
- Expand the volatility stack beyond storage objects and add clearer support for smiles, cubes, interpolation, and calibration.
- Keep broadening validation and examples for options, RV, cross-market workflows, and the calc runtime.
- Write down the `1.x` compatibility and deprecation policy in one short public document once the API surface is ready to freeze.

## Public repo readiness

- The repo is in a state that can be made public.
- The basics are already in place: license, changelog, contributing guide, CI, docs, examples, packaging metadata, and a broad automated test suite.
- The right public message is not "everything is finished." The right public message is "the core fixed-income analytics are already substantial, but the repo is still pre-`1.0` and some package boundaries are intentionally still moving."
- Before you announce a public release, make sure the current local source and docs changes are actually committed, because untracked local files will not appear in the public branch by themselves.
