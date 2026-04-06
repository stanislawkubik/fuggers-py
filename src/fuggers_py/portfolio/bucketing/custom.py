"""Custom-field bucketing.

These helpers group holdings by classification metadata or user-defined custom
fields, returning portfolio-friendly bucket maps for downstream aggregation.
"""

from __future__ import annotations

from enum import Enum

from ..portfolio import Portfolio
from ..results import ClassifierDistribution, CustomDistribution
from ..types import Position


def bucket_by_custom_field(portfolio: Portfolio, field_name: str) -> CustomDistribution:
    """Bucket holdings by a custom field name."""

    buckets: dict[str, list[Position]] = {}
    for position in portfolio.positions:
        if not isinstance(position, Position):
            continue
        value = position.custom_fields.get(field_name)
        if value is None and position.classification is not None:
            value = position.classification.custom_fields.get(field_name)
        buckets.setdefault(value or "UNKNOWN", []).append(position)
    return CustomDistribution(field_name=field_name, entries=buckets)


def _normalize_bucket_key(value: object) -> str:
    if value is None:
        return "UNKNOWN"
    if isinstance(value, Enum):
        return str(value.value)
    return str(value)


def _classifier_value(position: Position, classifier_name: str) -> object:
    classification = position.classification
    sector_info = position.sector_info
    rating_info = position.rating_info
    seniority_info = position.seniority_info

    if classifier_name == "rating":
        if rating_info is not None:
            return rating_info.rating
        if classification is not None:
            return classification.rating
        return None
    if classifier_name == "sector":
        if sector_info is not None:
            return sector_info.sector
        if classification is not None:
            return classification.sector
        return None
    if classifier_name == "seniority":
        if seniority_info is not None:
            return seniority_info.seniority
        if classification is not None:
            return classification.seniority
        return None
    if classifier_name == "country":
        if sector_info is not None and sector_info.country is not None:
            return sector_info.country
        if classification is not None:
            return classification.country
        return None
    if classifier_name == "region":
        if sector_info is not None and sector_info.region is not None:
            return sector_info.region
        if classification is not None:
            return classification.region
        return None
    if classifier_name == "issuer":
        if sector_info is not None and sector_info.issuer is not None:
            return sector_info.issuer
        if classification is not None:
            return classification.issuer
        return None
    if classifier_name == "currency":
        if classification is not None and classification.currency is not None:
            return classification.currency
        return position.currency
    if classifier_name in position.custom_fields:
        return position.custom_fields[classifier_name]
    if classification is not None and classifier_name in classification.custom_fields:
        return classification.custom_fields[classifier_name]
    if classification is not None:
        return getattr(classification, classifier_name, None)
    return None


def bucket_by_classifier(portfolio: Portfolio, classifier_name: str) -> ClassifierDistribution:
    """Bucket holdings by a named classifier or custom field."""

    buckets: dict[str, list[Position]] = {}
    for position in portfolio.positions:
        if not isinstance(position, Position):
            continue
        key = _normalize_bucket_key(_classifier_value(position, classifier_name))
        buckets.setdefault(key, []).append(position)
    return ClassifierDistribution(classifier_name=classifier_name, entries=buckets)


def _bucket_by_attr(portfolio: Portfolio, attr: str) -> dict[str, list[Position]]:
    buckets: dict[str, list[Position]] = {}
    for position in portfolio.positions:
        if not isinstance(position, Position):
            continue
        classification = position.classification
        value = getattr(classification, attr) if classification is not None else None
        buckets.setdefault(value or "UNKNOWN", []).append(position)
    return buckets


def bucket_by_country(portfolio: Portfolio) -> dict[str, list[Position]]:
    """Bucket holdings by country."""

    return _bucket_by_attr(portfolio, "country")


def bucket_by_currency(portfolio: Portfolio) -> dict[str, list[Position]]:
    """Bucket holdings by currency."""

    return _bucket_by_attr(portfolio, "currency")


def bucket_by_issuer(portfolio: Portfolio) -> dict[str, list[Position]]:
    """Bucket holdings by issuer."""

    return _bucket_by_attr(portfolio, "issuer")


def bucket_by_region(portfolio: Portfolio) -> dict[str, list[Position]]:
    """Bucket holdings by region."""

    return _bucket_by_attr(portfolio, "region")


__all__ = [
    "bucket_by_classifier",
    "bucket_by_country",
    "bucket_by_currency",
    "bucket_by_custom_field",
    "bucket_by_issuer",
    "bucket_by_region",
]
