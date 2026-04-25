from __future__ import annotations

import ast
import importlib
from pathlib import Path

import pytest

from fuggers_py import CalendarId as root_calendar_id
from fuggers_py import OptionType as root_option_type
from fuggers_py import PayReceive as root_pay_receive
from fuggers_py import SettlementAdjustment as root_settlement_adjustment
from fuggers_py import Tenor as root_tenor
from fuggers_py import YieldCalculationRules as root_yield_calculation_rules
from fuggers_py._core import CalendarId, OptionType, PayReceive, SettlementAdjustment, Tenor, YieldCalculationRules
from tests.helpers._paths import REPO_ROOT

BONDS_MODULE = "fuggers_py.bonds"
REFERENCE_MODULE = "fuggers_py._reference"


def test_shared_language_types_resolve_to__core_owners() -> None:
    assert Tenor is root_tenor
    assert CalendarId is root_calendar_id
    assert SettlementAdjustment is root_settlement_adjustment
    assert YieldCalculationRules is root_yield_calculation_rules
    assert PayReceive is root_pay_receive
    assert OptionType is root_option_type
    assert Tenor.__module__ == "fuggers_py._core.tenor"
    assert CalendarId.__module__ == "fuggers_py._core.calendar_id"
    assert SettlementAdjustment.__module__ == "fuggers_py._core.settlement_rules"
    assert YieldCalculationRules.__module__ == "fuggers_py._core.yield_calculation_rules"
    assert PayReceive.__module__ == "fuggers_py._core.pay_receive"
    assert OptionType.__module__ == "fuggers_py._core.option_type"


def test_old_owner_modules_no_longer_define_shared_language_types() -> None:
    deleted_old_owner_candidates = [
        REPO_ROOT / "src" / "fuggers_py" / "_reference" / "bonds" / "types" / "tenor.py",
        REPO_ROOT / "src" / "fuggers_py" / "_reference" / "bonds" / "types" / "settlement_rules.py",
        REPO_ROOT / "src" / "fuggers_py" / "_reference" / "bonds" / "types" / "yield_rules.py",
        REPO_ROOT / "src" / "fuggers_py" / "bonds" / "types" / "tenor.py",
        REPO_ROOT / "src" / "fuggers_py" / "bonds" / "types" / "settlement_rules.py",
        REPO_ROOT / "src" / "fuggers_py" / "bonds" / "types" / "yield_rules.py",
    ]
    for path in deleted_old_owner_candidates:
        assert path.exists() is False

    old_owner_candidates = {
        REPO_ROOT / "src" / "fuggers_py" / "_reference" / "bonds" / "types" / "identifiers.py": "CalendarId",
        REPO_ROOT / "src" / "fuggers_py" / "bonds" / "types" / "identifiers.py": "CalendarId",
        REPO_ROOT / "src" / "fuggers_py" / "_products" / "rates" / "common.py": "PayReceive",
        REPO_ROOT / "src" / "fuggers_py" / "_products" / "rates" / "options" / "_common.py": "OptionType",
    }

    for path, class_name in old_owner_candidates.items():
        if not path.exists():
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        defined_classes = {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, ast.ClassDef)
        }
        assert class_name not in defined_classes


def test_old_reference_routes_are_deleted() -> None:
    for module_name in (REFERENCE_MODULE, REFERENCE_MODULE + ".reference_data", REFERENCE_MODULE + ".bonds"):
        with pytest.raises(ModuleNotFoundError):
            importlib.import_module(module_name)


def test_old_products_rates_routes_stop_binding_moved_phase1_names() -> None:
    products_rates = importlib.import_module("fuggers_py.rates")
    products_rates_common = importlib.import_module("fuggers_py.rates.common")
    products_rates_options = importlib.import_module("fuggers_py.rates.options")
    products_rates_options_common = importlib.import_module("fuggers_py.rates.options._product_common")

    for module, forbidden_names in (
        (products_rates, ("PayReceive", "OptionType")),
        (products_rates_common, ("PayReceive",)),
        (products_rates_options, ("OptionType",)),
        (products_rates_options_common, ("OptionType",)),
    ):
        for name in forbidden_names:
            assert name not in vars(module)
            assert hasattr(module, name) is False


def test_bonds_types_package_stops_binding_shared_language_names() -> None:
    tree = ast.parse(
        (REPO_ROOT / "src" / "fuggers_py" / "bonds" / "types" / "__init__.py").read_text(encoding="utf-8")
    )
    bound_names: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.ImportFrom):
            bound_names.update(alias.asname or alias.name for alias in node.names)
        elif isinstance(node, ast.Assign):
            bound_names.update(target.id for target in node.targets if isinstance(target, ast.Name))

    for name in ("Tenor", "CalendarId", "SettlementAdjustment", "YieldCalculationRules"):
        assert name not in bound_names


def test_repo_imports_stop_pulling_phase1_shared_names_from_old_routes() -> None:
    target_names = {
        "Tenor",
        "CalendarId",
        "SettlementAdjustment",
        "YieldCalculationRules",
        "PayReceive",
        "OptionType",
        "BondType",
        "IssuerType",
    }
    old_module_prefixes = ("fuggers_py._reference", "fuggers_py.rates")
    package_root = REPO_ROOT / "src" / "fuggers_py"
    violations: set[str] = set()

    def current_package(path: Path) -> str:
        if not path.is_relative_to(package_root):
            return ""
        relative = path.relative_to(package_root).with_suffix("")
        parts = list(relative.parts)
        if parts[-1] == "__init__":
            parts = parts[:-1]
        current_module = "fuggers_py" + ("." + ".".join(parts) if parts else "")
        return current_module if path.name == "__init__.py" else current_module.rsplit(".", 1)[0]

    def resolved_import_base_module(path: Path, node: ast.ImportFrom) -> str:
        if node.level == 0:
            return node.module or ""
        base_parts = current_package(path).split(".")
        trim_count = max(node.level - 1, 0)
        if trim_count:
            base_parts = base_parts[:-trim_count]
        if node.module is None:
            return ".".join(base_parts)
        return ".".join([*base_parts, node.module])

    for root_name in ("src", "tests"):
        for path in sorted((REPO_ROOT / root_name).rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            old_import_aliases: dict[str, str] = {}

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        module_name = alias.name
                        if any(
                            module_name == prefix or module_name.startswith(prefix + ".")
                            for prefix in old_module_prefixes
                        ):
                            old_import_aliases[alias.asname or module_name.split(".")[-1]] = module_name
                elif isinstance(node, ast.ImportFrom):
                    base_module = resolved_import_base_module(path, node)
                    if not base_module or not any(
                        base_module == prefix or base_module.startswith(prefix + ".")
                        for prefix in old_module_prefixes
                    ):
                        continue
                    matched_names = sorted(alias.name for alias in node.names if alias.name in target_names)
                    if matched_names:
                        violations.add(
                            f"{path.relative_to(REPO_ROOT)}:{node.lineno} -> {base_module}: {', '.join(matched_names)}"
                        )

            class _OldImportAttributeVisitor(ast.NodeVisitor):
                def visit_Attribute(self, node: ast.Attribute) -> None:
                    if isinstance(node.value, ast.Name):
                        module_name = old_import_aliases.get(node.value.id)
                        if module_name is not None and node.attr in target_names:
                            violations.add(
                                f"{path.relative_to(REPO_ROOT)}:{node.lineno} -> {module_name}: {node.attr}"
                            )
                    self.generic_visit(node)

            _OldImportAttributeVisitor().visit(tree)

    assert sorted(violations) == []


def test__core_init_imports_shared_language_types_from_local_owner_modules() -> None:
    tree = ast.parse((REPO_ROOT / "src" / "fuggers_py" / "_core" / "__init__.py").read_text(encoding="utf-8"))

    expected_import_source_by_name = {
        "CalendarId": (1, "calendar_id"),
        "OptionType": (1, "option_type"),
        "PayReceive": (1, "pay_receive"),
        "SettlementAdjustment": (1, "settlement_rules"),
        "Tenor": (1, "tenor"),
        "YieldCalculationRules": (1, "yield_calculation_rules"),
    }
    actual_import_sources: dict[str, set[tuple[int, str | None] | tuple[str, str]]] = {
        name: set() for name in expected_import_source_by_name
    }

    for node in tree.body:
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name in actual_import_sources:
                    actual_import_sources[alias.name].add((node.level, node.module))
        elif isinstance(node, ast.Import):
            for alias in node.names:
                bound_name = alias.asname or alias.name.split(".")[-1]
                if bound_name in actual_import_sources:
                    actual_import_sources[bound_name].add(("import", alias.name))

    assert actual_import_sources == {
        name: {source}
        for name, source in expected_import_source_by_name.items()
    }


def test_bond_type_and_issuer_type_have_exactly_one_live_class_definition() -> None:
    from fuggers_py import BondType as root_bond_type, IssuerType as root_issuer_type
    from fuggers_py.bonds import BondType as bonds_bond_type, IssuerType as bonds_issuer_type

    assert len({id(root_bond_type), id(bonds_bond_type)}) == 1
    assert len({id(root_issuer_type), id(bonds_issuer_type)}) == 1

    defining_paths = {
        "BondType": [REPO_ROOT / "src" / "fuggers_py" / "bonds" / "types" / "bond_type.py"],
        "IssuerType": [REPO_ROOT / "src" / "fuggers_py" / "bonds" / "types" / "issuer_type.py"],
    }

    for class_name, expected_paths in defining_paths.items():
        actual_paths: list[Path] = []
        for path in sorted((REPO_ROOT / "src" / "fuggers_py").rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            if any(isinstance(node, ast.ClassDef) and node.name == class_name for node in ast.walk(tree)):
                actual_paths.append(path)
        assert actual_paths == expected_paths


def test_shared_bond_support_types_and_errors_resolve_to__core_owners() -> None:
    core_compounding = importlib.import_module("fuggers_py._core.compounding")
    core_ex_dividend = importlib.import_module("fuggers_py._core.ex_dividend")
    core_stub_rules = importlib.import_module("fuggers_py._core.stub_rules")
    core_yield_convention = importlib.import_module("fuggers_py._core.yield_convention")
    bonds_types = importlib.import_module(BONDS_MODULE + ".types")
    reference_types = bonds_types
    bonds_root = importlib.import_module(BONDS_MODULE)

    assert bonds_types.CompoundingMethod is core_compounding.CompoundingMethod
    assert reference_types.CompoundingMethod is core_compounding.CompoundingMethod
    assert bonds_types.CompoundingKind is core_compounding.CompoundingKind
    assert reference_types.CompoundingKind is core_compounding.CompoundingKind
    assert bonds_types.ExDividendRules is core_ex_dividend.ExDividendRules
    assert reference_types.ExDividendRules is core_ex_dividend.ExDividendRules
    assert bonds_types.StubPeriodRules is core_stub_rules.StubPeriodRules
    assert reference_types.StubPeriodRules is core_stub_rules.StubPeriodRules
    assert bonds_types.StubType is core_stub_rules.StubType
    assert reference_types.StubType is core_stub_rules.StubType
    assert bonds_types.YieldConvention is core_yield_convention.YieldConvention
    assert reference_types.YieldConvention is core_yield_convention.YieldConvention
    assert bonds_types.AccruedConvention is core_yield_convention.AccruedConvention
    assert reference_types.AccruedConvention is core_yield_convention.AccruedConvention
    assert bonds_types.RoundingConvention is core_yield_convention.RoundingConvention
    assert reference_types.RoundingConvention is core_yield_convention.RoundingConvention
    assert bonds_types.RoundingKind is core_yield_convention.RoundingKind
    assert reference_types.RoundingKind is core_yield_convention.RoundingKind

    expected_error_module = BONDS_MODULE + ".errors"
    assert bonds_root.InvalidBondSpec.__module__ == expected_error_module
    assert bonds_root.InvalidIdentifier.__module__ == expected_error_module
    assert bonds_root.BondPricingError.__module__ == expected_error_module
    assert bonds_root.ScheduleError.__module__ == expected_error_module
    assert bonds_root.SettlementError.__module__ == expected_error_module
    assert bonds_root.YieldConvergenceFailed.__module__ == expected_error_module

    assert core_compounding.CompoundingMethod.__module__ == "fuggers_py._core.compounding"
    assert core_ex_dividend.ExDividendRules.__module__ == "fuggers_py._core.ex_dividend"
    assert core_stub_rules.StubPeriodRules.__module__ == "fuggers_py._core.stub_rules"
    assert core_yield_convention.YieldConvention.__module__ == "fuggers_py._core.yield_convention"


def test__core_owner_modules_do_not_import_reference_bond_support() -> None:
    target_paths = [
        REPO_ROOT / "src" / "fuggers_py" / "_core" / "tenor.py",
        REPO_ROOT / "src" / "fuggers_py" / "_core" / "calendar_id.py",
        REPO_ROOT / "src" / "fuggers_py" / "_core" / "settlement_rules.py",
        REPO_ROOT / "src" / "fuggers_py" / "_core" / "yield_calculation_rules.py",
    ]

    violations: list[str] = []
    for path in target_paths:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "fuggers_py.bonds" or alias.name.startswith("fuggers_py.bonds."):
                        violations.append(f"{path.relative_to(REPO_ROOT)}:{node.lineno} -> {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                if node.level != 0 or node.module is None:
                    continue
                if node.module == "fuggers_py.bonds" or node.module.startswith("fuggers_py.bonds."):
                    violations.append(f"{path.relative_to(REPO_ROOT)}:{node.lineno} -> {node.module}")

    assert violations == []


def test_old_bond_support_routes_stop_defining__core_owned_types_and_errors() -> None:
    deleted_old_owner_candidates = [
        REPO_ROOT / "src" / "fuggers_py" / "_reference" / "bonds" / "errors.py",
        REPO_ROOT / "src" / "fuggers_py" / "bonds" / "_errors.py",
    ]
    for path in deleted_old_owner_candidates:
        assert path.exists() is False

    old_owner_candidates = {
        REPO_ROOT / "src" / "fuggers_py" / "_reference" / "bonds" / "types" / "compounding.py": {
            "CompoundingKind",
            "CompoundingMethod",
        },
        REPO_ROOT / "src" / "fuggers_py" / "_reference" / "bonds" / "types" / "ex_dividend.py": {"ExDividendRules"},
        REPO_ROOT / "src" / "fuggers_py" / "_reference" / "bonds" / "types" / "stub_rules.py": {
            "StubType",
            "StubPeriodRules",
        },
        REPO_ROOT / "src" / "fuggers_py" / "_reference" / "bonds" / "types" / "yield_convention.py": {
            "YieldConvention",
            "AccruedConvention",
            "RoundingKind",
            "RoundingConvention",
        },
        REPO_ROOT / "src" / "fuggers_py" / "bonds" / "types" / "compounding.py": {
            "CompoundingKind",
            "CompoundingMethod",
        },
        REPO_ROOT / "src" / "fuggers_py" / "bonds" / "types" / "ex_dividend.py": {"ExDividendRules"},
        REPO_ROOT / "src" / "fuggers_py" / "bonds" / "types" / "stub_rules.py": {"StubType", "StubPeriodRules"},
        REPO_ROOT / "src" / "fuggers_py" / "bonds" / "types" / "yield_convention.py": {
            "YieldConvention",
            "AccruedConvention",
            "RoundingKind",
            "RoundingConvention",
        },
        REPO_ROOT / "src" / "fuggers_py" / "bonds" / "_types" / "compounding.py": {
            "CompoundingKind",
            "CompoundingMethod",
        },
        REPO_ROOT / "src" / "fuggers_py" / "bonds" / "_types" / "ex_dividend.py": {"ExDividendRules"},
        REPO_ROOT / "src" / "fuggers_py" / "bonds" / "_types" / "stub_rules.py": {"StubType", "StubPeriodRules"},
        REPO_ROOT / "src" / "fuggers_py" / "bonds" / "_types" / "yield_convention.py": {
            "YieldConvention",
            "AccruedConvention",
            "RoundingKind",
            "RoundingConvention",
        },
    }

    for path, class_names in old_owner_candidates.items():
        if not path.exists():
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        defined_classes = {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, ast.ClassDef)
        }
        assert defined_classes.isdisjoint(class_names)
