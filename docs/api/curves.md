# `fuggers_py.curves`

## Executive Summary

`fuggers_py.curves` provides a toolkit for building interest-rate term
structures from fixed-income quotes. It can bootstrap exact node curves or fit
smooth curves from swap quotes, bond quotes, and repo quotes. The main user
object is `YieldCurve`: callers give it quotes plus a `CurveSpec`, then query
rates, discount factors, and forward rates. The fit also returns one
`CalibrationReport` so users can inspect how closely the curve matched the
input quotes.

Use the root package for the first-layer curve API:

```python
from fuggers_py.curves import CurveSpec, YieldCurve
```

Advanced fit instruction records live one level below the root:

```python
from fuggers_py.curves.calibrators import CalibrationSpec
from fuggers_py.curves.kernels import KernelSpec
```

Most users do not need those advanced records. `YieldCurve.fit(...)` accepts
plain strings for the common path.

```{figure} ../_static/api/curves-main-workflow.svg
:alt: Curve fitting workflow
:align: center
```

## Public Surface

`fuggers_py.curves` exports only the first-layer curve objects and helpers:

| Export | What it does |
| --- | --- |
| `CurveSpec` | Names one curve snapshot and fixes its date, currency, day-count rule, curve type, and out-of-range rule. |
| `YieldCurve` | Concrete discounting curve. Build it from quotes with `YieldCurve.fit(...)` or from an already-built internal kernel. |
| `RatesTermStructure` | Base type for rate curves. |
| `DiscountingCurve` | Base type for curves that can return discount factors. |
| `CalibrationReport` | Fit-level report attached to `YieldCurve.calibration_report`. |
| `CalibrationPoint` | One fitted quote row inside a report. |
| `STANDARD_KEY_RATE_TENORS` | Built-in key-rate tenor grid. |

The root package does not export kernel classes, calibrator classes, old enum
controls, or compatibility aliases. Import advanced objects from their
submodules when you need them.

```{figure} ../_static/api/curves-class-hierarchy.svg
:alt: Curve class hierarchy
:align: center
```

## Basic Fit

```python
from fuggers_py import Date
from fuggers_py.curves import CurveSpec, YieldCurve
from fuggers_py.rates import SwapQuote

reference_date = Date.from_ymd(2026, 4, 9)

curve = YieldCurve.fit(
    quotes=[
        SwapQuote("USD-SWAP-1Y", tenor="1Y", rate=0.040, currency="USD", as_of=reference_date),
        SwapQuote("USD-SWAP-2Y", tenor="2Y", rate=0.041, currency="USD", as_of=reference_date),
        SwapQuote("USD-SWAP-5Y", tenor="5Y", rate=0.043, currency="USD", as_of=reference_date),
    ],
    spec=CurveSpec(
        name="USD SOFR",
        reference_date=reference_date,
        day_count="ACT/365F",
        currency="USD",
        type="overnight_discount",
        extrapolation_policy="hold_last_zero_rate",
    ),
)

print(curve.rate_at(2.0))
print(curve.discount_factor_at(5.0))
print(curve.forward_rate_between(1.0, 5.0))
```

`rate_at(...)` returns the public zero-rate view of the curve. A zero rate is
one rate from the curve date to a future tenor. `discount_factor_at(...)` turns
a future cash flow into today’s value on the curve date.

```{figure} ../_static/api/curves-yieldcurve-wrapper.svg
:alt: YieldCurve wrapper
:align: center
```

## `CurveSpec`

`CurveSpec` is the identity record for one curve snapshot.

```python
from fuggers_py import Date
from fuggers_py.curves import CurveSpec

spec = CurveSpec(
    name="USD OIS",
    reference_date=Date.from_ymd(2026, 4, 9),
    day_count="act/365f",
    currency="usd",
    type="overnight_discount",
    reference="SOFR",
    extrapolation_policy="error",
)
```

Important fields:

| Field | Meaning |
| --- | --- |
| `name` | Human-readable curve name. Whitespace is stripped. |
| `reference_date` | Curve date. Quote `as_of` values must match it. |
| `day_count` | Day-count label. Strings are normalized. |
| `currency` | Curve currency. Strings such as `"usd"` become `Currency.USD`. |
| `type` | Plain string such as `"nominal"`, `"real"`, `"overnight_discount"`, or `"projection"`. |
| `reference` | Optional benchmark or index label. |
| `extrapolation_policy` | Plain string controlling tenors above `max_t()`. |

Supported extrapolation policies:

| Policy | Behavior above `max_t()` |
| --- | --- |
| `"error"` | Raise `TenorOutOfBounds`. |
| `"hold_last_zero_rate"` | Hold the final public zero rate. |
| `"hold_last_native_rate"` | Ask the fitted kernel to hold its own final rate concept. |
| `"hold_last_forward_rate"` | Hold the terminal forward rate when the kernel supports that rule. |

## `YieldCurve.fit(...)`

```python
YieldCurve.fit(
    quotes,
    *,
    spec,
    kernel="linear_zero",
    method="bootstrap",
    bond_target="dirty_price",
    regressors=(),
    kernel_params=None,
)
```

Main inputs:

| Input | Meaning |
| --- | --- |
| `quotes` | Sequence of `SwapQuote`, `BondQuote`, or `RepoQuote` records. |
| `spec` | `CurveSpec` for the curve being built. |
| `kernel` | Curve shape name, such as `"linear_zero"` or `"nelson_siegel"`. |
| `method` | Fit route: `"bootstrap"` or `"global_fit"`. |
| `bond_target` | For global-fit bond price rows, choose `"dirty_price"` or `"clean_price"`. |
| `regressors` | Optional bond regressor names used by global fit. |
| `kernel_params` | Optional shape-specific settings, such as spline knots. |

Advanced callers may pass `KernelSpec` as `kernel` and `CalibrationSpec` as
`method`. This is for code that already owns the lower-level records:

```python
from fuggers_py.curves.calibrators import CalibrationSpec
from fuggers_py.curves.kernels import KernelSpec

curve = YieldCurve.fit(
    quotes,
    spec=spec,
    kernel=KernelSpec(kind="cubic_spline", parameters={"knots": (1.0, 2.0, 5.0)}),
    method=CalibrationSpec(method="global_fit", bond_target="clean_price"),
)
```

## Quote Inputs

Quote objects stay in the package that owns the instrument:

| Quote type | Import from | What the fitter reads |
| --- | --- | --- |
| `SwapQuote` | `fuggers_py.rates` | `instrument_id`, `tenor`, `rate`, `currency`, and `as_of`. The current fitter treats the rate as a zero-rate observation. |
| `BondQuote` | `fuggers_py.bonds` | The bond instrument, `as_of`, optional yield, optional clean or dirty price, optional fit weight, and optional regressors. |
| `RepoQuote` | `fuggers_py.funding` | `instrument_id`, repo term or dates, rate, currency, and `as_of`. |

Shared quote rules:

- `as_of` is required and must equal `CurveSpec.reference_date`.
- If quote currency is supplied, it must equal `CurveSpec.currency`.
- Bootstrap requires strictly increasing tenors after sorting.
- Global fit allows duplicate tenors but all rows must fit one target type:
  rates, discount factors, or bond prices.

## Fit Methods And Kernels

Bootstrap builds local curve nodes one by one. It is the exact-fit path.

| Kernel | Meaning |
| --- | --- |
| `"linear_zero"` | Zero-rate nodes with linear interpolation. |
| `"log_linear_discount"` | Discount-factor nodes with log-linear interpolation. |
| `"piecewise_constant"` | Zero rates stay flat until the next node. |
| `"piecewise_flat_forward"` | Short forward rates stay flat between nodes. |
| `"monotone_convex"` | Smooth zero-rate curve built from positive tenor nodes. |

Global fit estimates all parameters together. It is used when the curve shape
has fewer parameters than quote rows, or when bond regressors are included.

| Kernel | Required settings |
| --- | --- |
| `"cubic_spline"` | `kernel_params={"knots": (...)}` with at least three knots. |
| `"nelson_siegel"` | Optional `initial_parameters` and `max_t`. Needs at least four quotes. |
| `"svensson"` | Optional `initial_parameters` and `max_t`. Needs at least six quotes. |
| `"exponential_spline"` | `decay_factors` is required. Optional initial parameters and `max_t`. |

## Fit Reports

`YieldCurve.fit(...)` attaches a `CalibrationReport` to the returned curve.

```{figure} ../_static/api/curves-fit-reports.svg
:alt: Calibration report and calibration point model
:align: center
```

Common report fields:

| Field | Meaning |
| --- | --- |
| `converged` | Whether the solver reported success. Bootstrap reports `True` after a successful build. |
| `method` | `"bootstrap"` or `"global_fit"`. |
| `objective` | `"exact_fit"` or `"weighted_l2"`. |
| `iterations` | Solver iteration count. |
| `max_abs_residual` | Largest absolute fitted-minus-observed difference. |
| `points` | Tuple of `CalibrationPoint` rows. |
| `solver` | Solver name. |
| `regressors` | Regressor names used in global fit. |
| `regressor_coefficients` | Fitted coefficients in the same order as `regressors`. |
| `kernel` | Fitted kernel name for global fit. |
| `kernel_parameters` | Raw fitted kernel parameters for global fit. |
| `objective_value` | Final weighted objective value for global fit. |

Each `CalibrationPoint` contains the quote id, tenor, observed value, fitted
value, residual, observed kind, weight, and solver iterations. Global-fit rows
also carry the curve-only value and optional bond price or yield diagnostics.

## Curve Moves

`DiscountingCurve.shifted(...)` and `DiscountingCurve.bumped(...)` return a
new `DiscountingCurve`. Use `shifted(...)` when the whole zero-rate curve should
move by one amount. Use `bumped(...)` when one or more tenor points should move
and the move should be interpolated across a tenor grid.

```{figure} ../_static/api/curves-bumped-helper.svg
:alt: Curve move methods
:align: center
```

```python
from fuggers_py.curves import STANDARD_KEY_RATE_TENORS

shifted = curve.shifted(shift=0.0001)

bumped = curve.bumped(
    tenor_grid=STANDARD_KEY_RATE_TENORS,
    bumps={
        2.0: 0.0001,
        5.0: 0.0002,
    },
)

print(shifted.zero_rate_at(2.0))
print(bumped.zero_rate_at(2.0))
```

The returned object keeps the discounting methods, but it is a wrapper rather
than a fitted `YieldCurve`.

## Advanced Submodules

Advanced code may import these directly:

```python
from fuggers_py.curves.calibrators import CalibrationSpec
from fuggers_py.curves.conversion import ValueConverter
from fuggers_py.curves.kernels import KernelSpec
from fuggers_py.curves.multicurve import CurrencyPair, RateIndex
```

Concrete kernel classes live in their implementation modules under
`fuggers_py.curves.kernels`. They are not root exports.

## API Reference

.. automodule:: fuggers_py.curves
   :members:
   :undoc-members:
   :show-inheritance:
