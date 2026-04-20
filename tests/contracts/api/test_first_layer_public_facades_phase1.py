from __future__ import annotations

from fuggers_py.bonds import BondPricer, BondQuote, FixedBondBuilder, TipsBond
from fuggers_py.credit import Cds, CdsPricer, CdsQuote, bond_cds_basis
from fuggers_py.curves import YieldCurve
from fuggers_py.funding import HaircutQuote, RepoQuote, RepoTrade, repo_net_carry
from fuggers_py.inflation import reference_cpi, reference_index_ratio
from fuggers_py.rates import FixedFloatSwap, SwapPricer, SwapQuote, Swaption
from fuggers_py.vol_surfaces import VolatilitySurface


def test_phase1_acceptance_imports_work_from_first_layer_modules() -> None:
    assert YieldCurve.__name__ == "YieldCurve"
    assert VolatilitySurface.__name__ == "VolatilitySurface"
    assert BondPricer.__name__ == "BondPricer"
    assert SwapPricer.__name__ == "SwapPricer"
    assert CdsPricer.__name__ == "CdsPricer"
    assert RepoTrade.__name__ == "RepoTrade"


def test_target_state_canonical_import_examples_resolve_from_first_layer_modules() -> None:
    assert FixedBondBuilder.__name__ == "FixedBondBuilder"
    assert BondQuote.__name__ == "BondQuote"
    assert BondQuote.__module__ == "fuggers_py.bonds.quotes"
    assert TipsBond.__name__ == "TipsBond"
    assert FixedFloatSwap.__name__ == "FixedFloatSwap"
    assert SwapQuote.__name__ == "SwapQuote"
    assert SwapQuote.__module__ == "fuggers_py.rates.quotes"
    assert Swaption.__name__ == "Swaption"
    assert Cds.__name__ in {"Cds", "CreditDefaultSwap"}
    assert CdsQuote.__name__ == "CdsQuote"
    assert CdsQuote.__module__ == "fuggers_py.credit.quotes"
    assert RepoQuote.__name__ == "RepoQuote"
    assert RepoQuote.__module__ == "fuggers_py.funding.quotes"
    assert HaircutQuote.__name__ == "HaircutQuote"
    assert HaircutQuote.__module__ == "fuggers_py.funding.quotes"
    assert callable(reference_cpi)
    assert callable(reference_index_ratio)
    assert callable(bond_cds_basis)
    assert callable(repo_net_carry)
