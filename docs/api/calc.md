# `fuggers_py.calc`

Retired public namespace.

This path is no longer part of the public API.

For ordinary library use, start with the domain-first modules and shared root
language:

```python
from fuggers_py import Date, Price
from fuggers_py.bonds import FixedBondBuilder
from fuggers_py.curves import YieldCurve
from fuggers_py.portfolio import Portfolio
```

Runtime and engine wiring now live under the internal `_calc` package.
