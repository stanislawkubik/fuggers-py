from __future__ import annotations

import asyncio

from fuggers_py.adapters import (
    AsyncTransport,
    CacheTransport,
    Codec,
    RemoteStorageTransport,
    Transport,
)


class JsonLikeCodec:
    def encode(self, value: object) -> bytes:
        return str(value).encode("utf-8")

    def decode(self, payload: bytes) -> object:
        return payload.decode("utf-8")


class EchoTransport:
    codec = JsonLikeCodec()

    def send(self, topic: str, payload: bytes) -> None:
        self.last_sent = (topic, payload)

    def request(self, topic: str, payload: bytes) -> bytes:
        return b"%s:%s" % (topic.encode("utf-8"), payload)


class AsyncEchoTransport:
    codec = JsonLikeCodec()

    async def send(self, topic: str, payload: bytes) -> None:
        self.last_sent = (topic, payload)

    async def request(self, topic: str, payload: bytes) -> bytes:
        return payload


class MemoryCacheTransport:
    def __init__(self) -> None:
        self.items: dict[str, bytes] = {}

    def get(self, key: str) -> bytes | None:
        return self.items.get(key)

    def put(self, key: str, payload: bytes, *, ttl_seconds: int | None = None) -> None:
        self.items[key] = payload

    def delete(self, key: str) -> None:
        self.items.pop(key, None)


class MemoryRemoteStorageTransport:
    def __init__(self) -> None:
        self.items: dict[tuple[str, str], bytes] = {}

    def fetch(self, namespace: str, key: str) -> bytes | None:
        return self.items.get((namespace, key))

    def store(self, namespace: str, key: str, payload: bytes) -> None:
        self.items[(namespace, key)] = payload


def test_transport_protocols_support_noop_and_mock_implementations() -> None:
    codec = JsonLikeCodec()
    transport = EchoTransport()
    async_transport = AsyncEchoTransport()
    cache = MemoryCacheTransport()
    remote = MemoryRemoteStorageTransport()

    assert isinstance(codec, Codec)
    assert isinstance(transport, Transport)
    assert isinstance(async_transport, AsyncTransport)
    assert isinstance(cache, CacheTransport)
    assert isinstance(remote, RemoteStorageTransport)
    assert codec.decode(codec.encode({"a": 1})) == "{'a': 1}"
    transport.send("quotes", b"payload")
    assert transport.request("quotes", b"payload") == b"quotes:payload"
    asyncio.run(async_transport.send("quotes", b"payload"))
    assert asyncio.run(async_transport.request("quotes", b"payload")) == b"payload"
    cache.put("quote", b"1")
    remote.store("curves", "usd", b"curve")
    assert cache.get("quote") == b"1"
    assert remote.fetch("curves", "usd") == b"curve"

