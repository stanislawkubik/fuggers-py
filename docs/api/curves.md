# `fuggers_py.curves`

Public home for fitted curve objects and curve fitting inputs.

Use one-layer imports from `fuggers_py.curves`.

```python
from fuggers_py.curves import (
    CalibrationSpec,
    CurveKernelKind,
    CurveSpec,
    CurveType,
    ExtrapolationPolicy,
    KernelSpec,
    YieldCurve,
)
```

This package currently exposes:

- curve objects such as `RatesTermStructure`, `DiscountingCurve`, `YieldCurve`, and `RelativeRateCurve`
- curve config records such as `CurveSpec`, `KernelSpec`, and `CalibrationSpec`
- fit enums such as `CurveType`, `RateSpace`, `ExtrapolationPolicy`, `CurveKernelKind`, `CalibrationMode`, and `CalibrationObjective`
- fit reports such as `CalibrationReport` and `GlobalFitReport`

Typed quotes stay with the domain that owns the quoted instrument. For example,
swap quotes come from `fuggers_py.rates`, and bond quotes come from
`fuggers_py.bonds`.

The main curve construction entry point today is `YieldCurve.fit(...)`.

```{eval-rst}
.. automodule:: fuggers_py.curves
   :members:
   :member-order: bysource
```
