from __future__ import annotations

import ast
import importlib
import inspect
from importlib import metadata
from pathlib import Path

import pytest

import fuggers_py
from fuggers_py import (
    BusinessDayConvention as root_business_day_convention,
    Compounding as root_compounding,
    Currency as root_currency,
    CurveId as root_curve_id,
    Date as root_date,
    DayCountConvention as root_day_count_convention,
    Frequency as root_frequency,
    InstrumentId as root_instrument_id,
    PortfolioId as root_portfolio_id,
    Price as root_price,
    Spread as root_spread,
    YearMonth as root_year_month,
    Yield as root_yield,
)
from fuggers_py._core import (
    BusinessDayConvention as core_business_day_convention,
    CalendarId as core_calendar_id,
    Compounding as core_compounding,
    Currency as core_currency,
    CurveId as core_curve_id,
    Date as core_date,
    DayCountConvention as core_day_count_convention,
    Frequency as core_frequency,
    InstrumentId as core_instrument_id,
    OptionType as core_option_type,
    PayReceive as core_pay_receive,
    PortfolioId as core_portfolio_id,
    Price as core_price,
    SettlementAdjustment as core_settlement_adjustment,
    Spread as core_spread,
    Tenor as core_tenor,
    YearMonth as core_year_month,
    Yield as core_yield,
    YieldCalculationRules as core_yield_calculation_rules,
)
from fuggers_py.bonds import FixedBondBuilder as bonds_fixed_bond_builder
from fuggers_py.bonds import current_yield as bonds_current_yield
from fuggers_py.curves import RatesTermStructure as public_rates_term_structure
from fuggers_py.inflation import USD_CPI_U_NSA as inflation_usd_cpi_u_nsa
from fuggers_py.portfolio import Portfolio as portfolio_portfolio
from fuggers_py.rates import IndexConventions as rates_index_conventions
from fuggers_py.rates import OvernightCompounding as rates_overnight_compounding
from tests.helpers._paths import REPO_ROOT

ROOT = REPO_ROOT
REMOVED_ROOTS = (
    "adapters",
    "analytics",
    "calc",
    "core",
    "data",
    "engine",
    "io",
    "market",
    "math",
    "measures",
    "pricers",
    "products",
    "reference",
)


def _local_metadata_version() -> str:
    source_root = (ROOT / "src").resolve()
    for dist in metadata.distributions():
        if dist.metadata.get("Name") != "fuggers-py":
            continue
        if Path(dist.locate_file("")).resolve() == source_root:
            return dist.version
    from fuggers_py._version import version

    return version


def test_explicit_submodule_imports_match_expected_public_symbols() -> None:
    from fuggers_py import Date, InstrumentId, Price
    from fuggers_py.bonds import FixedBondBuilder
    from fuggers_py.bonds import current_yield
    from fuggers_py.curves import RatesTermStructure
    from fuggers_py.portfolio import Portfolio

    assert Date is root_date
    assert root_date is core_date
    assert InstrumentId is root_instrument_id
    assert root_instrument_id is core_instrument_id
    assert Price is root_price
    assert root_price is core_price
    assert RatesTermStructure is public_rates_term_structure
    assert FixedBondBuilder is bonds_fixed_bond_builder
    assert current_yield is bonds_current_yield
    assert Portfolio is portfolio_portfolio


def test_root_package_binds_all_first_layer_modules_on_plain_attribute_access() -> None:
    assert fuggers_py.bonds is importlib.import_module("fuggers_py.bonds")
    assert fuggers_py.curves is importlib.import_module("fuggers_py.curves")
    assert fuggers_py.rates is importlib.import_module("fuggers_py.rates")
    assert fuggers_py.inflation is importlib.import_module("fuggers_py.inflation")
    assert fuggers_py.vol_surfaces is importlib.import_module("fuggers_py.vol_surfaces")
    assert fuggers_py.credit is importlib.import_module("fuggers_py.credit")
    assert fuggers_py.funding is importlib.import_module("fuggers_py.funding")
    assert fuggers_py.portfolio is importlib.import_module("fuggers_py.portfolio")


def test_phase1_first_layer_public_modules_are_importable() -> None:
    from fuggers_py.bonds import BondPricer
    from fuggers_py.credit import CdsPricer
    from fuggers_py.curves import YieldCurve
    from fuggers_py.funding import RepoTrade
    from fuggers_py.inflation import reference_cpi
    from fuggers_py.rates import SwapPricer
    from fuggers_py.vol_surfaces import VolatilitySurface

    assert YieldCurve.__name__ == "YieldCurve"
    assert VolatilitySurface.__name__ == "VolatilitySurface"
    assert BondPricer.__name__ == "BondPricer"
    assert SwapPricer.__name__ == "SwapPricer"
    assert CdsPricer.__name__ == "CdsPricer"
    assert RepoTrade.__name__ == "RepoTrade"
    assert callable(reference_cpi)


def test_root_shared_exports_match_phase2_surface() -> None:
    from fuggers_py import (
        BondType,
        BusinessDayConvention,
        CalendarId,
        Compounding,
        CurveId,
        Currency,
        Date,
        DayCountConvention,
        Frequency,
        IndexConventions,
        InstrumentId,
        IssuerType,
        OptionType,
        OvernightCompounding,
        PayReceive,
        PortfolioId,
        Price,
        SettlementAdjustment,
        Spread,
        Tenor,
        USD_CPI_U_NSA,
        YearMonth,
        Yield,
        YieldCalculationRules,
    )
    from fuggers_py.bonds import BondType as bonds_bond_type, IssuerType as bonds_issuer_type

    assert Date is root_date
    assert root_date is core_date
    assert Currency is root_currency
    assert root_currency is core_currency
    assert Frequency is root_frequency
    assert root_frequency is core_frequency
    assert Compounding is root_compounding
    assert root_compounding is core_compounding
    assert Price is root_price
    assert root_price is core_price
    assert Yield is root_yield
    assert root_yield is core_yield
    assert Spread is root_spread
    assert root_spread is core_spread
    assert InstrumentId is root_instrument_id
    assert root_instrument_id is core_instrument_id
    assert CurveId is root_curve_id
    assert root_curve_id is core_curve_id
    assert PortfolioId is root_portfolio_id
    assert root_portfolio_id is core_portfolio_id
    assert YearMonth is root_year_month
    assert root_year_month is core_year_month
    assert DayCountConvention is root_day_count_convention
    assert root_day_count_convention is core_day_count_convention
    assert BusinessDayConvention is root_business_day_convention
    assert root_business_day_convention is core_business_day_convention
    assert Tenor is core_tenor
    assert str(Tenor.parse("5Y")) == "5Y"
    assert CalendarId is core_calendar_id
    assert str(CalendarId.sifma()) == "SIFMA"
    assert SettlementAdjustment is core_settlement_adjustment
    assert SettlementAdjustment.MODIFIED_FOLLOWING.value == "MODIFIED_FOLLOWING"
    assert YieldCalculationRules is core_yield_calculation_rules
    assert YieldCalculationRules.us_corporate().description == "US Corporate Bond Convention"
    assert BondType is bonds_bond_type
    assert len({id(BondType), id(bonds_bond_type)}) == 1
    assert IssuerType is bonds_issuer_type
    assert len({id(IssuerType), id(bonds_issuer_type)}) == 1
    assert BondType.__module__ == "fuggers_py.bonds.types.bond_type"
    assert IssuerType.__module__ == "fuggers_py.bonds.types.issuer_type"
    assert BondType.FIXED_RATE.value == "FIXED_RATE"
    assert IssuerType.CORPORATE.value == "CORPORATE"
    assert PayReceive is core_pay_receive
    assert OptionType is core_option_type
    assert USD_CPI_U_NSA is inflation_usd_cpi_u_nsa
    assert IndexConventions is rates_index_conventions
    assert OvernightCompounding is rates_overnight_compounding


def _sourcefile_path(value: object) -> Path:
    try:
        source_path = inspect.getsourcefile(value)
    except TypeError:
        source_path = inspect.getsourcefile(type(value))
    assert source_path is not None
    return Path(source_path).resolve()


def _runtime_module_name(value: object) -> str:
    module_name = getattr(value, "__module__", None)
    if module_name is None:
        return type(value).__module__
    return str(module_name)


def test_root_shared_exports_resolve_to_final_source_files() -> None:
    expected_exports = {
        "Date": (root_date, "fuggers_py._core.types", ROOT / "src" / "fuggers_py" / "_core" / "types.py"),
        "Currency": (root_currency, "fuggers_py._core.types", ROOT / "src" / "fuggers_py" / "_core" / "types.py"),
        "Frequency": (root_frequency, "fuggers_py._core.types", ROOT / "src" / "fuggers_py" / "_core" / "types.py"),
        "Compounding": (root_compounding, "fuggers_py._core.types", ROOT / "src" / "fuggers_py" / "_core" / "types.py"),
        "Price": (root_price, "fuggers_py._core.types", ROOT / "src" / "fuggers_py" / "_core" / "types.py"),
        "Yield": (root_yield, "fuggers_py._core.types", ROOT / "src" / "fuggers_py" / "_core" / "types.py"),
        "Spread": (root_spread, "fuggers_py._core.types", ROOT / "src" / "fuggers_py" / "_core" / "types.py"),
        "InstrumentId": (root_instrument_id, "fuggers_py._core.ids", ROOT / "src" / "fuggers_py" / "_core" / "ids.py"),
        "CurveId": (root_curve_id, "fuggers_py._core.ids", ROOT / "src" / "fuggers_py" / "_core" / "ids.py"),
        "PortfolioId": (root_portfolio_id, "fuggers_py._core.ids", ROOT / "src" / "fuggers_py" / "_core" / "ids.py"),
        "YearMonth": (root_year_month, "fuggers_py._core.ids", ROOT / "src" / "fuggers_py" / "_core" / "ids.py"),
        "Tenor": (core_tenor, "fuggers_py._core.tenor", ROOT / "src" / "fuggers_py" / "_core" / "tenor.py"),
        "DayCountConvention": (
            root_day_count_convention,
            "fuggers_py._core.daycounts",
            ROOT / "src" / "fuggers_py" / "_core" / "daycounts.py",
        ),
        "BusinessDayConvention": (
            root_business_day_convention,
            "fuggers_py._core.calendars",
            ROOT / "src" / "fuggers_py" / "_core" / "calendars.py",
        ),
        "CalendarId": (
            core_calendar_id,
            "fuggers_py._core.calendar_id",
            ROOT / "src" / "fuggers_py" / "_core" / "calendar_id.py",
        ),
        "SettlementAdjustment": (
            core_settlement_adjustment,
            "fuggers_py._core.settlement_rules",
            ROOT / "src" / "fuggers_py" / "_core" / "settlement_rules.py",
        ),
        "YieldCalculationRules": (
            core_yield_calculation_rules,
            "fuggers_py._core.yield_calculation_rules",
            ROOT / "src" / "fuggers_py" / "_core" / "yield_calculation_rules.py",
        ),
        "BondType": (
            fuggers_py.BondType,
            "fuggers_py.bonds.types.bond_type",
            ROOT / "src" / "fuggers_py" / "bonds" / "types" / "bond_type.py",
        ),
        "IssuerType": (
            fuggers_py.IssuerType,
            "fuggers_py.bonds.types.issuer_type",
            ROOT / "src" / "fuggers_py" / "bonds" / "types" / "issuer_type.py",
        ),
        "PayReceive": (
            core_pay_receive,
            "fuggers_py._core.pay_receive",
            ROOT / "src" / "fuggers_py" / "_core" / "pay_receive.py",
        ),
        "OptionType": (
            core_option_type,
            "fuggers_py._core.option_type",
            ROOT / "src" / "fuggers_py" / "_core" / "option_type.py",
        ),
        "USD_CPI_U_NSA": (
            inflation_usd_cpi_u_nsa,
            "fuggers_py.inflation.conventions",
            ROOT / "src" / "fuggers_py" / "inflation" / "conventions.py",
        ),
        "IndexConventions": (
            rates_index_conventions,
            "fuggers_py.rates.indices",
            ROOT / "src" / "fuggers_py" / "rates" / "indices.py",
        ),
        "OvernightCompounding": (
            rates_overnight_compounding,
            "fuggers_py.rates.indices",
            ROOT / "src" / "fuggers_py" / "rates" / "indices.py",
        ),
    }

    for export_name, (value, expected_module, expected_path) in expected_exports.items():
        assert _runtime_module_name(value) == expected_module, export_name
        assert _sourcefile_path(value) == expected_path.resolve(), export_name


def test_bond_type_and_issuer_type_have_one_live_owner_class_each() -> None:
    from fuggers_py import BondType, IssuerType
    from fuggers_py.bonds import BondType as bonds_bond_type, IssuerType as bonds_issuer_type

    assert {id(BondType), id(bonds_bond_type)} == {id(BondType)}
    assert {id(IssuerType), id(bonds_issuer_type)} == {id(IssuerType)}

    expected_definition_paths = {
        "BondType": ROOT / "src" / "fuggers_py" / "bonds" / "types" / "bond_type.py",
        "IssuerType": ROOT / "src" / "fuggers_py" / "bonds" / "types" / "issuer_type.py",
    }

    for class_name, expected_path in expected_definition_paths.items():
        class_definition_paths = [
            path
            for path in sorted((ROOT / "src" / "fuggers_py").rglob("*.py"))
            if any(
                isinstance(node, ast.ClassDef) and node.name == class_name
                for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
            )
        ]
        assert class_definition_paths == [expected_path]


def test_root_package_is_a_small_direct_import_surface() -> None:
    root_init = Path(fuggers_py.__file__)
    tree = ast.parse(root_init.read_text(encoding="utf-8"))

    assert "__getattr__" not in {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
    assert "__getattr__" not in {node.name for node in ast.walk(tree) if isinstance(node, ast.AsyncFunctionDef)}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                assert node.func.id not in {"import_module", "__import__"}
            elif isinstance(node.func, ast.Attribute):
                assert not (
                    isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "importlib"
                    and node.func.attr == "import_module"
                )


def test_top_level_package_exports_match_phase2_surface() -> None:
    assert set(fuggers_py.__all__) == {
        "__version__",
        "bonds",
        "credit",
        "curves",
        "Date",
        "Currency",
        "Frequency",
        "Compounding",
        "Price",
        "Yield",
        "Spread",
        "InstrumentId",
        "CurveId",
        "PortfolioId",
        "YearMonth",
        "Tenor",
        "DayCountConvention",
        "BusinessDayConvention",
        "CalendarId",
        "SettlementAdjustment",
        "YieldCalculationRules",
        "BondType",
        "IssuerType",
        "PayReceive",
        "OptionType",
        "USD_CPI_U_NSA",
        "IndexConventions",
        "OvernightCompounding",
        "funding",
        "inflation",
        "portfolio",
        "rates",
        "vol_surfaces",
    }


def test_top_level_package_module_exports_are_bound_attributes() -> None:
    for export_name in ("curves", "vol_surfaces", "bonds", "rates", "inflation", "credit", "funding", "portfolio"):
        assert hasattr(fuggers_py, export_name)


def test_root_does_not_export_domain_objects_directly() -> None:
    assert not hasattr(fuggers_py, "BondPricer")
    assert not hasattr(fuggers_py, "YieldCurve")


def test_top_level_package_version_is_available_and_matches_distribution_metadata() -> None:
    assert fuggers_py.__version__
    assert any(char.isdigit() for char in fuggers_py.__version__)
    assert _local_metadata_version() == fuggers_py.__version__


@pytest.mark.parametrize("root_name", REMOVED_ROOTS)
def test_removed_roots_are_not_importable(root_name: str) -> None:
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module(f"fuggers_py.{root_name}")
