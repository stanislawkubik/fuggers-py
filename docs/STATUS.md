# Project Status

## Stability policy

- `fuggers-py` is still pre-`1.0`.
- Public APIs are usable, but they are not frozen yet.
- Until the first `1.x` release, we may still rename modules, move types, remove compatibility shims, and simplify APIs without keeping full backwards compatibility.
- After `1.x`, the plan is to move to a normal deprecation policy instead of making direct breaking changes.

## Most ready today

- `fuggers_py.curves`: this is the closest package to the intended `1.x`
  shape. The public root is small, `YieldCurve.fit(...)` is the main fitting
  path, and advanced calibration or kernel records live in focused submodules.
- Quote-driven curve fitting is in its near-final shape for the current release.
  The fitter accepts swap, bond, and repo quotes, uses `CurveSpec` for curve
  identity, and returns a `CalibrationReport`.
- `_core/`: dates, prices, yields, spreads, identifiers, calendars, and
  day-count logic are central and well-covered.
- The first-layer package layout is in place: shared names come from
  `fuggers_py`, and domain names come from `fuggers_py.curves`,
  `fuggers_py.bonds`, `fuggers_py.rates`, `fuggers_py.inflation`,
  `fuggers_py.credit`, `fuggers_py.funding`, `fuggers_py.portfolio`, or
  `fuggers_py.vol_surfaces`.
- Validation and packaging checks are part of the repo: unit tests, integration
  tests, API contracts, docs checks, packaging checks, and CI workflows are all
  present.

## Usable, but still moving

- `fuggers_py.bonds`: the bond analytics are useful and broad, but the public
  surface is larger than the current target style. Before `1.x`, it still needs
  a hardening pass around ownership, inheritance, type records, and enum-heavy
  areas.
- `fuggers_py.rates`, `fuggers_py.funding`, `fuggers_py.credit`, and
  `fuggers_py.inflation`: these packages now own their domain objects, but their
  public roots and internal shapes are not final. They should be reviewed
  against the curve package before the compatibility promise.
- `fuggers_py.portfolio`: the portfolio layer already covers holdings,
  attribution, ETF, stress, liquidity, and risk workflows. It is still a large
  workflow surface and is less settled than the curve-fitting API.
- `_runtime/`: engine routing, scheduling, quote records, market-data snapshots,
  source protocols, and market-state records are functional. This layer is still
  more likely to change than the core analytics packages.
- `_storage/`: storage, file, and transport boundaries are useful and tested,
  but they are infrastructure-facing surfaces rather than frozen user-facing
  API.

## Scaffold in place, but not finished

- `fuggers_py.vol_surfaces`: the package now has canonical volatility surface records and in-memory providers. What it does not have yet is a full volatility modeling stack with smile models, cubes, interpolation policy, calibration, and fitting workflows. This is the clearest example of a deliberate scaffold.
- The repo still has internal implementation layers such as `_runtime/` and `_storage/`, but the old public compatibility roots are no longer part of the shipped API.
- Some storage and runtime helpers intentionally include no-op or empty implementations for local workflows, testing, or optional integration paths. They are useful, but they should not be mistaken for a complete external integration story.
- The example notebooks are real workflows, but they are still research-oriented examples. They are not a promise that every workflow surface is finalized.

## What still needs work before `1.x`

- Bring the other public modules up to the standard set by `curves`: one obvious
  public entry path, simple fitting or pricing calls, clear ownership inside the
  package, and focused submodules for advanced pieces.
- Review domain inheritance and keep it only where it makes the code easier to
  follow. Remove layers that only move names around.
- Reduce enum-heavy areas where a plain string, small record, or existing shared
  type is easier to read and test.
- Freeze the package boundaries and naming in the places that are still moving,
  especially around bonds, rates, portfolio, runtime, and volatility.
- Decide which remaining internal boundaries should be formalized before the
  first compatibility promise.
- Expand the volatility stack beyond storage objects and add clearer support for
  smiles, cubes, interpolation, and calibration.
- Keep broadening validation and examples for options, RV, cross-market
  workflows, and the runtime layer.
- Write down the `1.x` compatibility and deprecation policy in one short public
  document once the API surface is ready to freeze.

## Public repo readiness

- The repo is in a state that can be made public.
- The basics are already in place: license, changelog, contributing guide, CI, docs, examples, packaging metadata, and a broad automated test suite.
- The right public message is not "everything is finished." The right public
  message is "curve fitting is close to the intended final shape, the broader
  fixed-income surface is already substantial, and the repo is still pre-`1.0`
  while the other domains are brought up to the same standard."
- Before you announce a public release, make sure the current local source and docs changes are actually committed, because untracked local files will not appear in the public branch by themselves.
