# `fuggers_py.market`

Market state, quotes, fixings, and indices.

```{eval-rst}
.. automodule:: fuggers_py.market
   :members:
   :member-order: bysource
```

## `fuggers_py.market.state`

```{eval-rst}
.. automodule:: fuggers_py.market.state
   :members:
   :member-order: bysource
   :no-index:
```

## `fuggers_py.market.quotes`

```{eval-rst}
.. automodule:: fuggers_py.market.quotes
   :members:
   :member-order: bysource
   :no-index:
```

## `fuggers_py.market.snapshot`

```{eval-rst}
.. automodule:: fuggers_py.market.snapshot
   :members:
   :member-order: bysource
   :no-index:
```

## `fuggers_py.market.sources`

```{eval-rst}
.. automodule:: fuggers_py.market.sources
   :members:
   :member-order: bysource
   :no-index:
```

## `fuggers_py.market.curves`

`fuggers_py.market.curves` is intentionally small right now.

If you want the detailed explanation of the package structure, read
[the dedicated `market.curves` guide](market_curves.md) first. That page
explains what each object means, what belongs in each file, and how to think
about the difference between `RatesTermStructure`, `DiscountingCurve`, and
`YieldCurve`.

The package currently exposes the public rates curve root and the small set of
objects that define what a rates curve means:

- `CurveSpec`: the business identity of one curve snapshot
- `CurveType`: the economic type of the curve, such as nominal or real
- `RateSpace`: the meaning of the rate returned by the curve
- `ExtrapolationPolicy`: the rule for tenors past the curve domain
- `RatesTermStructure`: the public base class for rates curves
- `DiscountingCurve`: the public base class for curves that can discount cash flows
- `YieldCurve`: the concrete public class for discounting-style rates curves
- `RelativeRateCurve`: the public root for non-discounting rate curves such as spreads

The key contract is simple:

- `curve.rate_space` tells you what kind of rate the curve returns
- `curve.rate_at(tenor)` returns the rate at that tenor in the curve's `rate_space`
- `curve.max_t()` returns the last supported tenor
- `curve.validate_rate(tenor)` checks the tenor domain and verifies that the returned rate is finite
- if the curve is a `DiscountingCurve`, it also supports `discount_factor_at(tenor)`, `zero_rate_at(tenor)`, and `forward_rate_between(start_tenor, end_tenor)`

In plain language, this is the point:

- a curve giving you `0.04` at `5.0` is not enough by itself
- you also need to know what kind of rate that `0.04` is
- `curve.rate_space` gives that meaning
- `curve.rate_at(tenor)` gives the actual number

So you should read the API like this:

- `curve.rate_at(5.0)` answers "what is your 5-year number?"
- `curve.rate_space` answers "what kind of number is it?"

That keeps the root contract honest. At the root level the base curve only promises:

- a tenor-to-rate mapping
- a clear meaning for the returned rate
- a clear tenor domain

Discounting behavior now sits on the separate `DiscountingCurve` branch. That
is the point of the Step 3 split:

- `RatesTermStructure` means "a tenor-to-rate object"
- `DiscountingCurve` means "a tenor-to-rate object that can also discount cash flows"
- `RelativeRateCurve` means "a tenor-to-rate object that should not be used as a discount curve"

`YieldCurve` now sits on top of that split as the concrete public discounting
object. It always exposes a public zero-rate view:

- `yield_curve.rate_space` is always `RateSpace.ZERO`
- `yield_curve.rate_at(tenor)` returns the zero / spot-rate view for positive tenor
- `yield_curve.discount_factor_at(tenor)` delegates to one internal kernel
- `yield_curve.calibration_report` may carry one optional fit report attachment

The package also keeps a few shared helpers:

- `conversion.py`: numeric conversions between discount factors, zero rates, and forward rates
- `errors.py`: shared curve exceptions such as `InvalidCurveInput` and `TenorOutOfBounds`
- `multicurve/`: identifiers used for later multi-curve assembly, currently `RateIndex` and `CurrencyPair`

Today the public operation roots exist, and `YieldCurve` is now a real runtime
object backed by one internal kernel plus one optional report. What is still
missing is the rest of the deeper implementation layer: concrete parametric and
bond calibrators, richer fit reports, and the later fitted-spline kernel
family. In particular, breakeven curves and par-yield curves are
still later steps. Concrete internal kernel families now exist in
`market.curves.rates.kernels.nodes` and
`market.curves.rates.kernels.parametric`. The node family includes the rebuilt linear-zero,
log-linear-discount, piecewise-constant-zero, piecewise-flat-forward,
cubic-spline-zero, and monotone-convex kernels. The shared kernel contract is
still intentionally small: internal kernels define the fitted rate curve on a
tenor domain, and discount factors are derived from that rate curve. The
parametric family includes
`NelsonSiegelKernel` and `SvenssonKernel`, which wrap the existing parametric
math primitives behind the same internal `CurveKernel` contract while keeping
an explicit finite `max_t`. The first
real fitting path now exists in
`market.curves.rates.calibrators.bootstrap`. That bootstrap calibrator takes
typed node observations, reads a `KernelSpec`, builds one internal kernel, and
returns one `CalibrationReport` with per-observation residual rows.

Short package map:

- `market.curves`: narrow public export surface
- `market.curves.rates.enums`: public enum meanings
- `market.curves.rates.spec`: curve identity record
- `market.curves.rates.base`: public class hierarchy
- `market.curves.rates.reports`: internal home for fit reports
- `market.curves.rates.kernels.*`: internal home for mathematical discounting representations
- `market.curves.rates.kernels.base`: shared internal kernel family enum, config, and rate-first kernel contract
- `market.curves.rates.kernels.nodes`: concrete node-based discounting kernels
- `market.curves.rates.kernels.parametric`: concrete parametric discounting kernels
- `market.curves.rates.calibrators.base`: shared calibrator contract and objective enum
- `market.curves.rates.calibrators.observations`: typed bootstrap observations
- `market.curves.rates.calibrators.bootstrap`: bootstrap calibrator and solver choice
- `market.curves.errors`: curve-package errors
- `market.curves.conversion`: numeric conversion helpers
- `market.curves.multicurve.index`: identifiers such as `RateIndex` and `CurrencyPair`

```{eval-rst}
.. automodule:: fuggers_py.market.curves
   :members:
   :member-order: bysource
   :no-index:
```

## `fuggers_py.market.curves.rates`

```{eval-rst}
.. automodule:: fuggers_py.market.curves.rates
   :members:
   :member-order: bysource
   :no-index:
```

## `fuggers_py.market.curves.rates.enums`

```{eval-rst}
.. automodule:: fuggers_py.market.curves.rates.enums
   :members:
   :member-order: bysource
   :no-index:
```

## `fuggers_py.market.curves.rates.spec`

```{eval-rst}
.. automodule:: fuggers_py.market.curves.rates.spec
   :members:
   :member-order: bysource
   :no-index:
```

## `fuggers_py.market.curves.rates.base`

```{eval-rst}
.. automodule:: fuggers_py.market.curves.rates.base
   :members:
   :member-order: bysource
   :no-index:
```

## Internal Curve Modules

The modules below are part of the current curve package structure, but they are
not public pricing API.

They are documented in plain language in [the dedicated `market.curves`
guide](market_curves.md), because that guide is the right place to explain what
belongs where without making internal placeholders look like stable public
interfaces.

Current internal homes:

- `fuggers_py.market.curves.rates.reports`
- `fuggers_py.market.curves.rates.kernels`
- `fuggers_py.market.curves.rates.kernels.base`
- `fuggers_py.market.curves.rates.kernels.nodes`
- `fuggers_py.market.curves.rates.kernels.parametric`
- `fuggers_py.market.curves.rates.kernels.spline`
- `fuggers_py.market.curves.rates.kernels.composite`
- `fuggers_py.market.curves.rates.kernels.decorators`
- `fuggers_py.market.curves.rates.calibrators`
- `fuggers_py.market.curves.rates.calibrators.base`
- `fuggers_py.market.curves.rates.calibrators.observations`
- `fuggers_py.market.curves.rates.calibrators.bootstrap`
- `fuggers_py.market.curves.rates.calibrators.parametric`
- `fuggers_py.market.curves.rates.calibrators.bonds`

## `fuggers_py.market.curves.errors`

```{eval-rst}
.. automodule:: fuggers_py.market.curves.errors
   :members:
   :member-order: bysource
   :no-index:
```

## `fuggers_py.market.curves.conversion`

```{eval-rst}
.. automodule:: fuggers_py.market.curves.conversion
   :members:
   :member-order: bysource
   :no-index:
```

## `fuggers_py.market.curves.multicurve`

```{eval-rst}
.. automodule:: fuggers_py.market.curves.multicurve
   :members:
   :member-order: bysource
   :no-index:
```

## `fuggers_py.market.curves.multicurve.index`

```{eval-rst}
.. automodule:: fuggers_py.market.curves.multicurve.index
   :members:
   :member-order: bysource
   :no-index:
```

## `fuggers_py.market.indices`

```{eval-rst}
.. automodule:: fuggers_py.market.indices
   :members:
   :member-order: bysource
   :no-index:
```

## `fuggers_py.market.indices.bond_index`

```{eval-rst}
.. automodule:: fuggers_py.market.indices.bond_index
   :members:
   :member-order: bysource
   :no-index:
```

## `fuggers_py.market.indices.conventions`

```{eval-rst}
.. automodule:: fuggers_py.market.indices.conventions
   :members:
   :member-order: bysource
   :no-index:
```

## `fuggers_py.market.indices.fixing_store`

```{eval-rst}
.. automodule:: fuggers_py.market.indices.fixing_store
   :members:
   :member-order: bysource
   :no-index:
```

## `fuggers_py.market.indices.overnight`

```{eval-rst}
.. automodule:: fuggers_py.market.indices.overnight
   :members:
   :member-order: bysource
   :no-index:
```

## `fuggers_py.market.vol_surfaces`

```{eval-rst}
.. automodule:: fuggers_py.market.vol_surfaces
   :members:
   :member-order: bysource
   :no-index:
```

## `fuggers_py.market.vol_surfaces.surface`

```{eval-rst}
.. automodule:: fuggers_py.market.vol_surfaces.surface
   :members:
   :member-order: bysource
   :no-index:
```

## `fuggers_py.market.vol_surfaces.sources`

```{eval-rst}
.. automodule:: fuggers_py.market.vol_surfaces.sources
   :members:
   :member-order: bysource
   :no-index:
```
