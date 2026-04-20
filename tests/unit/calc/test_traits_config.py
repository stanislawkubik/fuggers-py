from __future__ import annotations

from fuggers_py._core import Date
from fuggers_py._calc import EngineConfig, NodeConfig, UpdateFrequency


def test_config_dataclasses_preserve_repr_and_value_equality() -> None:
    node = NodeConfig(
        node_id="pricing-node-1",
        service_name="pricing-router",
        update_frequency=UpdateFrequency.REAL_TIME,
        transport="ipc",
        partitions=("usd", "eur"),
        tags=("primary",),
    )
    engine = EngineConfig(
        engine_name="fixed-income-engine",
        as_of=Date.from_ymd(2026, 3, 13),
        update_frequency=UpdateFrequency.INTRADAY,
        nodes=(node,),
        allow_stale_data=False,
        timeout_seconds=15,
        default_pricing_config_id="base",
    )

    same_engine = EngineConfig(
        engine_name="fixed-income-engine",
        as_of=Date.from_ymd(2026, 3, 13),
        update_frequency=UpdateFrequency.INTRADAY,
        nodes=(node,),
        allow_stale_data=False,
        timeout_seconds=15,
        default_pricing_config_id="base",
    )

    assert engine == same_engine
    assert "EngineConfig" in repr(engine)
    assert "NodeConfig" in repr(node)

