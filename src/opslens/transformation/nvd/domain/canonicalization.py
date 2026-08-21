"""Canonical JSON encoding for versioned NVD CVE content."""

import hashlib
import json
import math
from typing import cast

from opslens.transformation.nvd.domain.errors import (
    InvalidNvdObservedCveVersionError,
)


def canonicalize_nvd_cve(source_cve: dict[str, object]) -> bytes:
    """Return deterministic UTF-8 JSON bytes for one NVD CVE object.

    Canonical JSON v1 uses:

    - UTF-8 encoding;
    - lexicographically sorted object keys;
    - source array order;
    - no insignificant whitespace;
    - native JSON scalar types only;
    - finite numeric values only.

    Unknown or additive NVD fields are intentionally preserved because the
    version identity covers the complete observed source CVE object.

    Args:
        source_cve: Parsed NVD CVE JSON object.

    Returns:
        Deterministic canonical JSON bytes.

    Raises:
        InvalidNvdObservedCveVersionError: If the value cannot be represented
            by the Canonical JSON v1 contract.
    """
    _validate_json_value(source_cve, path="$")

    try:
        canonical_text = json.dumps(
            source_cve,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    except (TypeError, ValueError) as exc:
        raise InvalidNvdObservedCveVersionError(
            "NVD CVE content cannot be serialized as Canonical JSON v1."
        ) from exc

    return canonical_text.encode("utf-8")


def sha256_hex(payload: bytes) -> str:
    """Return the lowercase SHA-256 digest for immutable content."""
    return hashlib.sha256(payload).hexdigest()


def _validate_json_value(value: object, *, path: str) -> None:
    """Require values representable by the Canonical JSON v1 contract."""
    if value is None or isinstance(value, (str, bool)) or type(value) is int:
        return

    if type(value) is float:
        if not math.isfinite(value):
            raise InvalidNvdObservedCveVersionError(
                f"NVD CVE JSON number at {path} must be finite."
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
                raise InvalidNvdObservedCveVersionError(
                    f"NVD CVE JSON object key at {path} must be a string."
                )

            _validate_json_value(item, path=f"{path}.{key}")

        return

    raise InvalidNvdObservedCveVersionError(
        f"NVD CVE JSON value at {path} has unsupported type {type(value).__name__!r}."
    )
