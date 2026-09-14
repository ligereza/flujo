"""Small strict primitives shared by read-only contract adapters."""

from __future__ import annotations

from collections.abc import Mapping
import copy
import hashlib
import json
from typing import Any


def required_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field}_required")
    return value.strip()


def optional_text(value: Any) -> str:
    return value.strip() if isinstance(value, str) and value.strip() else ""


def nullable_text(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def required_mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field}_invalid")
    return value


def nonnegative_int(value: Any, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{field}_invalid")
    return value


def required_bool(value: Any, field: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{field}_invalid")
    return value


def count_map(value: Any, field: str) -> dict[str, int]:
    value = required_mapping(value, field)
    return {str(key): nonnegative_int(item, f"{field}.{key}") for key, item in value.items()}


def integer(value: Any, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{field}_invalid")
    return value


def without_ok(value: Mapping[str, Any]) -> Mapping[str, Any]:
    return {key: item for key, item in value.items() if key != "ok"}


def stable_json(value: Any, *, pretty: bool = False) -> str:
    """Serialize contract values deterministically without accepting NaN."""
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        indent=2 if pretty else None,
        separators=None if pretty else (",", ":"),
        allow_nan=False,
    )


def canonicalize(value: Any) -> Any:
    """Normalize mappings and lists before hashing contract values."""
    if isinstance(value, Mapping):
        return {
            str(key): canonicalize(child)
            for key, child in sorted(value.items(), key=lambda item: str(item[0]))
        }
    if isinstance(value, list):
        return sorted((canonicalize(child) for child in value), key=stable_json)
    return copy.deepcopy(value)


def canonical_sha256_ref(value: Any) -> str:
    return "sha256:" + hashlib.sha256(
        stable_json(canonicalize(value)).encode("utf-8")
    ).hexdigest()


def compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_ref(value: Any) -> str:
    """Return the canonical JSON digest format used by contract payloads."""
    return "sha256:" + hashlib.sha256(stable_json(value).encode("utf-8")).hexdigest()


def sha256_hex(raw: bytes) -> str:
    """Return the hexadecimal SHA-256 digest for already-serialized bytes."""
    return hashlib.sha256(raw).hexdigest()
