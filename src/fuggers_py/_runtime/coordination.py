"""Coordination protocols and deterministic in-memory helpers.

The engine uses these records to describe service registration, partition
ownership, and leader-election state without binding the public surface to a
particular transport or storage backend. The in-memory implementations are
intended for tests and research flows where deterministic local state is
preferable to external coordination.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


def _normalize_text(value: str, *, field_name: str) -> str:
    text = value.strip()
    if not text:
        raise ValueError(f"{field_name} must be non-empty.")
    return text


@dataclass(frozen=True, slots=True)
class ServiceRegistration:
    """Registration record for a service instance.

    Parameters
    ----------
    service_name:
        Logical service name that owns the registration.
    node_id:
        Stable node identifier within that service.
    endpoint:
        Network or transport endpoint for the instance.
    metadata:
        Optional sorted key/value metadata carried with the registration.
    """

    service_name: str
    node_id: str
    endpoint: str
    metadata: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "service_name", _normalize_text(self.service_name, field_name="service_name"))
        object.__setattr__(self, "node_id", _normalize_text(self.node_id, field_name="node_id"))
        object.__setattr__(self, "endpoint", _normalize_text(self.endpoint, field_name="endpoint"))
        object.__setattr__(
            self,
            "metadata",
            tuple((key.strip(), value.strip()) for key, value in sorted(self.metadata)),
        )


@dataclass(frozen=True, slots=True)
class PartitionAssignment:
    """Current owner and version of a partition."""

    partition_id: str
    owner_id: str | None = None
    version: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "partition_id", _normalize_text(self.partition_id, field_name="partition_id"))
        if self.owner_id is not None:
            object.__setattr__(self, "owner_id", _normalize_text(self.owner_id, field_name="owner_id"))
        if self.version < 0:
            raise ValueError("version must be non-negative.")


@runtime_checkable
class ServiceRegistry(Protocol):
    """Protocol for service registration backends."""

    def register(self, registration: ServiceRegistration) -> ServiceRegistration:
        ...

    def deregister(self, service_name: str, node_id: str) -> None:
        ...

    def get_service(self, service_name: str, node_id: str) -> ServiceRegistration | None:
        ...

    def list_services(self, service_name: str | None = None) -> tuple[ServiceRegistration, ...]:
        ...


@runtime_checkable
class PartitionRegistry(Protocol):
    """Protocol for partition ownership backends."""

    def assign(self, partition_id: str, owner_id: str) -> PartitionAssignment:
        ...

    def release(self, partition_id: str) -> None:
        ...

    def owner(self, partition_id: str) -> str | None:
        ...

    def list_assignments(self) -> tuple[PartitionAssignment, ...]:
        ...


@runtime_checkable
class LeaderElection(Protocol):
    """Protocol for single-leader coordination backends."""

    def acquire(self, candidate_id: str) -> bool:
        ...

    def release(self, candidate_id: str) -> bool:
        ...

    def leader(self) -> str | None:
        ...


@dataclass(slots=True)
class InMemoryServiceRegistry:
    """Deterministic in-memory service registry for tests and research flows."""

    _registrations: dict[tuple[str, str], ServiceRegistration] = field(default_factory=dict)

    def register(self, registration: ServiceRegistration) -> ServiceRegistration:
        """Store a service registration and return it."""
        self._registrations[(registration.service_name, registration.node_id)] = registration
        return registration

    def deregister(self, service_name: str, node_id: str) -> None:
        """Remove a service registration if it exists."""
        self._registrations.pop((_normalize_text(service_name, field_name="service_name"), _normalize_text(node_id, field_name="node_id")), None)

    def get_service(self, service_name: str, node_id: str) -> ServiceRegistration | None:
        """Return a registered service instance for the given key."""
        return self._registrations.get(
            (_normalize_text(service_name, field_name="service_name"), _normalize_text(node_id, field_name="node_id"))
        )

    def list_services(self, service_name: str | None = None) -> tuple[ServiceRegistration, ...]:
        """Return registered services, optionally filtered by service name."""
        registrations = tuple(sorted(self._registrations.values(), key=lambda item: (item.service_name, item.node_id)))
        if service_name is None:
            return registrations
        normalized = _normalize_text(service_name, field_name="service_name")
        return tuple(item for item in registrations if item.service_name == normalized)


@dataclass(slots=True)
class InMemoryPartitionRegistry:
    """Deterministic in-memory partition registry for tests and research flows."""

    _assignments: dict[str, PartitionAssignment] = field(default_factory=dict)

    def assign(self, partition_id: str, owner_id: str) -> PartitionAssignment:
        """Assign a partition to an owner and bump the version."""
        normalized_partition = _normalize_text(partition_id, field_name="partition_id")
        normalized_owner = _normalize_text(owner_id, field_name="owner_id")
        current = self._assignments.get(normalized_partition)
        next_version = 1 if current is None else current.version + 1
        assignment = PartitionAssignment(partition_id=normalized_partition, owner_id=normalized_owner, version=next_version)
        self._assignments[normalized_partition] = assignment
        return assignment

    def release(self, partition_id: str) -> None:
        """Release a partition if it is currently assigned."""
        self._assignments.pop(_normalize_text(partition_id, field_name="partition_id"), None)

    def owner(self, partition_id: str) -> str | None:
        """Return the current owner for a partition."""
        assignment = self._assignments.get(_normalize_text(partition_id, field_name="partition_id"))
        return None if assignment is None else assignment.owner_id

    def list_assignments(self) -> tuple[PartitionAssignment, ...]:
        """Return all assignments in partition order."""
        return tuple(sorted(self._assignments.values(), key=lambda item: item.partition_id))


@dataclass(slots=True)
class InMemoryLeaderElection:
    """Single-leader in-memory election helper for deterministic tests."""

    _leader: str | None = None

    def acquire(self, candidate_id: str) -> bool:
        """Acquire leadership for the candidate if no leader is set."""
        normalized = _normalize_text(candidate_id, field_name="candidate_id")
        if self._leader is None:
            self._leader = normalized
            return True
        return self._leader == normalized

    def release(self, candidate_id: str) -> bool:
        """Release leadership if the candidate currently owns it."""
        normalized = _normalize_text(candidate_id, field_name="candidate_id")
        if self._leader != normalized:
            return False
        self._leader = None
        return True

    def leader(self) -> str | None:
        """Return the current leader identifier, if any."""
        return self._leader


__all__ = [
    "InMemoryLeaderElection",
    "InMemoryPartitionRegistry",
    "InMemoryServiceRegistry",
    "LeaderElection",
    "PartitionAssignment",
    "PartitionRegistry",
    "ServiceRegistration",
    "ServiceRegistry",
]
