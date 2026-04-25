# Examples

This folder holds the current example notebook.

These examples are small public-surface walkthroughs. They show the current
first-layer import story. For the broader readiness note, see
[docs/STATUS.md](../docs/STATUS.md).

Current public imports for fitted market objects start at the first layer:

```python
from fuggers_py.curves import YieldCurve
```

Current public examples:

- `01_treasury_curve_fit.ipynb`
  Synthetic Treasury curve fit. It starts with default `YieldCurve.fit(...)`,
  then compares an advanced cubic-spline fit with two quote regressors,
  diagnostics, date-based curve queries, and curve bumps.

The notebook is self-contained and does not read files from `examples/`.
