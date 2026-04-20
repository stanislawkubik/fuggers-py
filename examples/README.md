# Examples

This folder is a small map of the example notebooks.

These examples are small public-surface walkthroughs. They show the current
first-layer import story. For the broader readiness note, see
[docs/STATUS.md](../docs/STATUS.md).

Current public imports for fitted market objects start at the first layer:

```python
from fuggers_py.curves import YieldCurve
from fuggers_py.vol_surfaces import VolatilitySurface
```

Current public examples:

- `01_public_curves_and_surfaces.ipynb`
  Small working example for `fuggers_py.curves` and
  `fuggers_py.vol_surfaces`.
- `05_fitted_nominal_real_breakeven_minimal.ipynb`
  Archived placeholder for the older fitted-bond notebook family while that
  surface is still being rewritten.

Older workflow notebooks that still depend on the older repo shape were moved
to `artifacts/legacy_examples/`.

`synthetic_data/` holds the small input files used by the notebooks.
