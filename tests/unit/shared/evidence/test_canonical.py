"""Property and architecture tests for the one canonical evidence serialization."""

import ast
import json
import math
import pathlib

import pytest

from opslens.shared.evidence import (
    SHA256_HEX_LENGTH,
    CanonicalSerializationError,
    canonical_json,
    canonical_json_text,
    canonical_sha256,
    evidence_id,
    model_visible_json,
    sha256_hex,
)

_SRC_ROOT = pathlib.Path(__file__).resolve().parents[3] / "src" / "opslens"
_CANONICAL_MODULE = _SRC_ROOT / "shared" / "evidence" / "canonical.py"

_NON_ASCII_PAYLOAD = {
    "vendor_project": "Ação Segurança",
    "vulnerability_name": "Execução remota não autenticada",
    "cve": "CVE-2026-12345",
    "description": "Uma falha — crítica — no componente",
}


def test_key_order_does_not_change_identity() -> None:
    """Two orderings of the same logical payload share one identity."""
    first = {"b": 1, "a": 2, "c": {"z": 1, "y": 2}}
    second = {"c": {"y": 2, "z": 1}, "a": 2, "b": 1}

    assert canonical_json(first) == canonical_json(second)
    assert canonical_sha256(first) == canonical_sha256(second)


def test_identity_bytes_are_ascii_escaped() -> None:
    """Identity bytes never depend on a downstream UTF-8 handling decision."""
    encoded = canonical_json(_NON_ASCII_PAYLOAD)

    assert all(byte < 128 for byte in encoded)
    assert b"A\\u00e7\\u00e3o" in encoded


def test_identity_round_trips_to_the_same_logical_payload() -> None:
    """ASCII escaping is an encoding choice, never a content change."""
    assert json.loads(canonical_json(_NON_ASCII_PAYLOAD)) == _NON_ASCII_PAYLOAD
    assert json.loads(model_visible_json(_NON_ASCII_PAYLOAD)) == _NON_ASCII_PAYLOAD


def test_model_visible_serialization_keeps_text_readable() -> None:
    """A model reads real text, not escape sequences."""
    visible = model_visible_json(_NON_ASCII_PAYLOAD)

    assert "Ação Segurança" in visible
    assert "\\u00e7" not in visible


def test_model_visible_and_identity_serializations_differ_only_in_encoding() -> None:
    """The two serializations stay one payload under two encodings."""
    assert json.loads(model_visible_json(_NON_ASCII_PAYLOAD)) == json.loads(
        canonical_json(_NON_ASCII_PAYLOAD)
    )
    assert model_visible_json(_NON_ASCII_PAYLOAD).encode("utf-8") != canonical_json(
        _NON_ASCII_PAYLOAD
    )


def test_canonical_json_text_matches_canonical_bytes() -> None:
    """The text projection is the identity bytes, decoded."""
    assert canonical_json_text(_NON_ASCII_PAYLOAD).encode("utf-8") == canonical_json(
        _NON_ASCII_PAYLOAD
    )


@pytest.mark.parametrize(
    "value",
    [float("nan"), float("inf"), float("-inf")],
    ids=["nan", "inf", "-inf"],
)
def test_non_finite_scores_are_rejected_not_serialized(value: float) -> None:
    """A non-finite EPSS or CVSS score never becomes emitted evidence."""
    assert not math.isfinite(value)
    payload = {"cve": "CVE-2026-12345", "epss": value}

    with pytest.raises(CanonicalSerializationError):
        canonical_json(payload)
    with pytest.raises(CanonicalSerializationError):
        model_visible_json(payload)
    with pytest.raises(CanonicalSerializationError):
        canonical_sha256(payload)


def test_unserializable_payload_fails_closed() -> None:
    """A payload JSON cannot represent raises the canonical error, not TypeError."""
    with pytest.raises(CanonicalSerializationError):
        canonical_json({"when": object()})


def test_digest_shape_and_agreement() -> None:
    """canonical_sha256 is exactly the digest of the canonical identity bytes."""
    digest = canonical_sha256(_NON_ASCII_PAYLOAD)

    assert len(digest) == SHA256_HEX_LENGTH
    assert digest == sha256_hex(canonical_json(_NON_ASCII_PAYLOAD))
    assert digest == digest.lower()


def test_evidence_id_composes_contract_and_digest() -> None:
    """Evidence identity is the contract version bound to the payload digest."""
    composed = evidence_id("risk-policy:v1", _NON_ASCII_PAYLOAD)

    assert composed == f"risk-policy:v1@sha256:{canonical_sha256(_NON_ASCII_PAYLOAD)}"


@pytest.mark.parametrize("contract", ["", "   ", " risk-policy:v1", "risk-policy:v1 "])
def test_evidence_id_requires_a_normalized_contract_version(contract: str) -> None:
    """An unnormalized contract version cannot silently become part of an identity."""
    with pytest.raises(CanonicalSerializationError):
        evidence_id(contract, {"a": 1})


def _module_files() -> list[pathlib.Path]:
    """Return every opslens module except the canonical module itself."""
    return [
        path
        for path in sorted(_SRC_ROOT.rglob("*.py"))
        if "__pycache__" not in path.parts and path != _CANONICAL_MODULE
    ]


def test_no_module_canonicalizes_json_outside_the_shared_module() -> None:
    """Architecture guard: one canonical serialization, defined in exactly one place.

    Before this guard there were 34 independent canonicalizations in three
    semantic variants, so the same logical payload could carry two different
    evidence identities depending on which module hashed it.
    """
    offenders: list[str] = []
    for path in _module_files():
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if ast.unparse(node.func) != "json.dumps":
                continue
            keywords = {keyword.arg for keyword in node.keywords}
            if "indent" in keywords:
                # A human-readable report writer is not an identity serialization.
                continue
            if keywords & {"sort_keys", "separators", "ensure_ascii", "allow_nan"}:
                relative = path.relative_to(_SRC_ROOT)
                offenders.append(f"{relative}:{node.lineno}")

    assert offenders == [], (
        "canonical json.dumps outside opslens.shared.evidence.canonical: "
        + ", ".join(offenders)
    )


def test_no_module_hashes_its_own_json_serialization() -> None:
    """Architecture guard: digests come from the shared helpers, not local dumps."""
    offenders: list[str] = []
    for path in _module_files():
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            rendered = ast.unparse(node)
            if "sha256" in ast.unparse(node.func) and "json.dumps" in rendered:
                offenders.append(f"{path.relative_to(_SRC_ROOT)}:{node.lineno}")

    assert offenders == [], (
        "sha256 computed over a local json.dumps: " + ", ".join(offenders)
    )
