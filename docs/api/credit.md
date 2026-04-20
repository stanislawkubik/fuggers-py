# `fuggers_py.credit`

Public home for CDS instruments, CDS quote records, CDS pricing, and bond-CDS
basis analytics.

Use one-layer imports from `fuggers_py.credit`.

```python
from fuggers_py.credit import Cds, CdsPricer, CdsQuote, bond_cds_basis
```

This package currently exposes:

- CDS instruments such as `Cds` and `CreditDefaultSwap`
- `CdsQuote` for CDS market quotes
- pricing types such as `CdsPricer` and `CdsPricingResult`
- credit relative-value helpers such as `bond_cds_basis` and `adjusted_cds_spread`

```{eval-rst}
.. automodule:: fuggers_py.credit
   :members:
   :member-order: bysource
```
