from __future__ import annotations

import os
from importlib import metadata
from pathlib import Path

import fuggers_py
import fuggers_py.bonds
import fuggers_py.bonds.pricing
import fuggers_py.bonds.products
import fuggers_py.bonds.quotes
import fuggers_py.bonds.risk
import fuggers_py.bonds.spreads
import fuggers_py.bonds.yas
import fuggers_py.bonds.yields
import fuggers_py.credit
import fuggers_py.credit.analytics
import fuggers_py.credit.pricing
import fuggers_py.credit.products
import fuggers_py.credit.quotes
import fuggers_py.curves
import fuggers_py.funding
import fuggers_py.funding.analytics
import fuggers_py.funding.products
import fuggers_py.funding.quotes
import fuggers_py.inflation
import fuggers_py.inflation.analytics
import fuggers_py.inflation.reference
import fuggers_py.portfolio
import fuggers_py.portfolio.analytics.quote_outputs
import fuggers_py.portfolio.etf.pricing
import fuggers_py.rates
import fuggers_py.rates.indices
import fuggers_py.rates.pricing
import fuggers_py.rates.products
import fuggers_py.rates.quotes
import fuggers_py.vol_surfaces


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
