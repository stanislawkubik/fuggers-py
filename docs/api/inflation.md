# `fuggers_py.inflation`

Public home for CPI history, reference CPI helpers, index-ratio helpers,
inflation swaps, and inflation analytics.

Use one-layer imports from `fuggers_py.inflation`.

```python
from fuggers_py.inflation import (
    InflationSwapPricer,
    StandardCouponInflationSwap,
    USD_CPI_U_NSA,
    reference_cpi,
    reference_index_ratio,
)
```

This package currently exposes:

- inflation conventions and index definitions such as `USD_CPI_U_NSA`
- CPI loaders and parsers for monthly fixings
- reference CPI and index-ratio helpers
- inflation swap products and pricing
- inflation analytics such as `breakeven_inflation_rate` and `linker_swap_parity_check`

`TipsBond` stays in `fuggers_py.bonds` because it is still a bond instrument.

```{eval-rst}
.. automodule:: fuggers_py.inflation
   :members:
   :member-order: bysource
```
