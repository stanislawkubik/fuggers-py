# `fuggers_py.market.curves` guide

This page explains the current `market.curves` package in plain language.

It is not the refactor plan. It describes what exists in the code today, what
each object means, and where each concept belongs.

## Why This Package Is Small

`market.curves` is being rebuilt around a cleaner public ontology.

Right now the package is intentionally narrow. It contains:

1. the public rates-curve vocabulary
2. the public curve identity record
3. the public curve base classes
4. the shared internal kernel contract and kernel config
5. the live internal node, parametric, and spline kernel families
6. the live internal fitting paths and report layer
7. shared curve errors and numeric conversions
8. multi-curve identifiers

It does **not** yet contain the repo-wide upstream migration or the later
relative / par public curve views. It now does contain one richer report type
for the imperfect-fit path: `GlobalFitReport` extends the generic calibration
report with fitted kernel parameters, objective value, and typed per-row
residual diagnostics.

That is why the package may feel smaller than the historical curve stack. The
old broad curve tree was removed first. The new public contract came back
first. Three internal kernel families and two fitting paths are now in place,
and the next work is mainly about moving the rest of the repo onto that
contract.

That migration now happens mostly outside this package. The public curve API
stays tenor-based. Older pricing code that still works in dates now bridges
through
[`market/curve_support.py`](/Users/butterflytrading/AI-tests/fuggers-py/src/fuggers_py/market/curve_support.py)
instead of asking `market.curves` to grow the old date-based methods again.

## Current File Layout

This is the live package shape today:

```text
src/fuggers_py/market/curves/
├── __init__.py
├── conversion.py
├── errors.py
├── multicurve/
│   ├── __init__.py
│   └── index.py
└── rates/
    ├── __init__.py
    ├── base.py
    ├── enums.py
    ├── spec.py
    ├── reports.py
    ├── kernels/
    │   ├── __init__.py
    │   ├── base.py
    │   ├── nodes.py
    │   ├── parametric.py
    │   ├── spline.py
    │   ├── composite.py
    │   └── decorators.py
    └── calibrators/
        ├── __init__.py
        ├── base.py
        ├── _quotes.py
        ├── bootstrap.py
        └── global_fit.py
```

Read that tree like this:

1. `market.curves.__init__`
   The narrow public export surface. Upstream code should usually import from
   here.
2. `market.curves.rates.enums`
   The public enum layer. This is where we define the meaning of rate values,
   curve economic type, and extrapolation policy.
3. `market.curves.rates.spec`
   The public identity record for one curve snapshot.
4. `market.curves.rates.base`
   The public class hierarchy.
5. `market.curves.rates.reports`
   The internal home for calibration and fit reports. `CalibrationReport`
   stays the shared base report, and `GlobalFitReport` adds the richer
   imperfect-fit detail.
6. `market.curves.rates.kernels.*`
   The internal home for mathematical discounting representations. The shared
   kernel contract now lives here.
7. `market.curves.rates.calibrators.*`
   The internal home for fitting logic. Both the node-bootstrap path and the
   global-fit path live here now.
8. `market.curves.errors`
   Shared curve-package exceptions.
9. `market.curves.conversion`
   Numeric helpers for moving between discount factors, zero rates, and
   forward rates.
10. `market.curves.multicurve.index`
   Stable identifiers for multi-curve setups. These are not curve classes.

Important current boundary:

1. the internal `kernels/`, `calibrators/`, and `reports.py` files now exist
2. the kernel layer is no longer just an empty placeholder
3. `rates.kernels.base` now defines the shared internal kernel vocabulary:
   `CurveKernelKind`, `KernelSpec`, and `CurveKernel`
4. `rates.kernels.nodes`, `rates.kernels.parametric`, and
   `rates.kernels.spline` now provide the live concrete kernel families
5. `rates.calibrators.base` now defines the shared fitting layer, and
   `rates.calibrators.bootstrap` and `rates.calibrators.global_fit` now
   provide the live quote-driven fitting paths
6. bond quotes are now part of those live quote-driven fitting paths

Known migration blockers found outside this package:

1. some old upstream code still imports deleted legacy curve helpers such as
   `fitted_bonds`, `CreditCurve`, or `MultiCurveEnvironmentBuilder`
2. calc no longer builds curves, so upstream code now needs an explicit
   finished-curve handoff into calc instead of expecting calc to construct
   curves from raw point inputs
3. those are upstream migration gaps, not reasons to grow the new public curve
   package again unless we explicitly choose to restore those legacy exports

## The Mental Model

The current package is built around one simple idea:

1. a curve should first say what kind of object it is
2. then it should say what kind of number it returns
3. only after that should it expose richer pricing behavior

That gives us this public shape:

```text
RatesTermStructure
├── DiscountingCurve
│   └── YieldCurve
└── RelativeRateCurve
```

You should read those names in this order:

1. `RatesTermStructure`
   The generic public root for a rates object defined on tenor.
2. `DiscountingCurve`
   A rates term structure that can also discount future cash flows.
3. `YieldCurve`
   The named public class for discounting-style rates curves.
4. `RelativeRateCurve`
   A rates term structure that returns rates or spreads but should not be used
   as a discount curve.

## The Internal Kernel Layer

This is the new internal layer added after the public roots.

It exists so that we can say:

1. pricing code sees one stable discounting interface
2. the internal fitting code can still use different mathematical shapes underneath

That is what the kernel layer is for.

The key internal objects are:

1. `CurveKernelKind`
   The family name of the math we want to use. Examples are linear zero,
   log-linear discount, or Nelson-Siegel.
2. `KernelSpec`
   The immutable internal config that says which kernel family we want and
   what settings it needs.
3. `CurveKernel`
   The internal object that defines the fitted rate curve over a tenor domain.

In simple words:

1. `CurveKernelKind` says "which shape?"
2. `KernelSpec` says "which shape, with which settings?"
3. `CurveKernel` says "here is the built curve shape that gives fitted rates"

The kernel implementations are still internal. Normal pricing code should not
depend on the concrete kernel modules. But the public `YieldCurve.fit(...)`
entry point does need a small construction vocabulary, so
`fuggers_py.market.curves.rates` now re-exports:

1. `CurveKernelKind`
2. `KernelSpec`
3. `CalibrationMode`
4. `CalibrationObjective`
5. `BondFitTarget`
6. `CalibrationSpec`
7. `CalibrationReport`
8. `GlobalFitReport`

`CurveKernel` is also re-exported there for the advanced direct
`YieldCurve(spec=..., kernel=...)` path.

The intended flow is:

1. today a caller can still wrap a built kernel directly when needed
2. the normal public construction path is `YieldCurve.fit(...)`
3. that classmethod reads market quotes, one `CurveSpec`, one `KernelSpec`,
   and one `CalibrationSpec`
4. the fitting layer chooses the live calibrator path from
   `CalibrationSpec.mode`
5. the calibrator builds one `CurveKernel` and one calibration report
6. pricers still only depend on `DiscountingCurve`

So the kernel layer gives us freedom to change the math without changing the
pricing-facing contract.

The important simplification is this:

1. the shared kernel interface now uses a rate-first base case
2. the kernel must define the fitted curve through `rate_at(tenor)`
3. discount factors are then derived from that fitted rate curve
4. some kernels may still internally store discount factors or forwards
5. the shared contract does not force the caller to know that

That makes the public story simpler too:

1. `YieldCurve` is now the public zero / spot-rate view
2. forward rates will be derived from the same discount curve
3. kernel family differences stay internal

Today there are three live internal kernel families:

1. node-based kernels in `rates.kernels.nodes`
2. parametric kernels in `rates.kernels.parametric`
3. spline kernels in `rates.kernels.spline`

The parametric family currently contains `NelsonSiegelKernel` and
`SvenssonKernel`. These wrap the existing parametric math primitives behind the
same `CurveKernel` interface and keep an explicit finite `max_t`, so they fit
the same public-curve contract as the node kernels.

The spline family currently contains `ExponentialSplineKernel` and
`CubicSplineKernel`. The exponential spline kernel uses a constant term
plus exponential basis terms. `CubicSplineKernel` is the one cubic spline
production kernel. It uses one fixed knot grid, takes knot zero values as its
parameters, inserts a zero-tenor anchor only as an internal helper when
needed, and evaluates a natural cubic spline in zero-rate space.

Today there are two live fitting paths on top of that internal layer:

1. `BootstrapSolverKind`
   The root-solver choice used when the calibrator has to convert between
   zero-rate and discount-factor space.
2. `BootstrapCalibrator`
   The exact sequential construction path. It normalizes supported market
   quotes into internal fit rows, sorts them by tenor, solves them in
   sequence, builds one internal kernel, and returns one `CalibrationReport`.
3. `GlobalFitOptimizerKind`
   The least-squares routine choice used by the global-fit calibrator.
4. `GlobalFitCalibrator`
   The imperfect global regression fit path. It normalizes supported market
   quotes into internal fit rows, converts quoted zero rates into continuous
   compounding internally when needed, fits one global curve-parameter vector,
   builds one global-fit kernel, and returns one `GlobalFitReport`.
   When regressors are supplied, it profiles the regressor coefficients by
   weighted least squares inside each curve-parameter evaluation and stores
   the fitted coefficients on the report. The report also stores the fitted
   kernel parameter vector, the final objective value, and typed per-row
   residual rows. Bond price rows keep price residuals in native target units
   and add YTM diagnostics only as secondary detail.

The global-fit path now covers:

1. `CUBIC_SPLINE`
2. `NELSON_SIEGEL`
3. `SVENSSON`
4. `EXPONENTIAL_SPLINE`

For `CUBIC_SPLINE`, the caller must pass fixed `knots` in
`KernelSpec.parameters`. The calibrator then fits the knot zero values on that
fixed grid. The knot grid must be strictly increasing, contain at least three
knots, and define valid front-end spacing. `CUBIC_SPLINE` only accepts its own
spline-specific parameter keys.

For `EXPONENTIAL_SPLINE`, the caller must pass fixed `decay_factors` in
`KernelSpec.parameters`. The calibrator then fits the spline coefficients
against those fixed decay factors. More generally, the global-fit path now
checks `KernelSpec.parameters` by kernel kind, so stale keys for one kernel
family are rejected instead of being ignored on another.

Today the live quote-driven path accepts:

1. tenor-carrying `SwapQuote`
2. tenor-carrying `RepoQuote`
3. `BondQuote`

For the bond side, the live rule is:

1. `yield_to_maturity` stays a YTM target
2. on the bootstrap route, bond price quotes normalize to bond-implied YTM
3. on the global-fit route, price quotes stay in price space
4. global-fit price quotes use `CalibrationSpec.bond_fit_target`
5. the default bond price target is `DIRTY_PRICE`
6. callers can switch the global-fit bond price target to `CLEAN_PRICE`

`BondQuote` can also carry optional observation-date `regressors` and
`fit_weight` values. Those stay on the quote because they belong to one market
observation, not to the bond instrument itself.

The public construction layer now puts those live methods in one place:

1. `YieldCurve.fit(...)`
   One public entry point that always returns `YieldCurve`.
2. `CalibrationSpec(mode=CalibrationMode.BOOTSTRAP, ...)`
   This is the exact sequential route for the local node-style families.
3. `CalibrationSpec(mode=CalibrationMode.GLOBAL_FIT, ...)`
   This is the imperfect global regression route for the coefficient-based
   families and the fixed-knot cubic-spline family.

`CalibrationSpec` is also the single control object for the direct calibrator
constructors. `BootstrapCalibrator` only accepts
`CalibrationObjective.EXACT_FIT`. `GlobalFitCalibrator` currently only accepts
`CalibrationObjective.WEIGHTED_L2`.

## Why `CUBIC_SPLINE` Is Now A Global-Fit Kernel

The important rule is now simple.

`CUBIC_SPLINE` is no longer a bootstrap kernel.

That means:

1. the caller supplies one fixed knot grid
2. the unknowns are the zero-rate values at those knots
3. the whole spline curve moves when one knot value changes

That makes it a global parameter fit, not an exact sequential bootstrap.

That means:

1. `CUBIC_SPLINE` belongs on the global-fit path
2. the caller fixes the knot grid through `KernelSpec.parameters['knots']`
3. the calibrator fits the knot zero values on that grid

## The Core Question: What Does `rate_at(tenor)` Mean?

The key design choice is that a curve does not just return a number.

It returns a number with a declared meaning.

That is why the base API has both:

1. `curve.rate_space`
2. `curve.rate_at(tenor)`

Read them together:

1. `curve.rate_at(5.0)` answers:
   "what is your number at the 5-year tenor?"
2. `curve.rate_space` answers:
   "what kind of number is that?"

This matters because the same value can mean very different things.

Examples:

1. if `curve.rate_space` is `RateSpace.ZERO`, then `curve.rate_at(5.0) == 0.04`
   means a 5-year zero rate of 4%
2. if `curve.rate_space` is `RateSpace.INSTANTANEOUS_FORWARD`, the same `0.04`
   means the instantaneous forward rate at 5 years
3. if `curve.rate_space` is `RateSpace.SPREAD`, the same `0.04` means a 4%
   spread-style rate, not a discounting rate

That is the reason the root public contract is honest and small. It does not
pretend every rates object can discount cash flows.

## Public Enums

### `RateSpace`

`RateSpace` tells you how to interpret `rate_at(tenor)`.

Current members:

1. `ZERO`
   `rate_at(tenor)` is a zero-coupon rate.
2. `INSTANTANEOUS_FORWARD`
   `rate_at(tenor)` is an instantaneous forward rate.
3. `PAR_YIELD`
   `rate_at(tenor)` is a par yield.
4. `SPREAD`
   `rate_at(tenor)` is a relative rate, such as a spread.

What it is for:

1. correctness
2. introspection
3. reporting
4. documentation

What it is **not** for:

1. choosing the economic role of the curve
2. choosing the calibrator
3. choosing the pricing route

### `CurveType`

`CurveType` tells the wider system what economic job the curve plays.

Current members:

1. `NOMINAL`
2. `REAL`
3. `OVERNIGHT_DISCOUNT`
4. `PROJECTION`
5. `BREAKEVEN`
6. `PAR`
7. `BASIS`

Read it as a routing label, not as a mathematical class.

Examples:

1. a nominal discount curve and a real discount curve can both still be
   `YieldCurve`
2. they differ in `CurveType`, not in their public base class

### `ExtrapolationPolicy`

`ExtrapolationPolicy` tells the curve what to do when you ask for a tenor past
its explicit domain.

Current members:

1. `ERROR`
   Out-of-range tenors raise.
2. `HOLD_LAST_NATIVE_RATE`
   Hold the last value in the curve's own `rate_space`.
3. `HOLD_LAST_ZERO_RATE`
   Hold the last zero rate.
4. `HOLD_LAST_FORWARD_RATE`
   Hold the last forward rate.

This is part of the public contract because the supported tenor domain is part
of the meaning of a curve.

## `CurveSpec`

`CurveSpec` is the identity record for one curve snapshot.

It answers:

1. what this curve is called
2. what date it is anchored on
3. what day-count convention it uses for tenor interpretation
4. what currency it belongs to
5. what economic type it has
6. what extrapolation rule it follows

Fields:

1. `name`
   Human-readable curve name.
2. `reference_date`
   The anchor date of the curve.
3. `day_count`
   The day-count convention label.
4. `currency`
   The curve currency.
5. `type`
   The economic curve type.
6. `reference`
   An optional narrower label, for example an index family.
7. `extrapolation_policy`
   The public out-of-domain rule.

What belongs in `CurveSpec`:

1. business identity
2. routing identity
3. domain policy

What does **not** belong in `CurveSpec`:

1. spline knots
2. solver settings
3. calibration weights
4. interpolation choices

Those are internal representation or fitting choices, not public identity.

## Public Base Classes

### `RatesTermStructure`

`RatesTermStructure` is the public root for tenor-based rate objects.

It guarantees:

1. every curve has a `spec`
2. every curve has a `reference_date`
3. every curve declares one `rate_space`
4. every curve declares one upper tenor bound through `max_t()`
5. every curve returns its scalar through `rate_at(tenor)`
6. every curve can validate the domain and finiteness of that scalar through
   `validate_rate(tenor)`

What it does **not** guarantee:

1. discount factors
2. zero rates
3. forward rates between two tenors
4. smoothness
5. monotonicity

This is deliberate. The root class stays small so it can represent both
discounting curves and non-discounting rate views.

### `DiscountingCurve`

`DiscountingCurve` is the branch for curves that can price future cash flows
through discounting.

It adds:

1. `discount_factor_at(tenor)`
2. `zero_rate_at(tenor)`
3. `forward_rate_between(start_tenor, end_tenor)`

How to read it:

1. `discount_factor_at(tenor)` is the primitive pricing-facing operation
2. `zero_rate_at(tenor)` is the continuously compounded zero-rate view implied
   by the discount factors
3. `forward_rate_between(...)` is the continuously compounded forward-rate view
   implied by the same discounting object

Who should depend on this class:

1. pricers
2. risk measures
3. analytics that need discount factors or forwards

Who should **not** depend on this class:

1. generic reporting code that only needs tenor-to-rate access
2. code that wants a spread-style term structure

### `YieldCurve`

`YieldCurve` is the named public class for discounting-style rates curves.

This is the class users are meant to hold when they want:

1. a nominal discount curve
2. a real discount curve
3. an overnight discount curve
4. a projection-style rates curve, as long as it still supports the same
   discount / zero / forward contract

Important current detail:

1. `YieldCurve` is now the concrete public runtime object
2. it owns one `CurveSpec`
3. it owns one internal `CurveKernel`
4. it may carry one optional `CalibrationReport`
5. its public `rate_space` is fixed to `RateSpace.ZERO`
6. its public `rate_at(tenor)` is the zero / spot-rate view for positive tenor
7. most callers should build it through `YieldCurve.fit(...)`
8. direct `YieldCurve(spec=..., kernel=...)` construction is the advanced path

So, today:

1. `DiscountingCurve` is the behavioral contract pricing code should depend on
2. `YieldCurve` is the concrete public class users should normally hold

### `RelativeRateCurve`

`RelativeRateCurve` is the public root for rate objects that should not be
used as primary discount curves.

This branch exists so the ontology can later hold things such as:

1. breakeven curves
2. basis curves
3. spread-style term structures

Important current detail:

1. this is only a public root right now
2. there are no concrete `RelativeRateCurve` leaves implemented yet

## `DiscountingCurve` Versus `YieldCurve`

This is the most common confusion point, so the short answer is:

1. `DiscountingCurve` means:
   "any public curve type that can discount"
2. `YieldCurve` means:
   "the public class name we use for discounting-style rates curves"

In the current code the difference is still mostly about responsibility, but it
is no longer empty.

`DiscountingCurve` defines the operations. `YieldCurve` is the concrete public
implementation that wraps one internal kernel and exposes a public zero-rate
view.

The concrete internal node kernel family lives in
`fuggers_py.market.curves.rates.kernels.nodes`:

1. `LinearZeroKernel`
2. `LogLinearDiscountKernel`
3. `PiecewiseConstantZeroKernel`
4. `PiecewiseFlatForwardKernel`
5. `MonotoneConvexKernel`

`CubicSplineKernel` lives in `fuggers_py.market.curves.rates.kernels.spline`.
These kernels differ only in the internal math. They all still plug into the
same public `YieldCurve`.

Why keep both names?

1. `DiscountingCurve` is the right type for pricing code to depend on
2. `YieldCurve` is the right named public object for users to build and carry
3. this lets the public object grow richer without changing what pricing code
   depends on

That split is intentional. It lets pricing code stay generic while the public
curve object becomes richer over time.

## What Belongs In `market.curves`

Right now this package should contain:

1. the public rates ontology
2. shared curve errors
3. shared numeric conversions
4. multi-curve identifiers

Later, this package will also contain:

1. richer concrete fit reports if real downstream code still needs them
2. optional composite or decorator helpers if they still prove useful
3. later public relative / par curve views

What does **not** belong in the current public root:

1. bond-specific public curve classes
2. one public curve class per fitting method
3. one public curve class per interpolation family
4. non-rate domains such as credit curves or inflation-index curves

## What Belongs In Each Current Module

### `fuggers_py.market.curves`

This is the public import surface.

Use it when you want:

1. `CurveSpec`
2. `CurveType`
3. `RateSpace`
4. `ExtrapolationPolicy`
5. `RatesTermStructure`
6. `DiscountingCurve`
7. `YieldCurve`
8. `RelativeRateCurve`

### `fuggers_py.market.curves.rates.enums`

Use this module when you want the public enum meanings directly.

This is where value meaning, economic type, and extrapolation policy belong.

### `fuggers_py.market.curves.rates.spec`

Use this module when you want the curve identity record directly.

This is where curve identity belongs. It is not where curve behavior belongs.

### `fuggers_py.market.curves.rates.base`

Use this module when you want the public class hierarchy directly.

This is where public curve behavior belongs. It is not where fitting logic or
mathematical storage choices belong.

### `fuggers_py.market.curves.rates.kernels.base`

Use this module when you want the shared internal kernel vocabulary directly.

This is where `CurveKernelKind`, `KernelSpec`, and the small shared
`CurveKernel` contract belong.

### `fuggers_py.market.curves.rates.kernels.nodes`

Use this module when you want the current concrete internal discounting kernels.

This is where the rebuilt node-based kernels live:

1. linear zero
2. log-linear discount
3. piecewise-constant zero
4. piecewise-flat forward
5. cubic spline zero
6. monotone-convex

### `fuggers_py.market.curves.rates.calibrators.base`

Use this module when you want the shared fitting contract directly.

This is where `CalibrationObjective` and `CurveCalibrator` belong.

### `fuggers_py.market.curves.rates.calibrators.bootstrap`

Use this module when you want the node-bootstrap fitting path.

This is where `BootstrapSolverKind` and `BootstrapCalibrator` belong. The
module now reads market quotes and normalizes supported quote types
internally. The constructor takes one `CalibrationSpec` and only accepts the
bootstrap exact-fit route.

### `fuggers_py.market.curves.rates.calibrators.global_fit`

Use this module when you want the global-fit path.

This is where `GlobalFitOptimizerKind` and `GlobalFitCalibrator` belong. The
module now reads market quotes and normalizes supported quote types
internally. It is the imperfect global regression fitter for these supported
kernel kinds:

The constructor takes one `CalibrationSpec` and currently only accepts the
global-fit weighted-L2 route.

1. fixed-knot cubic spline
2. Nelson-Siegel
3. Svensson
4. exponential spline

### `fuggers_py.market.curves.errors`

Use this module for curve-package input and domain errors.

This is where the package-level error vocabulary belongs.

### `fuggers_py.market.curves.conversion`

Use this module for numeric conversions between discount factors, zero rates,
and forward rates.

This is a helper module. It is not part of the public ontology itself.

### `fuggers_py.market.curves.multicurve.index`

Use this module for stable identifiers such as `RateIndex` and
`CurrencyPair`.

These are assembly keys. They are not curve classes.

## What Is Implemented Now, And What Is Not

Implemented now:

1. the public rate ontology
2. the public enums
3. the public curve identity record
4. the public class split between generic rate curves and discounting curves
5. the concrete `YieldCurve` runtime object
6. the node-based internal kernel family
7. the parametric internal kernel family
8. the spline internal kernel family
9. one public `YieldCurve.fit(..., calibration_spec=...)` construction path
10. the bootstrap fitting path
11. the global-fit path for fixed-knot cubic spline, Nelson-Siegel, Svensson, and exponential spline
12. quote-driven bond support on both live fitting paths
13. shared conversion and error helpers
14. multi-curve identifiers

Not implemented yet:

1. the repo-wide upstream migration onto `DiscountingCurve` / `YieldCurve`
2. richer concrete report types beyond `GlobalFitReport`
3. `BreakevenCurve`
4. `ParYieldCurve`

So the current package is best understood as:

1. a finished public vocabulary
2. a real discounting runtime
3. one public construction path over two real discount-curve fitting paths that now read real rate and bond quotes
4. a package whose next job is upstream adoption, not another core fitting rewrite

## Where To Read Next

1. Read [market](market.md) for the wider market package API page.
2. Read [SRC_STRUCTURE](../SRC_STRUCTURE.md) for the repo-wide package map.
3. Read the public API docs for:
   - `fuggers_py.market.curves`
   - `fuggers_py.market.curves.rates.enums`
   - `fuggers_py.market.curves.rates.spec`
   - `fuggers_py.market.curves.rates.base`
