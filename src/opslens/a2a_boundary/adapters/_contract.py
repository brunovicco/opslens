"""Shared A2A 1.0 constants, identities, and strict JSON helpers."""

import json
from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
from typing import cast

from opslens.a2a_boundary.domain.errors import A2ABoundaryValidationError
from opslens.a2a_boundary.domain.reference import (
    A2A_REFERENCE_INTEROPERABILITY_CONTRACT_VERSION,
    A2AReference,
)
from opslens.shared.evidence import canonical_json

A2A_PROTOCOL_RELEASE = "1.0.0"
A2A_PROTOCOL_VERSION = "1.0"
A2A_PROTOCOL_BINDING = "JSONRPC"
A2A_JSONRPC_VERSION = "2.0"
A2A_SEND_MESSAGE_METHOD = "SendMessage"

AGENT_CARD_URL = "https://opslens.invalid/a2a"
AGENT_CARD_VERSION = "15.2.0"
REQUEST_ROLE = "ROLE_USER"
RESPONSE_ROLE = "ROLE_AGENT"
COMPLETED_TASK_STATE = "TASK_STATE_COMPLETED"
REFERENCE_ADMITTED = "REFERENCE_ADMITTED"


class A2AResponseKind(StrEnum):
    """Response forms exercised by the bounded offline experiment."""

    MESSAGE = "message"
    TASK = "task"


@dataclass(frozen=True, slots=True)
class A2AReferenceResult:
    """Admitted A2A protocol metadata re-bound to one OpsLens reference."""

    reference_sha256: str
    request_id: str
    context_id: str
    outcome: A2AResponseKind
    response_identity: str


@dataclass(frozen=True, slots=True)
class A2AOfflineExchangeEvidence:
    """Independent local observability dimensions for one offline exchange."""

    protocol_request_count: int
    peer_handler_count: int
    request_bytes: int
    response_bytes: int
    client_elapsed_ms: float
    handler_elapsed_ms: float
    retry_count: int
    failure_class: str | None
    reference_admission_outcome: str
    protocol_outcome: str
    protocol_binding: str
    protocol_version: str
    model_invocations: int
    capability_executions: int
    incremental_aws_cost_usd: float


@dataclass(frozen=True, slots=True)
class A2AOfflineExchange:
    """One admitted result plus its local protocol evidence."""

    result: A2AReferenceResult
    evidence: A2AOfflineExchangeEvidence


@dataclass(frozen=True, slots=True)
class AdmittedSendMessageRequest:
    """Strictly admitted SendMessage fields used by the offline peer."""

    reference: A2AReference
    request_id: str
    message_id: str


def canonical_json_bytes(value: object) -> bytes:
    """Serialize one protocol object deterministically for byte accounting."""
    return canonical_json(value)


def correlation_id(*, kind: str, reference_sha256: str) -> str:
    """Create one deterministic protocol correlation id with evidence-only authority."""
    payload = {
        "contract_version": A2A_REFERENCE_INTEROPERABILITY_CONTRACT_VERSION,
        "kind": kind,
        "reference_sha256": reference_sha256,
    }
    digest = sha256(canonical_json_bytes(payload)).hexdigest()
    return f"{A2A_REFERENCE_INTEROPERABILITY_CONTRACT_VERSION}:{kind}:{digest}"


def _reject_duplicate_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    """Reject duplicate JSON keys before framework-style coercion."""
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise A2ABoundaryValidationError(f"duplicate JSON key is not allowed: {key}")
        result[key] = value
    return result


def load_raw_json(raw: bytes) -> object:
    """Decode strict UTF-8 JSON while preserving duplicate-key rejection."""
    if type(raw) is not bytes:
        raise A2ABoundaryValidationError("A2A protocol input must be raw bytes")
    try:
        text = raw.decode("utf-8", errors="strict")
        return json.loads(text, object_pairs_hook=_reject_duplicate_pairs)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise A2ABoundaryValidationError("A2A protocol input must be valid UTF-8 JSON") from exc


def expect_object(
    value: object,
    *,
    label: str,
    exact_keys: frozenset[str],
) -> dict[str, object]:
    """Require one exact JSON object shape."""
    if type(value) is not dict:
        raise A2ABoundaryValidationError(f"{label} must be a JSON object")
    raw = cast(dict[object, object], value)
    if any(type(key) is not str for key in raw):
        raise A2ABoundaryValidationError(f"{label} keys must be strings")
    typed = cast(dict[str, object], raw)
    if frozenset(typed) != exact_keys:
        raise A2ABoundaryValidationError(f"{label} keys violate the frozen contract")
    return typed


def expect_string(value: object, *, label: str) -> str:
    """Require one non-empty string field."""
    if type(value) is not str or not value:
        raise A2ABoundaryValidationError(f"{label} must be a non-empty string")
    return value


def expect_single_data_part(value: object, *, label: str) -> dict[str, object]:
    """Require exactly one A2A structured-data Part."""
    if type(value) is not list:
        raise A2ABoundaryValidationError(f"{label} must be a list")
    parts = cast(list[object], value)
    if len(parts) != 1:
        raise A2ABoundaryValidationError(f"{label} must contain exactly one Part")
    return expect_object(
        parts[0],
        label=f"{label}[0]",
        exact_keys=frozenset({"data"}),
    )
