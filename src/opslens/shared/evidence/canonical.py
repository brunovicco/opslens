r"""Single canonical serialization used by every OpsLens evidence identity.

Evidence identity in OpsLens is a SHA-256 over serialized JSON. That only holds
as an identity if every module producing or comparing one serializes the same
logical payload to the same bytes. Before this module there were 34 independent
canonicalizations across ``src`` in three semantic variants: 23 with
``ensure_ascii=True`` and ``allow_nan=False``, three with ``ensure_ascii=False``,
and six that omitted ``allow_nan`` entirely.

The divergence is not cosmetic. ``ensure_ascii`` decides whether ``"Ação"``
serializes as ``"A\u00e7\u00e3o"`` or as raw UTF-8, and the two hash
differently — so the same KEV vendor name, GHSA summary or CVE description
could carry two evidence identities depending on which module hashed it.
Omitting ``allow_nan=False`` lets a ``NaN`` EPSS or CVSS score serialize as the
non-standard token ``NaN`` instead of being rejected, which converts missing
evidence into emitted evidence.

Two serializations exist here, and the distinction is deliberate:

``canonical_json``
    Identity bytes. ASCII-escaped, so the bytes are stable under any transport,
    terminal, editor or filesystem encoding that later handles them.

``model_visible_json``
    Bytes a model actually receives in a prompt. Not ASCII-escaped, because the
    model should read ``Ação``, not ``A\u00e7\u00e3o``. Prompt identity hashes
    these bytes rather than ``canonical_json`` bytes, so the digest binds what
    was actually sent instead of a re-encoding of it.

Both reject ``NaN`` and ``Infinity``, sort keys, and use the compact separators.

```text
identidade determinística != identidade única
missing evidence != benign evidence
```
"""

import hashlib
import json
from typing import Final

_SEPARATORS: Final = (",", ":")

SHA256_HEX_LENGTH: Final = 64
"""Length of a lowercase hexadecimal SHA-256 digest."""


class CanonicalSerializationError(ValueError):
    """Raised when a payload cannot carry a deterministic evidence identity."""


def canonical_json(value: object) -> bytes:
    """Serialize one payload to the canonical identity bytes.

    Args:
        value: Any JSON-serializable payload.

    Returns:
        UTF-8 bytes with sorted keys, compact separators and ASCII escaping.

    Raises:
        CanonicalSerializationError: If the payload holds a non-finite float or
            a value JSON cannot represent.
    """
    return _dumps(value, ensure_ascii=True).encode("utf-8")


def canonical_json_text(value: object) -> str:
    """Return :func:`canonical_json` as text, for callers embedding it in JSON.

    Args:
        value: Any JSON-serializable payload.

    Returns:
        The canonical identity serialization as a ``str``.

    Raises:
        CanonicalSerializationError: If the payload cannot be canonicalized.
    """
    return _dumps(value, ensure_ascii=True)


def model_visible_json(value: object) -> str:
    """Serialize one payload exactly as a model will read it in a prompt.

    Identical to :func:`canonical_json` except that non-ASCII characters stay
    literal, so the model sees real text. Prompt identities hash the UTF-8
    encoding of this string, binding the digest to the bytes actually sent.

    Args:
        value: Any JSON-serializable payload.

    Returns:
        Deterministic UTF-8 text with sorted keys and compact separators.

    Raises:
        CanonicalSerializationError: If the payload cannot be canonicalized.
    """
    return _dumps(value, ensure_ascii=False)


def sha256_hex(payload: bytes) -> str:
    """Return the lowercase hexadecimal SHA-256 digest of exact bytes.

    Args:
        payload: The exact bytes to digest.

    Returns:
        A 64-character lowercase hexadecimal digest.
    """
    return hashlib.sha256(payload).hexdigest()


def canonical_sha256(value: object) -> str:
    """Return the SHA-256 digest of one payload's canonical identity bytes.

    Args:
        value: Any JSON-serializable payload.

    Returns:
        A 64-character lowercase hexadecimal digest.

    Raises:
        CanonicalSerializationError: If the payload cannot be canonicalized.
    """
    return sha256_hex(canonical_json(value))


def evidence_id(contract_version: str, value: object) -> str:
    """Compose one ``<contract>@sha256:<digest>`` identity for a payload.

    Args:
        contract_version: The versioned contract name, such as
            ``"risk-policy:v1"``.
        value: Any JSON-serializable payload.

    Returns:
        The composed evidence identity string.

    Raises:
        CanonicalSerializationError: If the contract version is empty or the
            payload cannot be canonicalized.
    """
    if not contract_version or contract_version != contract_version.strip():
        raise CanonicalSerializationError(
            "evidence identity requires one normalized non-empty contract version"
        )
    return f"{contract_version}@sha256:{canonical_sha256(value)}"


def _dumps(value: object, *, ensure_ascii: bool) -> str:
    """Apply the one deterministic json.dumps configuration used repository-wide."""
    try:
        return json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=ensure_ascii,
            separators=_SEPARATORS,
            sort_keys=True,
        )
    except (TypeError, ValueError) as exc:
        raise CanonicalSerializationError(
            f"payload cannot carry a deterministic evidence identity: {exc}"
        ) from exc


__all__ = [
    "SHA256_HEX_LENGTH",
    "CanonicalSerializationError",
    "canonical_json",
    "canonical_json_text",
    "canonical_sha256",
    "evidence_id",
    "model_visible_json",
    "sha256_hex",
]
