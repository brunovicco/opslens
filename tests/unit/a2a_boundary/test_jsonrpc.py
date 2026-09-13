"""Tests for the strict offline A2A 1.0 JSON-RPC reference adapter."""

import json
from typing import cast

import pytest

from opslens.a2a_boundary.adapters import (
    A2A_JSONRPC_VERSION,
    A2A_PROTOCOL_BINDING,
    A2A_PROTOCOL_RELEASE,
    A2A_PROTOCOL_VERSION,
    A2A_SEND_MESSAGE_METHOD,
    A2AResponseKind,
    OfflineA2AReferencePeer,
    admit_agent_card,
    admit_send_message_response,
    build_agent_card,
    build_send_message_request,
    parse_send_message_request,
    run_offline_exchange,
)
from opslens.a2a_boundary.application.registry import A2AReferenceRegistry
from opslens.a2a_boundary.domain.errors import (
    A2ABoundaryValidationError,
    A2AReferenceNotFoundError,
    A2AReplayError,
)
from opslens.a2a_boundary.domain.reference import create_a2a_reference
from opslens.multi_agent.domain.handoff import SpecialistAgentTask


def _decode_object(raw: bytes) -> dict[str, object]:
    """Decode one test JSON object with explicit typing."""
    value = json.loads(raw)
    if type(value) is not dict:
        raise AssertionError("fixture JSON must be an object")
    return cast(dict[str, object], value)


def _encode(value: object) -> bytes:
    """Encode one deterministic JSON fixture mutation."""
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _registered_peer(
    specialist_task: SpecialistAgentTask,
) -> tuple[A2AReferenceRegistry, OfflineA2AReferencePeer]:
    """Create one registered peer with isolated replay state."""
    registry = A2AReferenceRegistry()
    registry.register(specialist_task=specialist_task)
    return registry, OfflineA2AReferencePeer(registry=registry)


def test_protocol_constants_are_frozen_to_corrected_a2a_1_0() -> None:
    """Exercise the frozen A2A boundary behavior."""
    assert A2A_PROTOCOL_RELEASE == "1.0.0"
    assert A2A_PROTOCOL_VERSION == "1.0"
    assert A2A_PROTOCOL_BINDING == "JSONRPC"
    assert A2A_JSONRPC_VERSION == "2.0"
    assert A2A_SEND_MESSAGE_METHOD == "SendMessage"


def test_agent_card_admits_exact_selected_interface() -> None:
    """Exercise the frozen A2A boundary behavior."""
    raw = build_agent_card()
    admitted = admit_agent_card(raw=raw)

    assert admitted["name"] == "OpsLens Reference Peer"
    interfaces = cast(list[object], admitted["supportedInterfaces"])
    interface = cast(dict[str, object], interfaces[0])
    assert interface == {
        "protocolBinding": "JSONRPC",
        "protocolVersion": "1.0",
        "url": "https://opslens.invalid/a2a",
    }


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("protocolBinding", "GRPC", "unsupported A2A protocol binding"),
        ("protocolVersion", "0.3", "unsupported A2A protocol version"),
    ],
)
def test_agent_card_rejects_unselected_binding_or_version(
    field: str,
    value: str,
    message: str,
) -> None:
    """Exercise the frozen A2A boundary behavior."""
    card = _decode_object(build_agent_card())
    interfaces = cast(list[object], card["supportedInterfaces"])
    interface = cast(dict[str, object], interfaces[0])
    interface[field] = value

    with pytest.raises(A2ABoundaryValidationError, match=message):
        admit_agent_card(raw=_encode(card))


def test_agent_card_rejects_unknown_fields_before_domain_use() -> None:
    """Exercise the frozen A2A boundary behavior."""
    card = _decode_object(build_agent_card())
    card["unexpected"] = True

    with pytest.raises(A2ABoundaryValidationError, match="keys violate"):
        admit_agent_card(raw=_encode(card))


def test_send_message_request_is_reference_only_and_round_trips(
    specialist_task: SpecialistAgentTask,
) -> None:
    """Exercise the frozen A2A boundary behavior."""
    reference = create_a2a_reference(specialist_task=specialist_task)
    raw = build_send_message_request(reference=reference)
    parsed = parse_send_message_request(raw=raw)
    request = _decode_object(raw)

    assert parsed.reference == reference
    assert set(request) == {"jsonrpc", "id", "method", "params"}

    params = cast(dict[str, object], request["params"])
    assert set(params) == {"message"}
    message = cast(dict[str, object], params["message"])
    assert set(message) == {"messageId", "role", "parts"}
    assert message["role"] == "ROLE_USER"

    parts = cast(list[object], message["parts"])
    part = cast(dict[str, object], parts[0])
    assert set(part) == {"data"}
    data = cast(dict[str, object], part["data"])
    assert data == {
        "handoff_id": reference.handoff_id,
        "reference_sha256": reference.reference_sha256,
        "specialist_task_id": reference.specialist_task_id,
    }


def test_request_rejects_duplicate_json_keys_before_coercion(
    specialist_task: SpecialistAgentTask,
) -> None:
    """Exercise the frozen A2A boundary behavior."""
    reference = create_a2a_reference(specialist_task=specialist_task)
    raw = build_send_message_request(reference=reference)
    duplicate = raw[:-1] + b',"method":"SendMessage"}'

    with pytest.raises(A2ABoundaryValidationError, match="duplicate JSON key"):
        parse_send_message_request(raw=duplicate)


def test_request_rejects_unknown_top_level_fields(
    specialist_task: SpecialistAgentTask,
) -> None:
    """Exercise the frozen A2A boundary behavior."""
    reference = create_a2a_reference(specialist_task=specialist_task)
    request = _decode_object(build_send_message_request(reference=reference))
    request["extra"] = "authority-expansion-attempt"

    with pytest.raises(A2ABoundaryValidationError, match="keys violate"):
        parse_send_message_request(raw=_encode(request))


def test_request_rejects_unsupported_method(
    specialist_task: SpecialistAgentTask,
) -> None:
    """Exercise the frozen A2A boundary behavior."""
    reference = create_a2a_reference(specialist_task=specialist_task)
    request = _decode_object(build_send_message_request(reference=reference))
    request["method"] = "GetTask"

    with pytest.raises(A2ABoundaryValidationError, match="unsupported A2A method"):
        parse_send_message_request(raw=_encode(request))


def test_request_rejects_reference_argument_expansion(
    specialist_task: SpecialistAgentTask,
) -> None:
    """Exercise the frozen A2A boundary behavior."""
    reference = create_a2a_reference(specialist_task=specialist_task)
    request = _decode_object(build_send_message_request(reference=reference))
    params = cast(dict[str, object], request["params"])
    message = cast(dict[str, object], params["message"])
    parts = cast(list[object], message["parts"])
    part = cast(dict[str, object], parts[0])
    data = cast(dict[str, object], part["data"])
    data["allowed_capabilities"] = ["public_repository_analysis"]

    with pytest.raises(A2ABoundaryValidationError, match="reference data keys violate"):
        parse_send_message_request(raw=_encode(request))


@pytest.mark.parametrize("response_kind", list(A2AResponseKind))
def test_offline_exchange_admits_message_and_terminal_task_metadata(
    specialist_task: SpecialistAgentTask,
    response_kind: A2AResponseKind,
) -> None:
    """Exercise the frozen A2A boundary behavior."""
    registry, peer = _registered_peer(specialist_task)
    reference = registry.register(specialist_task=specialist_task)

    exchange = run_offline_exchange(
        peer=peer,
        reference=reference,
        response_kind=response_kind,
    )

    assert exchange.result.reference_sha256 == reference.reference_sha256
    assert exchange.result.outcome is response_kind
    assert exchange.evidence.protocol_request_count == 1
    assert exchange.evidence.peer_handler_count == 1
    assert exchange.evidence.request_bytes > 0
    assert exchange.evidence.response_bytes > 0
    assert exchange.evidence.client_elapsed_ms >= 0
    assert exchange.evidence.handler_elapsed_ms >= 0
    assert exchange.evidence.retry_count == 0
    assert exchange.evidence.failure_class is None
    assert exchange.evidence.reference_admission_outcome == "ADMITTED"
    assert exchange.evidence.protocol_binding == "JSONRPC"
    assert exchange.evidence.protocol_version == "1.0"
    assert exchange.evidence.model_invocations == 0
    assert exchange.evidence.capability_executions == 0
    assert exchange.evidence.incremental_aws_cost_usd == 0.0


def test_peer_rejects_duplicate_request_and_message_identity(
    specialist_task: SpecialistAgentTask,
) -> None:
    """Exercise the frozen A2A boundary behavior."""
    registry, peer = _registered_peer(specialist_task)
    reference = registry.register(specialist_task=specialist_task)
    raw = build_send_message_request(reference=reference)

    peer.handle(raw=raw, response_kind=A2AResponseKind.TASK)

    with pytest.raises(A2AReplayError, match="duplicate JSON-RPC request id"):
        peer.handle(raw=raw, response_kind=A2AResponseKind.TASK)


def test_peer_rejects_unknown_reference(
    specialist_task: SpecialistAgentTask,
    second_specialist_task: SpecialistAgentTask,
) -> None:
    """Exercise the frozen A2A boundary behavior."""
    _, peer = _registered_peer(specialist_task)
    unknown = create_a2a_reference(specialist_task=second_specialist_task)

    with pytest.raises(A2AReferenceNotFoundError, match="not registered"):
        peer.handle(
            raw=build_send_message_request(reference=unknown),
            response_kind=A2AResponseKind.TASK,
        )


def test_response_rejects_non_terminal_task(
    specialist_task: SpecialistAgentTask,
) -> None:
    """Exercise the frozen A2A boundary behavior."""
    registry, peer = _registered_peer(specialist_task)
    reference = registry.register(specialist_task=specialist_task)
    raw_request = build_send_message_request(reference=reference)
    raw_response, _ = peer.handle(
        raw=raw_request,
        response_kind=A2AResponseKind.TASK,
    )
    response = _decode_object(raw_response)
    result = cast(dict[str, object], response["result"])
    task = cast(dict[str, object], result["task"])
    status = cast(dict[str, object], task["status"])
    status["state"] = "TASK_STATE_WORKING"

    with pytest.raises(A2ABoundaryValidationError, match="terminal completed"):
        admit_send_message_response(raw=_encode(response), reference=reference)


@pytest.mark.parametrize(
    "state",
    [
        "TASK_STATE_FAILED",
        "TASK_STATE_CANCELED",
        "TASK_STATE_REJECTED",
    ],
)
def test_response_rejects_terminal_failure_states(
    specialist_task: SpecialistAgentTask,
    state: str,
) -> None:
    """Exercise the frozen A2A boundary behavior."""
    registry, peer = _registered_peer(specialist_task)
    reference = registry.register(specialist_task=specialist_task)
    raw_response, _ = peer.handle(
        raw=build_send_message_request(reference=reference),
        response_kind=A2AResponseKind.TASK,
    )
    response = _decode_object(raw_response)
    result = cast(dict[str, object], response["result"])
    task = cast(dict[str, object], result["task"])
    status = cast(dict[str, object], task["status"])
    status["state"] = state

    with pytest.raises(A2ABoundaryValidationError, match="terminal completed"):
        admit_send_message_response(raw=_encode(response), reference=reference)


def test_response_rejects_artifact_or_business_payload(
    specialist_task: SpecialistAgentTask,
) -> None:
    """Exercise the frozen A2A boundary behavior."""
    registry, peer = _registered_peer(specialist_task)
    reference = registry.register(specialist_task=specialist_task)
    raw_response, _ = peer.handle(
        raw=build_send_message_request(reference=reference),
        response_kind=A2AResponseKind.TASK,
    )
    response = _decode_object(raw_response)
    result = cast(dict[str, object], response["result"])
    task = cast(dict[str, object], result["task"])
    task["artifacts"] = [
        {
            "artifactId": "not-admitted",
            "parts": [{"data": {"business_result": "forbidden"}}],
        }
    ]

    with pytest.raises(A2ABoundaryValidationError, match="Task keys violate"):
        admit_send_message_response(raw=_encode(response), reference=reference)


def test_message_response_rejects_reference_digest_mismatch(
    specialist_task: SpecialistAgentTask,
) -> None:
    """Exercise the frozen A2A boundary behavior."""
    registry, peer = _registered_peer(specialist_task)
    reference = registry.register(specialist_task=specialist_task)
    raw_response, _ = peer.handle(
        raw=build_send_message_request(reference=reference),
        response_kind=A2AResponseKind.MESSAGE,
    )
    response = _decode_object(raw_response)
    result = cast(dict[str, object], response["result"])
    message = cast(dict[str, object], result["message"])
    parts = cast(list[object], message["parts"])
    part = cast(dict[str, object], parts[0])
    data = cast(dict[str, object], part["data"])
    data["referenceSha256"] = "0" * 64

    with pytest.raises(A2ABoundaryValidationError, match="reference digest mismatch"):
        admit_send_message_response(raw=_encode(response), reference=reference)
