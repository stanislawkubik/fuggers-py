# `fuggers_py.bonds`

Public home for bond instruments, bond quotes, pricing, risk, spread
analytics, and YAS-style bond tools.

Use one-layer imports from `fuggers_py.bonds`.

```python
from fuggers_py.bonds import (
    BondPricer,
    BondQuote,
    FixedBondBuilder,
    TipsBond,
    YieldCalculationRules,
)
```

This package currently exposes:

- bond instruments and builders such as `FixedBondBuilder`, `CallableBondBuilder`, and `TipsBond`
- `BondQuote` for quotes tied to a concrete bond instrument
- bond convention bundles such as `YieldCalculationRules`
- bond pricing and risk types such as `BondPricer`, `BondRiskCalculator`, and `KeyRateDurations`
- bond yield and spread helpers such as `current_yield`, `g_spread`, and `z_spread`
- callable-bond models and YAS-style bond helpers

Inflation-linked bond instruments stay here because they are still bond
instruments. CPI helpers stay in `fuggers_py.inflation`.

```{eval-rst}
.. automodule:: fuggers_py.bonds
   :members:
   :member-order: bysource
```
