from __future__ import annotations

from fuggers_py._calc import (
    InMemoryLeaderElection,
    InMemoryPartitionRegistry,
    InMemoryServiceRegistry,
    PartitionAssignment,
    ServiceRegistration,
)


def test_in_memory_service_registry_is_deterministic() -> None:
    registry = InMemoryServiceRegistry()
    registration_a = ServiceRegistration(service_name="pricing", node_id="node-b", endpoint="tcp://b")
    registration_b = ServiceRegistration(service_name="pricing", node_id="node-a", endpoint="tcp://a")

    registry.register(registration_a)
    registry.register(registration_b)

    assert registry.get_service("pricing", "node-a") == registration_b
    assert registry.list_services("pricing") == (registration_b, registration_a)

    registry.deregister("pricing", "node-b")
    assert registry.list_services("pricing") == (registration_b,)


def test_in_memory_partition_registry_tracks_assignments_and_versions() -> None:
    registry = InMemoryPartitionRegistry()

    first = registry.assign("usd-0", "node-a")
    second = registry.assign("usd-0", "node-b")

    assert first == PartitionAssignment(partition_id="usd-0", owner_id="node-a", version=1)
    assert second == PartitionAssignment(partition_id="usd-0", owner_id="node-b", version=2)
    assert registry.owner("usd-0") == "node-b"
    assert registry.list_assignments() == (second,)

    registry.release("usd-0")
    assert registry.owner("usd-0") is None


def test_in_memory_leader_election_is_deterministic() -> None:
    election = InMemoryLeaderElection()

    assert election.acquire("node-a") is True
    assert election.leader() == "node-a"
    assert election.acquire("node-b") is False
    assert election.release("node-b") is False
    assert election.release("node-a") is True
    assert election.leader() is None

