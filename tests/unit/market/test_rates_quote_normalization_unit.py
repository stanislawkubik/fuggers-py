from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from fuggers_py.core.types import Compounding, Currency, Date, Frequency
from fuggers_py.market.curves import CurveSpec, CurveType
from fuggers_py.market.curves.errors import InvalidCurveInput
from fuggers_py.market.curves.rates.calibrators import (
    BondFitTarget,
    CalibrationMode,
    CalibrationObjective,
    CalibrationSpec,
)
from fuggers_py.market.curves.rates.calibrators._quotes import (
    QuoteValueKind,
    TargetSpaceCategory,
    model_quote_value,
    normalized_quote_rows,
    quote_value_target_space,
)
from fuggers_py.market.curves.rates.kernels import CurveKernel
from fuggers_py.market.quotes import BondQuote, SwapQuote
from fuggers_py.products.bonds import FixedBondBuilder
from fuggers_py.reference.bonds.types import CompoundingMethod, YieldCalculationRules


def _spec() -> CurveSpec:
    return CurveSpec(
        name="USD Nominal",
        reference_date=Date.parse("2026-04-09"),
        day_count="ACT_365_FIXED",
        currency=Currency.USD,
        type=CurveType.NOMINAL,
    )


def _sample_bond(instrument_id: str, *, rules: YieldCalculationRules | None = None):
    settlement = Date.parse("2026-04-09")
    return (
        FixedBondBuilder.new()
        .with_issue_date(settlement)
        .with_maturity_date(settlement.add_years(2))
        .with_coupon_rate(Decimal("0.04"))
        .with_frequency(Frequency.SEMI_ANNUAL)
        .with_currency(Currency.USD)
        .with_instrument_id(instrument_id)
        .with_rules(rules or YieldCalculationRules.us_treasury())
        .build()
    )


class _FlatZeroKernel(CurveKernel):
    def __init__(self, *, zero_rate: float, max_t: float) -> None:
        self._zero_rate = zero_rate
        self._max_t = max_t

    def max_t(self) -> float:
        return self._max_t

    def rate_at(self, tenor: float) -> float:
        return self._zero_rate


def _bootstrap_calibration_spec() -> CalibrationSpec:
    return CalibrationSpec(
        mode=CalibrationMode.BOOTSTRAP,
        objective=CalibrationObjective.EXACT_FIT,
        bond_fit_target=BondFitTarget.CLEAN_PRICE,
    )


def _global_fit_calibration_spec() -> CalibrationSpec:
    return CalibrationSpec(
        mode=CalibrationMode.GLOBAL_FIT,
        objective=CalibrationObjective.WEIGHTED_L2,
        regressor_names=("liquidity", "seasonality"),
        bond_fit_target=BondFitTarget.CLEAN_PRICE,
    )


def test_bootstrap_bond_price_quotes_normalize_to_bond_ytm() -> None:
    row, = normalized_quote_rows(
        [
            BondQuote(
                instrument=_sample_bond("UST2Y"),
                clean_price=Decimal("99.25"),
                as_of=Date.parse("2026-04-09"),
                fit_weight=2.5,
            )
        ],
        spec=_spec(),
        calibration_spec=_bootstrap_calibration_spec(),
        require_strictly_positive_tenor=True,
    )

    assert row.value_kind is QuoteValueKind.BOND_YTM
    assert row.observed_kind == "BOND_YTM"
    assert row.weight == pytest.approx(2.5)
    assert row.regressor_values == ()


def test_global_fit_bond_quote_rows_keep_price_space_regressor_values_and_fit_weight() -> None:
    row, = normalized_quote_rows(
        [
            BondQuote(
                instrument=_sample_bond("UST2Y"),
                clean_price=Decimal("99.25"),
                as_of=Date.parse("2026-04-09"),
                regressors={"liquidity": 0.25},
                fit_weight=2.5,
            )
        ],
        spec=_spec(),
        calibration_spec=_global_fit_calibration_spec(),
        require_strictly_positive_tenor=True,
    )

    assert row.value_kind is QuoteValueKind.BOND_CLEAN_PRICE
    assert row.observed_kind == "BOND_CLEAN_PRICE"
    assert row.regressor_values == pytest.approx((0.25, 0.0))
    assert row.weight == pytest.approx(2.5)


def test_bond_quote_normalization_rejects_unsupported_bond_compounding_frequency() -> None:
    unsupported_rules = replace(
        YieldCalculationRules.us_treasury(),
        compounding=CompoundingMethod.periodic(3),
    )

    with pytest.raises(InvalidCurveInput, match="unsupported bond compounding frequency 3"):
        normalized_quote_rows(
            [
                BondQuote(
                    instrument=_sample_bond("UST2Y", rules=unsupported_rules),
                    clean_price=Decimal("99.25"),
                    as_of=Date.parse("2026-04-09"),
                )
            ],
            spec=_spec(),
            calibration_spec=_bootstrap_calibration_spec(),
            require_strictly_positive_tenor=True,
        )


def test_bond_quote_normalization_keeps_supported_actual_period_compounding() -> None:
    row, = normalized_quote_rows(
        [
            BondQuote(
                instrument=_sample_bond("UKT2Y", rules=YieldCalculationRules.uk_gilt()),
                clean_price=Decimal("99.25"),
                as_of=Date.parse("2026-04-09"),
            )
        ],
        spec=_spec(),
        calibration_spec=_bootstrap_calibration_spec(),
        require_strictly_positive_tenor=True,
    )

    assert row.value_kind is QuoteValueKind.BOND_YTM
    assert row.compounding is Compounding.SEMI_ANNUAL


def test_global_fit_bond_price_normalization_uses_requested_price_target_and_never_falls_back_to_bond_ytm() -> None:
    bond = _sample_bond("UST2Y")
    quote = BondQuote(
        instrument=bond,
        clean_price=Decimal("99.25"),
        accrued_interest=Decimal("0.50"),
        as_of=Date.parse("2026-04-09"),
    )
    clean_row, = normalized_quote_rows(
        [quote],
        spec=_spec(),
        calibration_spec=CalibrationSpec(
            mode=CalibrationMode.GLOBAL_FIT,
            objective=CalibrationObjective.WEIGHTED_L2,
            bond_fit_target=BondFitTarget.CLEAN_PRICE,
        ),
        require_strictly_positive_tenor=True,
    )
    dirty_row, = normalized_quote_rows(
        [quote],
        spec=_spec(),
        calibration_spec=CalibrationSpec(
            mode=CalibrationMode.GLOBAL_FIT,
            objective=CalibrationObjective.WEIGHTED_L2,
            bond_fit_target=BondFitTarget.DIRTY_PRICE,
        ),
        require_strictly_positive_tenor=True,
    )

    assert clean_row.value_kind is QuoteValueKind.BOND_CLEAN_PRICE
    assert dirty_row.value_kind is QuoteValueKind.BOND_DIRTY_PRICE
    assert clean_row.value_kind is not QuoteValueKind.BOND_YTM
    assert dirty_row.value_kind is not QuoteValueKind.BOND_YTM
    assert clean_row.value == pytest.approx(99.25)
    assert dirty_row.value == pytest.approx(99.75)


def test_global_fit_bond_price_target_wins_over_ytm_when_both_are_present() -> None:
    bond = _sample_bond("UST2Y")
    quote = BondQuote(
        instrument=bond,
        clean_price=Decimal("99.25"),
        accrued_interest=Decimal("0.50"),
        yield_to_maturity=Decimal("0.041"),
        as_of=Date.parse("2026-04-09"),
    )
    clean_row, = normalized_quote_rows(
        [quote],
        spec=_spec(),
        calibration_spec=CalibrationSpec(
            mode=CalibrationMode.GLOBAL_FIT,
            objective=CalibrationObjective.WEIGHTED_L2,
            bond_fit_target=BondFitTarget.CLEAN_PRICE,
        ),
        require_strictly_positive_tenor=True,
    )
    dirty_row, = normalized_quote_rows(
        [quote],
        spec=_spec(),
        calibration_spec=CalibrationSpec(
            mode=CalibrationMode.GLOBAL_FIT,
            objective=CalibrationObjective.WEIGHTED_L2,
            bond_fit_target=BondFitTarget.DIRTY_PRICE,
        ),
        require_strictly_positive_tenor=True,
    )

    assert clean_row.value_kind is QuoteValueKind.BOND_CLEAN_PRICE
    assert dirty_row.value_kind is QuoteValueKind.BOND_DIRTY_PRICE
    assert clean_row.value == pytest.approx(99.25)
    assert dirty_row.value == pytest.approx(99.75)


def test_global_fit_uses_bond_ytm_when_no_price_is_present() -> None:
    row, = normalized_quote_rows(
        [
            BondQuote(
                instrument=_sample_bond("UST2Y"),
                yield_to_maturity=Decimal("0.041"),
                as_of=Date.parse("2026-04-09"),
            )
        ],
        spec=_spec(),
        calibration_spec=CalibrationSpec(
            mode=CalibrationMode.GLOBAL_FIT,
            objective=CalibrationObjective.WEIGHTED_L2,
            bond_fit_target=BondFitTarget.CLEAN_PRICE,
        ),
        require_strictly_positive_tenor=True,
    )

    assert row.value_kind is QuoteValueKind.BOND_YTM
    assert row.observed_kind == "BOND_YTM"
    assert row.value == pytest.approx(0.041)


def test_bond_quote_regressor_values_follow_calibration_spec_order_and_fill_missing_names_with_zero() -> None:
    row, = normalized_quote_rows(
        [
            BondQuote(
                instrument=_sample_bond("UST2Y"),
                clean_price=Decimal("99.25"),
                as_of=Date.parse("2026-04-09"),
                regressors={
                    "deliverable_bpv": 1.25,
                    "issue_size_bn": 42.0,
                    "repo_specialness_bp": -3.5,
                },
            )
        ],
        spec=_spec(),
        calibration_spec=CalibrationSpec(
            mode=CalibrationMode.GLOBAL_FIT,
            objective=CalibrationObjective.WEIGHTED_L2,
            regressor_names=(
                "repo_specialness_bp",
                "issue_age_years",
                "issue_size_bn",
                "deliverable_bpv",
            ),
            bond_fit_target=BondFitTarget.CLEAN_PRICE,
        ),
        require_strictly_positive_tenor=True,
    )

    assert row.regressor_values == pytest.approx((-3.5, 0.0, 42.0, 1.25))


def test_non_bond_rows_still_use_the_same_row_type_with_zero_regressor_values() -> None:
    row, = normalized_quote_rows(
        [
            SwapQuote(
                instrument_id="5Y",
                tenor="5Y",
                rate=0.04,
                currency=Currency.USD,
                as_of=Date.parse("2026-04-09"),
            )
        ],
        spec=_spec(),
        calibration_spec=_global_fit_calibration_spec(),
        require_strictly_positive_tenor=True,
    )

    assert row.value_kind is QuoteValueKind.ZERO_RATE
    assert row.regressor_values == (0.0, 0.0)


def test_quote_value_target_space_groups_normalized_quote_kinds() -> None:
    assert quote_value_target_space(QuoteValueKind.ZERO_RATE) is TargetSpaceCategory.RATE
    assert quote_value_target_space(QuoteValueKind.BOND_YTM) is TargetSpaceCategory.RATE
    assert quote_value_target_space(QuoteValueKind.DISCOUNT_FACTOR) is TargetSpaceCategory.DISCOUNT_FACTOR
    assert quote_value_target_space(QuoteValueKind.BOND_CLEAN_PRICE) is TargetSpaceCategory.BOND_PRICE
    assert quote_value_target_space(QuoteValueKind.BOND_DIRTY_PRICE) is TargetSpaceCategory.BOND_PRICE


def test_global_fit_normalization_allows_duplicate_tenors() -> None:
    rows = normalized_quote_rows(
        [
            SwapQuote(
                instrument_id="2Y-A",
                tenor="2Y",
                rate=0.03,
                currency=Currency.USD,
                as_of=Date.parse("2026-04-09"),
            ),
            SwapQuote(
                instrument_id="2Y-B",
                tenor="2Y",
                rate=0.031,
                currency=Currency.USD,
                as_of=Date.parse("2026-04-09"),
            ),
        ],
        spec=_spec(),
        calibration_spec=_global_fit_calibration_spec(),
        require_strictly_positive_tenor=True,
    )

    assert len(rows) == 2
    assert rows[0].tenor == pytest.approx(2.0)
    assert rows[1].tenor == pytest.approx(2.0)


def test_model_quote_value_prices_bond_clean_and_dirty_targets_directly_from_the_curve() -> None:
    bond = _sample_bond("UST2Y")
    accrued_interest = Decimal("0.50")
    kernel = _FlatZeroKernel(zero_rate=0.03, max_t=5.0)
    dirty_quote = BondQuote(
        instrument=bond,
        dirty_price=Decimal("100.00"),
        accrued_interest=accrued_interest,
        as_of=Date.parse("2026-04-09"),
    )
    clean_row, = normalized_quote_rows(
        [dirty_quote],
        spec=_spec(),
        calibration_spec=_global_fit_calibration_spec(),
        require_strictly_positive_tenor=True,
    )
    dirty_row, = normalized_quote_rows(
        [dirty_quote],
        spec=_spec(),
        calibration_spec=CalibrationSpec(
            mode=CalibrationMode.GLOBAL_FIT,
            objective=CalibrationObjective.WEIGHTED_L2,
            bond_fit_target=BondFitTarget.DIRTY_PRICE,
        ),
        require_strictly_positive_tenor=True,
    )

    expected_dirty = Decimal(0)
    for cash_flow in bond.cash_flows(Date.parse("2026-04-09")):
        tenor = float(Date.parse("2026-04-09").days_between(cash_flow.date)) / 365.0
        expected_dirty += cash_flow.factored_amount() * Decimal(str(kernel.discount_factor_at(tenor)))
    expected_clean = expected_dirty - accrued_interest

    assert clean_row.value_kind is QuoteValueKind.BOND_CLEAN_PRICE
    assert dirty_row.value_kind is QuoteValueKind.BOND_DIRTY_PRICE
    assert model_quote_value(kernel, clean_row, spec=_spec()) == pytest.approx(float(expected_clean), abs=1e-10)
    assert model_quote_value(kernel, dirty_row, spec=_spec()) == pytest.approx(float(expected_dirty), abs=1e-10)
