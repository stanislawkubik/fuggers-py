"""Deterministic calculation-graph helpers for reactive orchestration.

The graph stores node values, dependency edges, dirty-node state, and shard
assignments for the reactive engine. Dirty propagation is explicit: when a
source node changes, dependent nodes are marked dirty and later re-evaluated by
the reactive runtime. The graph is intentionally small and in-memory so the
runtime layer can reason about dependency changes without external storage.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum


def _normalize(value: object) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError("Node identifier must be non-empty.")
    return text


@dataclass(frozen=True, order=True, slots=True)
class NodeId:
    """Normalized node identifier used throughout the engine graph.

    Node identifiers are stripped, validated, and stored as canonical strings
    so graph lookups remain stable across the reactive runtime.
    """

    value: str

    def __post_init__(self) -> None:
        """Normalize the identifier and reject empty values."""
        object.__setattr__(self, "value", _normalize(self.value))

    @classmethod
    def parse(cls, value: object) -> "NodeId":
        """Parse a node identifier from an arbitrary value."""
        return cls(_normalize(value))

    @classmethod
    def from_string(cls, value: str) -> "NodeId":
        """Parse a node identifier from text."""
        return cls.parse(value)

    def as_str(self) -> str:
        """Return the normalized node identifier as a string."""
        return self.value

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.value


@dataclass(frozen=True, slots=True)
class NodeValue:
    """Cached node payload stored in the calculation graph.

    The record stores the cached value together with its revision, update
    timestamp, source label, and stale flag.
    """

    value: object | None = None
    revision: int = 0
    updated_at: datetime | None = None
    source: str | None = None
    stale: bool = False


class ShardStrategy(str, Enum):
    """Strategy used to map nodes to shard owners."""

    MODULO = "MODULO"
    CONSISTENT_HASH = "CONSISTENT_HASH"


@dataclass(frozen=True, slots=True)
class ShardAssignment:
    """Resolved shard index and owner for a node."""

    node_id: NodeId
    shard_key: str
    shard_index: int
    owner: str | None = None


@dataclass(frozen=True, slots=True)
class ShardConfig:
    """Shard layout used by the calculation graph.

    Parameters
    ----------
    shard_count:
        Number of shards to map nodes across.
    owners:
        Optional ordered list of shard owners.
    strategy:
        Owner selection strategy when owners are present.
    virtual_nodes:
        Number of virtual nodes per owner for consistent hashing.
    """

    shard_count: int = 1
    owners: tuple[str, ...] = ()
    strategy: ShardStrategy = ShardStrategy.CONSISTENT_HASH
    virtual_nodes: int = 16

    def __post_init__(self) -> None:
        """Validate the shard layout and normalize owner names."""
        if self.shard_count <= 0:
            raise ValueError("shard_count must be positive.")
        if self.virtual_nodes <= 0:
            raise ValueError("virtual_nodes must be positive.")
        object.__setattr__(self, "owners", tuple(item.strip() for item in self.owners if item.strip()))


@dataclass(slots=True)
class _GraphNode:
    node_id: NodeId
    dependencies: set[NodeId] = field(default_factory=set)
    dependents: set[NodeId] = field(default_factory=set)
    cached_value: NodeValue | None = None
    dirty: bool = False
    shard_key: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)


def _hash_to_int(value: str) -> int:
    return int(hashlib.sha256(value.encode("utf-8")).hexdigest(), 16)


@dataclass(slots=True)
class CalculationGraph:
    """Mutable dependency graph with cached node values and dirty tracking.

    Nodes can be added lazily, marked dirty, updated with new cached values, and
    assigned to shards for distributed orchestration.
    """

    _nodes: dict[NodeId, _GraphNode] = field(default_factory=dict)

    def add_node(
        self,
        node_id: NodeId | str,
        *,
        value: object | None = None,
        shard_key: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> NodeId:
        """Register a node and optionally seed its cached value.

        Existing nodes are updated in place. This keeps node identity stable
        while allowing metadata, shard hints, and initial cached values to be
        attached lazily.
        """
        resolved = node_id if isinstance(node_id, NodeId) else NodeId.parse(node_id)
        node = self._nodes.get(resolved)
        if node is None:
            cached_value = None
            if value is not None:
                cached_value = NodeValue(value=value, revision=1, updated_at=datetime.now(UTC))
            self._nodes[resolved] = _GraphNode(
                node_id=resolved,
                cached_value=cached_value,
                shard_key=shard_key,
                metadata=dict(metadata or {}),
            )
            return resolved
        if shard_key is not None:
            node.shard_key = shard_key
        if metadata is not None:
            node.metadata.update(metadata)
        if value is not None and node.cached_value is None:
            node.cached_value = NodeValue(value=value, revision=1, updated_at=datetime.now(UTC))
        return resolved

    def has_node(self, node_id: NodeId | str) -> bool:
        """Return ``True`` when the graph already contains the node."""
        resolved = node_id if isinstance(node_id, NodeId) else NodeId.parse(node_id)
        return resolved in self._nodes

    def add_dependency(self, node_id: NodeId | str, depends_on: NodeId | str) -> None:
        """Add a dependency edge from ``node_id`` to ``depends_on``."""
        child = self.add_node(node_id)
        parent = self.add_node(depends_on)
        self._nodes[child].dependencies.add(parent)
        self._nodes[parent].dependents.add(child)

    def dependencies(self, node_id: NodeId | str) -> tuple[NodeId, ...]:
        """Return the direct dependencies for a node."""
        resolved = self._require_node(node_id)
        return tuple(sorted(self._nodes[resolved].dependencies))

    def dependents(self, node_id: NodeId | str) -> tuple[NodeId, ...]:
        """Return the direct dependents for a node."""
        resolved = self._require_node(node_id)
        return tuple(sorted(self._nodes[resolved].dependents))

    def mark_dirty(
        self,
        node_id: NodeId | str,
        *,
        propagate: bool = True,
        include_self: bool = True,
    ) -> tuple[NodeId, ...]:
        """Mark a node and, optionally, its dependents as dirty.

        Parameters
        ----------
        node_id:
            Root node to mark.
        propagate:
            When ``True``, recursively mark downstream dependents.
        include_self:
            When ``False``, only downstream dependents are marked dirty.
        """
        resolved = self.add_node(node_id)
        marked: set[NodeId] = set()
        stack = [resolved]
        while stack:
            current = stack.pop()
            if current in marked and (current != resolved or include_self):
                continue
            if current != resolved or include_self:
                self._nodes[current].dirty = True
                marked.add(current)
            if propagate:
                stack.extend(sorted(self._nodes[current].dependents, reverse=True))
        return tuple(sorted(marked))

    def mark_dependents_dirty(self, node_id: NodeId | str) -> tuple[NodeId, ...]:
        """Mark the downstream dependents of a node as dirty."""
        return self.mark_dirty(node_id, include_self=False)

    def clear_dirty(self, node_id: NodeId | str) -> None:
        """Clear the dirty flag for a node."""
        resolved = self._require_node(node_id)
        self._nodes[resolved].dirty = False

    def query_dirty(self) -> tuple[NodeId, ...]:
        """Return all dirty nodes in deterministic order."""
        return tuple(sorted(node_id for node_id, node in self._nodes.items() if node.dirty))

    def update_node_value(
        self,
        node_id: NodeId | str,
        value: object,
        *,
        revision: int | None = None,
        source: str | None = None,
        mark_clean: bool = True,
    ) -> NodeValue:
        """Store a new cached value and optionally clear the dirty flag.

        The revision is incremented automatically unless an explicit revision is
        supplied. Values are timestamped in UTC at the time of the update.
        """
        resolved = self.add_node(node_id)
        current = self._nodes[resolved].cached_value
        next_revision = 1 if current is None else current.revision + 1
        if revision is not None:
            next_revision = revision
        cached = NodeValue(
            value=value,
            revision=next_revision,
            updated_at=datetime.now(UTC),
            source=source,
            stale=False,
        )
        self._nodes[resolved].cached_value = cached
        if mark_clean:
            self._nodes[resolved].dirty = False
        return cached

    def get_node_value(self, node_id: NodeId | str) -> NodeValue | None:
        """Return the cached value for a node, if one exists."""
        resolved = self._require_node(node_id)
        return self._nodes[resolved].cached_value

    def revision(self, node_id: NodeId | str) -> int:
        """Return the current cached revision for a node."""
        cached = self.get_node_value(node_id)
        return 0 if cached is None else cached.revision

    def node_metadata(self, node_id: NodeId | str) -> dict[str, object]:
        """Return a copy of the node metadata."""
        resolved = self._require_node(node_id)
        return dict(self._nodes[resolved].metadata)

    def shard_assignment(self, node_id: NodeId | str, config: ShardConfig) -> ShardAssignment:
        """Resolve the shard index and owner for a node.

        The shard index is derived from the node's explicit shard key when
        present, otherwise from the node identifier. Owners are selected either
        by modulo or by consistent hashing depending on ``config.strategy``.
        """
        resolved = self.add_node(node_id)
        node = self._nodes[resolved]
        shard_key = node.shard_key or resolved.as_str()
        shard_index = _hash_to_int(shard_key) % config.shard_count
        owner = None
        if config.owners:
            if config.strategy is ShardStrategy.MODULO:
                owner = config.owners[shard_index % len(config.owners)]
            else:
                owner = self._consistent_hash_owner(shard_key, config)
        return ShardAssignment(
            node_id=resolved,
            shard_key=shard_key,
            shard_index=shard_index,
            owner=owner,
        )

    def _consistent_hash_owner(self, key: str, config: ShardConfig) -> str:
        """Return the consistent-hash owner for a shard key."""
        ring: list[tuple[int, str]] = []
        for owner in config.owners:
            for vnode in range(config.virtual_nodes):
                ring.append((_hash_to_int(f"{owner}:{vnode}"), owner))
        ring.sort(key=lambda item: item[0])
        target = _hash_to_int(key)
        for point, owner in ring:
            if target <= point:
                return owner
        return ring[0][1]

    def _require_node(self, node_id: NodeId | str) -> NodeId:
        """Resolve a node identifier and fail if the node is not registered."""
        resolved = node_id if isinstance(node_id, NodeId) else NodeId.parse(node_id)
        if resolved not in self._nodes:
            raise KeyError(f"Node {resolved.as_str()!r} is not registered.")
        return resolved


__all__ = [
    "CalculationGraph",
    "NodeId",
    "NodeValue",
    "ShardAssignment",
    "ShardConfig",
    "ShardStrategy",
]
