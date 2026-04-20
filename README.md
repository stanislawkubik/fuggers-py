# fuggers-py

[![Docs](https://img.shields.io/readthedocs/fuggers-py?label=docs)](https://fuggers-py.readthedocs.io/en/latest/)

`fuggers-py` is a fixed-income analytics library with domain-first public
modules.

Public docs: [fuggers-py.readthedocs.io](https://fuggers-py.readthedocs.io/en/latest/).
Current feature readiness and the pre-`1.0` stability policy are documented in
[docs/STATUS.md](docs/STATUS.md).

## Status

- `fuggers-py` is still pre-`1.0`.
- Core bond, inflation, and analytics workflows are already substantial and well-tested.
- Some newer or broader surfaces, especially volatility surfaces and parts of the runtime/integration layer, are still moving and may change before `1.x`.
- Backwards compatibility is not promised yet. The plan is to formalize that policy starting with the first `1.x` release.

## Package layout

- `fuggers_py.curves`: fitted curve objects and curve fitting inputs
- `fuggers_py.vol_surfaces`: volatility surface records and surface sources
- `fuggers_py.bonds`: bond instruments, quotes, pricing, risk, spreads, and YAS-style tools
- `fuggers_py.rates`: swaps, futures, swaptions, fixing storage, and rates pricing or risk
- `fuggers_py.inflation`: CPI helpers, inflation swaps, and inflation analytics
- `fuggers_py.credit`: CDS instruments, quotes, pricing, and bond-CDS basis analytics
- `fuggers_py.funding`: repo trades, repo or haircut quotes, and financing analytics
- `fuggers_py.portfolio`: holdings, aggregation, attribution, liquidity, ETF, stress, results
- Shared types such as `Date`, `Currency`, `Price`, `Yield`, `InstrumentId`, and `Tenor` come from the `fuggers_py` root

Internal implementation roots such as `_core`, `_math`, `_market`, `_calc`,
`_adapters`, `_products`, `_pricers`, `_measures`, and `_reference` are not
public API.

See [docs/SRC_STRUCTURE.md](docs/SRC_STRUCTURE.md) for the directory-by-directory structure under `src/fuggers_py/`.
See [docs/MODULE_REFERENCE.md](docs/MODULE_REFERENCE.md) for the archived module-reference note from before the public API cutover.
See [docs/STATUS.md](docs/STATUS.md) for what is ready today, what is still scaffold-only, and what is expected to change before `1.x`.

## Quick start

```python
from decimal import Decimal

from fuggers_py import Currency, Date, Price
from fuggers_py.bonds import FixedBondBuilder

as_of = Date.from_ymd(2026, 1, 15)
clean_price = Price.new(Decimal("99.125"), Currency.USD)
builder = FixedBondBuilder.new()
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
