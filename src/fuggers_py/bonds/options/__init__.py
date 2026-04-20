"""Bond option pricing models and short-rate tree helpers.

The public surface combines embedded-bond option payoffs, recombining tree
utilities, and short-rate model implementations used for callable and puttable
bond valuation.
"""

from __future__ import annotations

from fuggers_py._core import OptionType

from .binomial_tree import BinomialTree, ExerciseRule
from .bond_option import BondOption, ExerciseStyle
from .errors import ModelError
from .models import HullWhite, HullWhiteModel, ShortRateModel

__all__ = [
    "BinomialTree",
    "BondOption",
    "ExerciseRule",
    "ExerciseStyle",
    "HullWhite",
    "HullWhiteModel",
    "ModelError",
    "OptionType",
    "ShortRateModel",
]
