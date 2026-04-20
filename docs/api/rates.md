# `fuggers_py.rates`

Public home for swaps, FRA, basis swaps, futures, swaptions, cap or floor
products, rates quotes, fixing storage, and rates pricing or risk helpers.

Use one-layer imports from `fuggers_py.rates`.

```python
from fuggers_py.rates import (
    FixedFloatSwap,
    IndexConventions,
    OvernightCompounding,
    SwapPricer,
    SwapQuote,
    Swaption,
)
```

This package currently exposes:

- rates products such as `FixedFloatSwap`, `BasisSwap`, `GovernmentBondFuture`, and `Swaption`
- quote records such as `SwapQuote`, `BasisSwapQuote`, `BondFutureQuote`, and `FxForwardQuote`
- pricing and risk helpers such as `SwapPricer`, `FraPricer`, `AssetSwapPricer`, and `swap_dv01`
- overnight convention and fixing records such as `IndexConventions` and `IndexFixingStore`

Built fitted curves still live in `fuggers_py.curves`. CPI history and
inflation swaps live in `fuggers_py.inflation`.

```{eval-rst}
.. automodule:: fuggers_py.rates
   :members:
   :member-order: bysource
```
