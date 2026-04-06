from __future__ import annotations

import os
from importlib import metadata
from pathlib import Path

import fuggers_py
import fuggers_py.adapters
import fuggers_py.adapters.file
import fuggers_py.adapters.json_codec
import fuggers_py.adapters.portfolio_store
import fuggers_py.adapters.sqlite_storage
import fuggers_py.adapters.storage
import fuggers_py.adapters.transport
import fuggers_py.calc
import fuggers_py.core
import fuggers_py.market
import fuggers_py.market.curves
import fuggers_py.market.indices
import fuggers_py.math
import fuggers_py.measures
import fuggers_py.measures.credit
import fuggers_py.measures.funding
import fuggers_py.measures.inflation
import fuggers_py.portfolio
import fuggers_py.portfolio.analytics.quote_outputs
import fuggers_py.portfolio.etf.pricing
import fuggers_py.pricers
import fuggers_py.pricers.bonds
import fuggers_py.pricers.bonds.options
import fuggers_py.pricers.credit
import fuggers_py.pricers.rates
import fuggers_py.pricers.rates.futures
import fuggers_py.pricers.rates.options
import fuggers_py.products
import fuggers_py.products.bonds
import fuggers_py.products.credit
import fuggers_py.products.funding
import fuggers_py.products.rates
import fuggers_py.products.rates.futures
import fuggers_py.products.rates.options
import fuggers_py.reference
import fuggers_py.reference.bonds
import fuggers_py.reference.inflation


def main() -> None:
    version = fuggers_py.__version__
    assert version
    assert any(char.isdigit() for char in version)
    try:
        source_root = (Path(__file__).resolve().parents[2] / "src").resolve()
        local_version = None
        for dist in metadata.distributions():
            if dist.metadata.get("Name") != "fuggers-py":
                continue
            if Path(dist.locate_file("")).resolve() == source_root:
                local_version = dist.version
                break
        if local_version is None:
            from fuggers_py._version import version as local_version
        assert local_version == version
    except metadata.PackageNotFoundError:
        pass

    expected_version = os.environ.get("EXPECTED_RELEASE_VERSION")
    if expected_version is not None:
        assert version == expected_version

    print(version)


if __name__ == "__main__":
    main()
