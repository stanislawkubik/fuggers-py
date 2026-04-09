# `fuggers_py.market`

Market state, quotes, fixings, indices, and curve abstractions.

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

```{eval-rst}
.. automodule:: fuggers_py.market.curves
   :members:
   :member-order: bysource
   :no-index:
```

## Bond Curves

For the bond-curve workflow, it helps to separate two ideas:

1. the instruments are the observations
2. the curve shape defines the term-structure family we are allowed to fit

So in:

```python
curve = BondCurve(
    quotes,
    shape=CubicSplineZeroRateCurveModel((2, 5, 10)),
)
```

the bond quotes are the observations, while `(2, 5, 10)` are spline knot tenors in years. They are not rates. The curve solves one zero-rate parameter at each knot, then interpolates the zero curve between them with a natural cubic spline.

Why this matters:

1. a bond maturity is an observation date, not by itself a complete curve definition
2. coupon bonds need discounting at many cash-flow dates before maturity
3. the spline knots are the parameter grid that controls curve flexibility

The public nominal bond surface is now:

```python
curve = BondCurve(
    quotes,
    shape=ExponentialSplineCurveModel(),
    objective=CurveObjective.L2,
)
```

`BondCurve` is itself the calibrated yield curve. It owns:

1. the fitted term structure
2. the calibrated parameters
3. the calibration diagnostics
4. the per-bond fit points

The exact object stack is:

```text
BondQuote list
-> BondCurve(...)
-> BondCurve.term_structure
```

What those pieces mean:

1. `BondQuote`
   One market observation bound to one concrete bond.

2. `BondCurve`
   The public curve object you construct and then use.

3. `BondCurve.term_structure`
   The actual fitted tenor-to-rate function.

The fitted `term_structure` is very small. In the current code it only needs:

```python
class TermStructure(ABC):
    def date(self) -> Date: ...
    def value_at_tenor(self, tenor_years: float) -> float: ...
```

In the nominal bond path:

1. `date()` is the curve date
2. `value_at_tenor(t)` returns the continuous zero rate at tenor `t`

So you call curve methods directly:

```python
curve.discount_factor(date)
curve.zero_rate(date)
curve.get_bond("UST5Y")
curve.richest()
curve.cheapest()
```

The important structural point is:

1. the fitted mathematical function lives only in `curve.term_structure`
2. `curve.term_structure.value_at_tenor(t)` is the continuous zero rate at tenor `t`
3. `BondCurve` derives `discount_factor(...)` and `zero_rate(...)` directly from that term structure
4. there is no extra `RateCurve` adapter in the nominal bond path anymore

### Accepted Input Types

`CubicSplineZeroRateCurveModel` currently accepts:

1. `knot_tenors: tuple[Decimal | int | float | str, ...]`
2. `initial_zero_rates: tuple[Decimal | int | float | str, ...] | None`

All of those values are normalized to `Decimal` internally.

Examples:

```python
CubicSplineZeroRateCurveModel((2, 5, 10))
CubicSplineZeroRateCurveModel(("2.0", "5.0", "10.0"))
CubicSplineZeroRateCurveModel(
    knot_tenors=(2, 5, 10),
    initial_zero_rates=(0.02, 0.025, 0.03),
)
```

`initial_zero_rates` are raw decimal rates, so `0.02` means 2 percent.

`ExponentialSplineCurveModel` behaves the same way for its `decay_factors` input:

1. `decay_factors: tuple[Decimal | int | float | str, ...]`

and those values are also normalized to `Decimal` internally.

### TIPS Path

The current TIPS path has not been moved to a dedicated concrete curve class yet.

It still uses the legacy fitter surface:

1. `BondQuote` objects bound to `TipsBond` instruments
2. `TipsRealBondPricingAdapter(fixing_source=...)`

So the current TIPS flow is:

```python
fit = BondCurveFitter(
    curve_model=CubicSplineZeroRateCurveModel((2, 5, 10)),
    pricing_adapter=TipsRealBondPricingAdapter(fixing_source),
).fit(tips_quotes)
```

The quote still contains the instrument. The extra object here is the inflation fixing source required by the current TIPS pricing adapter. That is why TIPS still sits outside the clean nominal `BondCurve(...)` surface for now.

## `fuggers_py.market.indices`

```{eval-rst}
.. automodule:: fuggers_py.market.indices
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
