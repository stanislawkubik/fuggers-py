"""Serializable configuration records for engine orchestration.

These records capture engine identity, default cadence, node registration, and
the small set of toggles that control whether stale data may still be used.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from fuggers_py.core.types import Date


def _normalize_text(value: str, *, field_name: str) -> str:
    text = value.strip()
    if not text:
        raise ValueError(f"{field_name} must be non-empty.")
    return text


class UpdateFrequency(str, Enum):
    """Cadence labels used to describe how often an engine node updates."""

    REAL_TIME = "REAL_TIME"
    INTRADAY = "INTRADAY"
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    ON_DEMAND = "ON_DEMAND"


@dataclass(frozen=True, slots=True)
class NodeConfig:
    """Configuration for a single engine node.

    Parameters
    ----------
    node_id:
        Stable identifier for the node.
    service_name:
        Logical service that owns the node.
    update_frequency:
        Expected cadence for updates.
    enabled:
        Whether the node participates in orchestration.
    transport:
        Optional transport name used by external coordination layers.
    partitions:
        Optional partition labels associated with the node.
    tags:
        Optional free-form tags for discovery and filtering.

    Notes
    -----
    Text fields are stripped and validated as non-empty. `partitions` and
    `tags` are frozen into tuples so the record remains hashable and stable.
    """

    node_id: str
    service_name: str
    update_frequency: UpdateFrequency = UpdateFrequency.ON_DEMAND
    enabled: bool = True
    transport: str | None = None
    partitions: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Normalize text fields and freeze partition/tag containers."""
        object.__setattr__(self, "node_id", _normalize_text(self.node_id, field_name="node_id"))
        object.__setattr__(self, "service_name", _normalize_text(self.service_name, field_name="service_name"))
        if self.transport is not None:
            object.__setattr__(self, "transport", _normalize_text(self.transport, field_name="transport"))
        object.__setattr__(self, "partitions", tuple(_normalize_text(item, field_name="partition") for item in self.partitions))
        object.__setattr__(self, "tags", tuple(_normalize_text(item, field_name="tag") for item in self.tags))


@dataclass(frozen=True, slots=True)
class EngineConfig:
    """Top-level engine configuration.

    Parameters
    ----------
    engine_name:
        Stable engine identifier.
    as_of:
        Optional valuation date used as the default settlement date.
    update_frequency:
        Cadence for the engine as a whole.
    nodes:
        Registered node configurations.
    allow_stale_data:
        Whether stale market data may still be consumed.
    timeout_seconds:
        Default orchestration timeout.
    default_pricing_config_id:
        Optional pricing-configuration identifier.

    Notes
    -----
    `engine_name` is normalized as a non-empty string. `nodes` are frozen into
    a tuple, `timeout_seconds` must be positive, and `as_of` is reused as the
    default settlement date when the builder does not supply one explicitly.
    """

    engine_name: str
    as_of: Date | None = None
    update_frequency: UpdateFrequency = UpdateFrequency.ON_DEMAND
    nodes: tuple[NodeConfig, ...] = ()
    allow_stale_data: bool = True
    timeout_seconds: int = 30
    default_pricing_config_id: str | None = None

    def __post_init__(self) -> None:
        """Normalize identifiers and validate the configuration."""
        object.__setattr__(self, "engine_name", _normalize_text(self.engine_name, field_name="engine_name"))
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive.")
        if self.default_pricing_config_id is not None:
            object.__setattr__(
                self,
                "default_pricing_config_id",
                _normalize_text(self.default_pricing_config_id, field_name="default_pricing_config_id"),
            )
        object.__setattr__(self, "nodes", tuple(self.nodes))


__all__ = ["EngineConfig", "NodeConfig", "UpdateFrequency"]
