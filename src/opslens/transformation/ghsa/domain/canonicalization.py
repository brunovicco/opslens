"""Canonical JSON encoding for versioned GitHub Security Advisory content."""

import hashlib
import json
import math
from typing import cast

from opslens.transformation.ghsa.domain.errors import (
    InvalidGhsaObservedAdvisoryVersionError,
)


def canonicalize_json_value(value: object) -> bytes:
    """Return deterministic Canonical JSON v1 bytes for one JSON value."""
    _validate_json_value(value, path="$")

    try:
        canonical_text = json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    except (TypeError, ValueError) as exc:
        raise InvalidGhsaObservedAdvisoryVersionError(
            "GHSA JSON value cannot be serialized as Canonical JSON v1."
        ) from exc

    return canonical_text.encode("utf-8")


def canonicalize_json_object(value: dict[str, object]) -> bytes:
    """Return deterministic Canonical JSON v1 bytes for one JSON object."""
    return canonicalize_json_value(value)


def canonicalize_ghsa_advisory(source_advisory: dict[str, object]) -> bytes:
    """Return deterministic Canonical JSON v1 bytes for one GHSA advisory."""
    return canonicalize_json_object(source_advisory)


def sha256_hex(payload: bytes) -> str:
    """Return the lowercase SHA-256 digest for immutable content."""
    return hashlib.sha256(payload).hexdigest()


def _validate_json_value(value: object, *, path: str) -> None:
    """Require values representable by the Canonical JSON v1 contract."""
    if value is None or isinstance(value, (str, bool)) or type(value) is int:
        return

    if type(value) is float:
        if not math.isfinite(value):
            raise InvalidGhsaObservedAdvisoryVersionError(
                f"GHSA JSON number at {path} must be finite."
            )

        return

    if isinstance(value, list):
        items = cast(list[object], value)

        for index, item in enumerate(items):
            _validate_json_value(item, path=f"{path}[{index}]")

        return

    if isinstance(value, dict):
        mapping = cast(dict[object, object], value)

        for key, item in mapping.items():
            if not isinstance(key, str):
                raise InvalidGhsaObservedAdvisoryVersionError(
                    f"GHSA JSON object key at {path} must be a string."
                )

            _validate_json_value(item, path=f"{path}.{key}")

        return

    raise InvalidGhsaObservedAdvisoryVersionError(
        f"GHSA JSON value at {path} has unsupported type {type(value).__name__!r}."
    )
