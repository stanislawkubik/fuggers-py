# `fuggers_py.reference`

Retired public namespace.

This path is no longer part of the public API.

For shared conventions and types, use the root package or the owning
first-layer module instead:

```python
from fuggers_py import (
    BondType,
    CalendarId,
    IndexConventions,
    IssuerType,
    OvernightCompounding,
    SettlementAdjustment,
    Tenor,
    USD_CPI_U_NSA,
    YieldCalculationRules,
)

from fuggers_py.bonds import YieldCalculationRules
from fuggers_py.inflation import USD_CPI_U_NSA
from fuggers_py.rates import IndexConventions, OvernightCompounding
```

Reference-data implementation now lives under the internal `_reference`
package.
