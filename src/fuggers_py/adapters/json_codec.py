"""JSON codec adapters for trait-layer transports and storage.

The codec preserves transport-safe representations of ``Decimal``, dates,
datetimes, enums, dataclasses, tuples, sets, and non-string-key dictionaries
using tagged JSON payloads. Decoding is best-effort: importable dataclasses and
enums are restored, while unresolved types fall back to plain Python values.
"""

from __future__ import annotations

import importlib
import json
from dataclasses import fields, is_dataclass
from datetime import date as native_date
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any


_TYPE_KEY = "__fuggers_py_type__"
_CLASS_KEY = "__fuggers_py_class__"


def _qualified_name(value: type[Any]) -> str:
    """Return an importable qualified name for a Python type."""
    return f"{value.__module__}:{value.__qualname__}"


def _resolve_qualified_name(name: str) -> type[Any] | None:
    """Resolve a previously encoded qualified name to a Python type."""
    module_name, _, qualname = name.partition(":")
    if not module_name or not qualname or "<locals>" in qualname:
        return None
    try:
        current: Any = importlib.import_module(module_name)
    except Exception:
        return None
    for part in qualname.split("."):
        current = getattr(current, part, None)
        if current is None:
            return None
    return current if isinstance(current, type) else None


def _to_jsonable(value: Any) -> Any:
    """Convert a Python value into a JSON-serializable structure.

    The encoder uses tagged objects for values that JSON cannot represent
    directly or cannot round-trip without extra type information.
    """
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Decimal):
        return {_TYPE_KEY: "decimal", "value": str(value)}
    if isinstance(value, datetime):
        return {_TYPE_KEY: "datetime", "value": value.isoformat()}
    if isinstance(value, native_date):
        return {_TYPE_KEY: "date", "value": value.isoformat()}
    if isinstance(value, Enum):
        return {
            _TYPE_KEY: "enum",
            _CLASS_KEY: _qualified_name(type(value)),
            "value": _to_jsonable(value.value),
        }
    if is_dataclass(value) and not isinstance(value, type):
        return {
            _TYPE_KEY: "dataclass",
            _CLASS_KEY: _qualified_name(type(value)),
            "fields": {field.name: _to_jsonable(getattr(value, field.name)) for field in fields(value)},
        }
    if isinstance(value, tuple):
        return {_TYPE_KEY: "tuple", "items": [_to_jsonable(item) for item in value]}
    if isinstance(value, set):
        return {_TYPE_KEY: "set", "items": [_to_jsonable(item) for item in sorted(value, key=repr)]}
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, dict):
        if all(isinstance(key, str) for key in value):
            return {key: _to_jsonable(item) for key, item in value.items()}
        return {
            _TYPE_KEY: "dict",
            "items": [[_to_jsonable(key), _to_jsonable(item)] for key, item in value.items()],
        }
    raise TypeError(f"Value of type {type(value).__name__} is not JSON serializable.")


def _from_jsonable(value: Any) -> Any:
    """Restore a Python value from a tagged JSON structure.

    Tagged values are decoded back into the original Python shape whenever the
    type can be resolved. Unknown tags fall back to plain Python structures.
    """
    if isinstance(value, list):
        return [_from_jsonable(item) for item in value]
    if not isinstance(value, dict):
        return value
    type_name = value.get(_TYPE_KEY)
    if type_name is None:
        return {key: _from_jsonable(item) for key, item in value.items()}
    if type_name == "decimal":
        return Decimal(value["value"])
    if type_name == "datetime":
        return datetime.fromisoformat(value["value"])
    if type_name == "date":
        return native_date.fromisoformat(value["value"])
    if type_name == "tuple":
        return tuple(_from_jsonable(item) for item in value["items"])
    if type_name == "set":
        return set(_from_jsonable(item) for item in value["items"])
    if type_name == "dict":
        return {_from_jsonable(key): _from_jsonable(item) for key, item in value["items"]}
    if type_name == "enum":
        resolved = _resolve_qualified_name(value.get(_CLASS_KEY, ""))
        decoded_value = _from_jsonable(value["value"])
        if resolved is None:
            return decoded_value
        return resolved(decoded_value)
    if type_name == "dataclass":
        resolved = _resolve_qualified_name(value.get(_CLASS_KEY, ""))
        decoded_fields = {key: _from_jsonable(item) for key, item in value["fields"].items()}
        if resolved is None or not is_dataclass(resolved):
            return decoded_fields
        return resolved(**decoded_fields)
    return {key: _from_jsonable(item) for key, item in value.items() if key != _TYPE_KEY}


class JsonCodec:
    """Compact JSON codec with dataclass-aware encoding.

    Encoded payloads are UTF-8 bytes. The transport boundary is bytes-oriented
    even though ``decode`` also accepts text for convenience in tests and
    storage adapters.

    Parameters
    ----------
    indent:
        Optional indentation level used when encoding JSON text.
    sort_keys:
        Whether dictionary keys should be emitted in sorted order.
    """

    def __init__(self, *, indent: int | None = None, sort_keys: bool = True) -> None:
        self.indent = indent
        self.sort_keys = sort_keys

    def encode(self, value: object) -> bytes:
        """Encode a Python value into UTF-8 JSON bytes."""
        payload = json.dumps(
            _to_jsonable(value),
            ensure_ascii=False,
            indent=self.indent,
            sort_keys=self.sort_keys,
        )
        return payload.encode("utf-8")

    def decode(self, payload: bytes | str) -> object:
        """Decode JSON bytes or text back into Python values."""
        text = payload.decode("utf-8") if isinstance(payload, bytes) else payload
        return _from_jsonable(json.loads(text))


class PrettyJsonCodec(JsonCodec):
    """Indented JSON codec for debugging and human-readable fixtures.

    This variant uses a stable two-space indent so fixtures are easy to inspect
    and diff.
    """

    def __init__(self) -> None:
        super().__init__(indent=2, sort_keys=True)


__all__ = ["JsonCodec", "PrettyJsonCodec"]
