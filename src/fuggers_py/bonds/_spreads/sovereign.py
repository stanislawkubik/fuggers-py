"""Sovereign issuer labels used by spread analytics."""

from __future__ import annotations

from enum import Enum

from fuggers_py._core import Tenor
from fuggers_py._core.types import Currency


class Sovereign(str, Enum):
    """Supported sovereign issuers and their standard curve metadata."""

    UNITED_STATES = "UNITED_STATES"
    UNITED_KINGDOM = "UNITED_KINGDOM"
    GERMANY = "GERMANY"
    FRANCE = "FRANCE"
    JAPAN = "JAPAN"

    def currency(self) -> Currency:
        """Return the home currency for the sovereign issuer."""
        return {
            Sovereign.UNITED_STATES: Currency.USD,
            Sovereign.UNITED_KINGDOM: Currency.GBP,
            Sovereign.GERMANY: Currency.EUR,
            Sovereign.FRANCE: Currency.EUR,
            Sovereign.JAPAN: Currency.JPY,
        }[self]

    def bond_name(self) -> str:
        """Return the market name used for the sovereign curve."""
        return {
            Sovereign.UNITED_STATES: "Treasury",
            Sovereign.UNITED_KINGDOM: "Gilt",
            Sovereign.GERMANY: "Bund",
            Sovereign.FRANCE: "OAT",
            Sovereign.JAPAN: "JGB",
        }[self]

    def standard_tenors(self) -> list[Tenor]:
        """Return the standard benchmark tenors for the sovereign curve."""
        return [Tenor.parse("2Y"), Tenor.parse("5Y"), Tenor.parse("10Y"), Tenor.parse("30Y")]

    @classmethod
    def us_treasury(cls) -> "Sovereign":
        """Return the U.S. Treasury sovereign label."""
        return cls.UNITED_STATES

    @classmethod
    def uk_gilt(cls) -> "Sovereign":
        """Return the U.K. gilt sovereign label."""
        return cls.UNITED_KINGDOM

    @classmethod
    def german_bund(cls) -> "Sovereign":
        """Return the German Bund sovereign label."""
        return cls.GERMANY


class SupranationalIssuer(str, Enum):
    """Supranational issuer labels used by spread analytics."""

    WORLD_BANK = "WORLD_BANK"
    IMF = "IMF"
    EIB = "EIB"


__all__ = ["Sovereign", "SupranationalIssuer"]
