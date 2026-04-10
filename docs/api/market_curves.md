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
5. the live internal node and parametric kernel families
6. the first internal fitting path and report layer
7. shared curve errors and numeric conversions
8. multi-curve identifiers

It does **not** yet contain the full rebuilt fitting stack, the fitted-spline
path, the parametric calibrator path, or the later specialized curve views.
Those come later.

That is why the package may feel smaller than the historical curve stack. The
old broad curve tree was removed first. The new public contract came back
first. Two internal kernel families and the first fitting path are now in
place, and the rest will be rebuilt behind that contract.

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
        ├── observations.py
        ├── bootstrap.py
        ├── parametric.py
        └── bonds.py
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
   The internal home for calibration and fit reports. The minimal
   `CalibrationReport` object already lives here, and richer report types are
   still later work.
6. `market.curves.rates.kernels.*`
   The internal home for mathematical discounting representations. The shared
   kernel contract now lives here.
7. `market.curves.rates.calibrators.*`
   The internal home for fitting logic. The bootstrap fitting path already
   lives here now.
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
4. `rates.kernels.nodes` and `rates.kernels.parametric` now provide the live
   concrete kernel families
5. `rates.calibrators.base`, `rates.calibrators.observations`, and
   `rates.calibrators.bootstrap` now provide the first real fitting path
6. the fitted-spline kernel family and the later fitting paths are still later steps

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
2. curve builders can still choose different mathematical shapes internally

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

This is still internal. Normal pricing code should not import any of those
objects.

The intended flow is:

1. today a caller can already build a `YieldCurve` directly from `CurveSpec` and a built kernel
2. today the bootstrap calibrator can also read typed observations plus a `KernelSpec`
3. that calibrator builds one `CurveKernel` and one `CalibrationReport`
4. pricers still only depend on `DiscountingCurve`

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

Today there are two live internal kernel families:

1. node-based kernels in `rates.kernels.nodes`
2. parametric kernels in `rates.kernels.parametric`

The parametric family currently contains `NelsonSiegelKernel` and
`SvenssonKernel`. These wrap the existing parametric math primitives behind the
same `CurveKernel` interface and keep an explicit finite `max_t`, so they fit
the same public-curve contract as the node kernels.

The first fitting path already built on top of that internal layer is the
bootstrap path:

1. `BootstrapObservationKind`
   Says whether one input node is a zero rate or a discount factor.
2. `BootstrapObservation`
   One typed node observation with tenor, value, and identifier.
3. `BootstrapSolverKind`
   The root-solver choice used when the calibrator has to convert between
   zero-rate and discount-factor space.
4. `BootstrapCalibrator`
   The first real calibrator. It sorts observations by tenor, solves them in
   sequence, builds one internal kernel, and returns one `CalibrationReport`.

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

The first concrete internal kernel family already exists in
`fuggers_py.market.curves.rates.kernels.nodes`:

1. `LinearZeroKernel`
2. `LogLinearDiscountKernel`
3. `PiecewiseConstantZeroKernel`
4. `PiecewiseFlatForwardKernel`
5. `CubicSplineZeroKernel`
6. `MonotoneConvexKernel`

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

1. the remaining internal kernel families such as fitted-spline kernels
2. concrete internal calibrators beyond bootstrap
3. richer concrete fit reports

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

### `fuggers_py.market.curves.rates.calibrators.observations`

Use this module when you want typed bootstrap inputs directly.

This is where `BootstrapObservationKind` and `BootstrapObservation` belong.

### `fuggers_py.market.curves.rates.calibrators.bootstrap`

Use this module when you want the current concrete fitting path.

This is where `BootstrapSolverKind` and `BootstrapCalibrator` belong.

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
8. the bootstrap fitting path
9. shared conversion and error helpers
10. multi-curve identifiers

Not implemented yet:

1. the later internal kernel families such as fitted-spline kernels
2. the later fitting paths such as parametric and bond-price calibrators
3. richer concrete report types
4. `BreakevenCurve`
5. `ParYieldCurve`

So the current package is best understood as:

1. a finished public vocabulary
2. a real discounting runtime
3. the first real discount-curve fitting path

## Where To Read Next

1. Read [market](market.md) for the wider market package API page.
2. Read [SRC_STRUCTURE](../SRC_STRUCTURE.md) for the repo-wide package map.
3. Read the public API docs for:
   - `fuggers_py.market.curves`
   - `fuggers_py.market.curves.rates.enums`
   - `fuggers_py.market.curves.rates.spec`
   - `fuggers_py.market.curves.rates.base`
