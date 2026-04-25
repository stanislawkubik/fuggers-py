from __future__ import annotations

from fuggers_py._runtime.calc_graph import CalculationGraph, NodeId, ShardConfig


def test_calc_graph_dependency_propagation_and_revision_tracking() -> None:
    graph = CalculationGraph()
    graph.add_node("quote:ABC")
    graph.add_node("price:ABC")
    graph.add_node("portfolio:core")
    graph.add_dependency("price:ABC", "quote:ABC")
    graph.add_dependency("portfolio:core", "price:ABC")

    graph.update_node_value("quote:ABC", 101.25, source="test")
    marked = graph.mark_dependents_dirty("quote:ABC")

    assert marked == (NodeId("portfolio:core"), NodeId("price:ABC"))
    assert graph.query_dirty() == (NodeId("portfolio:core"), NodeId("price:ABC"))

    graph.update_node_value("price:ABC", {"clean_price": 101.25}, source="pricing")

    assert graph.revision("quote:ABC") == 1
    assert graph.revision("price:ABC") == 1
    assert graph.get_node_value("price:ABC").source == "pricing"


def test_calc_graph_shard_assignment_is_deterministic() -> None:
    graph = CalculationGraph()
    graph.add_node("price:ABC", shard_key="ABC")
    config = ShardConfig(shard_count=8, owners=("node-a", "node-b", "node-c"))

    first = graph.shard_assignment("price:ABC", config)
    second = graph.shard_assignment("price:ABC", config)

    assert first == second
    assert first.owner in config.owners
    assert 0 <= first.shard_index < 8

