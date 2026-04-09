# fuggers-py

[![Docs](https://img.shields.io/readthedocs/fuggers-py?label=docs)](https://fuggers-py.readthedocs.io/en/latest/)

`fuggers-py` is a fixed-income analytics library organized by responsibility-first package boundaries.

Public docs: [fuggers-py.readthedocs.io](https://fuggers-py.readthedocs.io/en/latest/).
Current feature readiness and the pre-`1.0` stability policy are documented in
[docs/STATUS.md](docs/STATUS.md).

## Status

- `fuggers-py` is still pre-`1.0`.
- Core bond, inflation, and analytics workflows are already substantial and well-tested.
- Some newer or broader surfaces, especially volatility surfaces and parts of the runtime/integration layer, are still moving and may change before `1.x`.
- Backwards compatibility is not promised yet. The plan is to formalize that policy starting with the first `1.x` release.

## Package layout

- `fuggers_py.core`: primitives, calendars, daycounts, shared ids, common low-level types
- `fuggers_py.reference`: conventions, security metadata, contract specs, index metadata
- `fuggers_py.market`: market state, quote/fixing objects, indices, and snapshots
- `fuggers_py.products`: contract definitions by product family
- `fuggers_py.pricers`: valuation engines and low-level risk algorithms
- `fuggers_py.measures`: user-facing analytics and desk-style measures
- `fuggers_py.portfolio`: holdings, aggregation, attribution, liquidity, ETF, stress, results
- `fuggers_py.calc`: orchestration, dispatch, graph execution, and runtime wiring
- `fuggers_py.adapters`: file, storage, JSON, transport, and external-boundary adapters
- `fuggers_py.math`: numerical infrastructure

See [docs/SRC_STRUCTURE.md](docs/SRC_STRUCTURE.md) for the directory-by-directory structure under `src/fuggers_py/`.
See [docs/MODULE_REFERENCE.md](docs/MODULE_REFERENCE.md) for the full file-by-file module inventory of the live source tree.
See [docs/STATUS.md](docs/STATUS.md) for what is ready today, what is still scaffold-only, and what is expected to change before `1.x`.

## Quick start

```python
from decimal import Decimal

from fuggers_py.calc import PricingSpec
from fuggers_py.core import Currency, Date, Price
from fuggers_py.market.state import QuoteSide

as_of = Date.from_ymd(2026, 1, 15)
clean_price = Price.new(Decimal("99.125"), Currency.USD)
spec = PricingSpec(quote_side=QuoteSide.MID)
```

## Development

Install the project in editable mode:

```bash
python -m pip install -e ".[dev,engine,examples]"
```

Run the test suite:

```bash
pytest -q
```

Build the docs locally:

```bash
python -m pip install -e ".[docs]"
make docs
```

The built site will be available at `docs/_build/html/index.html`.

Examples live under `examples/` as paired research scripts and notebooks where applicable. Library code lives under `src/`. The test suite is split into `tests/unit/`, `tests/integration/`, and `tests/contracts/`.
