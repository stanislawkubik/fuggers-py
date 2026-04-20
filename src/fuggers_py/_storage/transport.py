"""Transport and codec contracts for remote trait adapters.

The transport boundary is always raw bytes. A codec can be attached to turn
Python objects into payload bytes and back again, but the transport protocol
itself stays agnostic about the serialized representation.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class Codec(Protocol):
    """Protocol for byte-oriented codecs.

    Implementations convert Python values into transport-safe ``bytes`` payloads
    and reconstruct values from those payloads on decode.
    """

    def encode(self, value: object) -> bytes:
        ...

    def decode(self, payload: bytes) -> object:
        ...


@runtime_checkable
class Transport(Protocol):
    """Protocol for synchronous byte-oriented request/response transports.

    The transport may carry an optional codec for convenience, but ``send`` and
    ``request`` always operate on raw payload bytes.
    """

    codec: Codec | None

    def send(self, topic: str, payload: bytes) -> None:
        ...

    def request(self, topic: str, payload: bytes) -> bytes:
        ...


@runtime_checkable
class AsyncTransport(Protocol):
    """Protocol for asynchronous byte-oriented request/response transports.

    This mirrors :class:`Transport` but allows the implementation to perform
    I/O asynchronously.
    """

    codec: Codec | None

    async def send(self, topic: str, payload: bytes) -> None:
        ...

    async def request(self, topic: str, payload: bytes) -> bytes:
        ...


@runtime_checkable
class RemoteStorageTransport(Protocol):
    """Protocol for remote key/value storage transport.

    Keys are addressed by namespace and key string, and payloads are stored as
    raw bytes.
    """

    def fetch(self, namespace: str, key: str) -> bytes | None:
        ...

    def store(self, namespace: str, key: str, payload: bytes) -> None:
        ...


@runtime_checkable
class CacheTransport(Protocol):
    """Protocol for cache transport with optional TTL semantics.

    Payloads are raw bytes, and callers may supply a time-to-live in seconds
    when the backend supports expiring entries.
    """

    def get(self, key: str) -> bytes | None:
        ...

    def put(self, key: str, payload: bytes, *, ttl_seconds: int | None = None) -> None:
        ...

    def delete(self, key: str) -> None:
        ...


__all__ = [
    "AsyncTransport",
    "CacheTransport",
    "Codec",
    "RemoteStorageTransport",
    "Transport",
]
