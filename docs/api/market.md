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

The package currently exposes the public rates curve root and the small set of
objects that define what a rates curve means:

- `CurveSpec`: the business identity of one curve snapshot
- `CurveType`: the economic type of the curve, such as nominal or real
- `RateSpace`: the meaning of the rate returned by the curve
- `ExtrapolationPolicy`: the rule for tenors past the curve domain
- `RatesTermStructure`: the public base class for rates curves

The key contract is simple:

- `curve.rate_space` tells you what kind of rate the curve returns
- `curve.rate_at(tenor)` returns the rate at that tenor in the curve's `rate_space`
- `curve.max_t()` returns the last supported tenor
- `curve.validate_rate(tenor)` checks the tenor domain and verifies that the returned rate is finite

In plain language, this is the point:

- a curve giving you `0.04` at `5.0` is not enough by itself
- you also need to know what kind of rate that `0.04` is
- `curve.rate_space` gives that meaning
- `curve.rate_at(tenor)` gives the actual number

So you should read the API like this:

- `curve.rate_at(5.0)` answers "what is your 5-year number?"
- `curve.rate_space` answers "what kind of number is it?"

That keeps the root contract honest. At this stage the base curve only promises:

- a tenor-to-rate mapping
- a clear meaning for the returned rate
- a clear tenor domain

It does not yet promise that every curve can discount cash flows. That comes
later with discounting-style subclasses.

The package also keeps a few shared helpers:

- `conversion.py`: numeric conversions between discount factors, zero rates, and forward rates
- `errors.py`: shared curve exceptions such as `InvalidCurveInput` and `TenorOutOfBounds`
- `multicurve/`: identifiers used for later multi-curve assembly, currently `RateIndex` and `CurrencyPair`

Today the public tree stops at `RatesTermStructure`. Discounting curves,
breakeven curves, and fit engines are not in the rebuilt public module yet.

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
