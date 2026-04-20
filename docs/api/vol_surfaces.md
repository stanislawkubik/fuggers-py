# `fuggers_py.vol_surfaces`

Public home for volatility surface records and surface source interfaces.

Use one-layer imports from `fuggers_py.vol_surfaces`.

```python
from fuggers_py.vol_surfaces import (
    InMemoryVolatilitySource,
    VolPoint,
    VolQuoteType,
    VolSurfaceType,
    VolatilitySurface,
)
```

This package currently exposes:

- `VolatilitySurface` for the built surface snapshot
- `VolPoint` for one quoted surface point
- `VolQuoteType` and `VolSurfaceType` for the quote and surface meanings
- `VolatilitySource` and `InMemoryVolatilitySource` for loading and serving surfaces

Option pricers consume these objects, but the public surface records live here.

```{eval-rst}
.. automodule:: fuggers_py.vol_surfaces
   :members:
   :member-order: bysource
```
