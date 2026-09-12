"""Strict A2A 1.0 JSON-RPC SendMessage projection and result admission."""

from typing import cast

from opslens.a2a_boundary.adapters._contract import (
    A2A_JSONRPC_VERSION,
    A2A_SEND_MESSAGE_METHOD,
    COMPLETED_TASK_STATE,
    REFERENCE_ADMITTED,
    REQUEST_ROLE,
    RESPONSE_ROLE,
    A2AReferenceResult,
    A2AResponseKind,
    AdmittedSendMessageRequest,
    canonical_json_bytes,
    correlation_id,
    expect_object,
    expect_single_data_part,
    expect_string,
    load_raw_json,
)
from opslens.a2a_boundary.domain.errors import A2ABoundaryValidationError
from opslens.a2a_boundary.domain.reference import (
    A2A_REFERENCE_INTEROPERABILITY_CONTRACT_VERSION,
    A2AReference,
)


def _reference_from_protocol_data(value: object) -> A2AReference:
    """Admit only the three-field reference projection from one data Part."""
    data = expect_object(
        value,
        label="A2A reference data",
        exact_keys=frozenset({"handoff_id", "specialist_task_id", "reference_sha256"}),
    )
    digest = expect_string(data["reference_sha256"], label="reference_sha256")
    return A2AReference(
        handoff_id=expect_string(data["handoff_id"], label="handoff_id"),
        specialist_task_id=expect_string(
            data["specialist_task_id"],
            label="specialist_task_id",
        ),
        reference_sha256=digest,
        reference_id=(
            f"{A2A_REFERENCE_INTEROPERABILITY_CONTRACT_VERSION}:reference:{digest}"
        ),
    )


def build_send_message_request(*, reference: A2AReference) -> bytes:
    """Project one admitted reference into the bounded A2A 1.0 SendMessage request."""
    if type(reference) is not A2AReference:
        raise A2ABoundaryValidationError("reference must be one admitted A2AReference")
    request_id = correlation_id(kind="request", reference_sha256=reference.reference_sha256)
    message_id = correlation_id(kind="message", reference_sha256=reference.reference_sha256)
    return canonical_json_bytes(
        {
            "jsonrpc": A2A_JSONRPC_VERSION,
            "id": request_id,
            "method": A2A_SEND_MESSAGE_METHOD,
            "params": {
                "message": {
                    "messageId": message_id,
                    "role": REQUEST_ROLE,
                    "parts": [
                        {
                            "data": {
                                "handoff_id": reference.handoff_id,
                                "specialist_task_id": reference.specialist_task_id,
                                "reference_sha256": reference.reference_sha256,
                            }
                        }
                    ],
                }
            },
        }
    )


def parse_send_message_request(*, raw: bytes) -> AdmittedSendMessageRequest:
    """Validate raw A2A JSON-RPC before resolving any OpsLens domain state."""
    root = expect_object(
        load_raw_json(raw),
        label="JSON-RPC request",
        exact_keys=frozenset({"jsonrpc", "id", "method", "params"}),
    )
    if root["jsonrpc"] != A2A_JSONRPC_VERSION:
        raise A2ABoundaryValidationError("unsupported JSON-RPC version")
    if root["method"] != A2A_SEND_MESSAGE_METHOD:
        raise A2ABoundaryValidationError("unsupported A2A method")

    params = expect_object(
        root["params"],
        label="SendMessage params",
        exact_keys=frozenset({"message"}),
    )
    message = expect_object(
        params["message"],
        label="SendMessage message",
        exact_keys=frozenset({"messageId", "role", "parts"}),
    )
    if message["role"] != REQUEST_ROLE:
        raise A2ABoundaryValidationError("SendMessage request role must be ROLE_USER")

    part = expect_single_data_part(message["parts"], label="SendMessage parts")
    reference = _reference_from_protocol_data(part["data"])
    request_id = expect_string(root["id"], label="JSON-RPC id")
    expected_request_id = correlation_id(
        kind="request",
        reference_sha256=reference.reference_sha256,
    )
    if request_id != expected_request_id:
        raise A2ABoundaryValidationError("JSON-RPC id is not bound to the reference")

    message_id = expect_string(message["messageId"], label="messageId")
    expected_message_id = correlation_id(
        kind="message",
        reference_sha256=reference.reference_sha256,
    )
    if message_id != expected_message_id:
        raise A2ABoundaryValidationError("messageId is not bound to the reference")
    return AdmittedSendMessageRequest(
        reference=reference,
        request_id=request_id,
        message_id=message_id,
    )


def build_message_response(*, request: AdmittedSendMessageRequest) -> bytes:
    """Build one direct metadata-only A2A Message response."""
    digest = request.reference.reference_sha256
    context_id = correlation_id(kind="context", reference_sha256=digest)
    message_id = correlation_id(kind="response-message", reference_sha256=digest)
    return canonical_json_bytes(
        {
            "jsonrpc": A2A_JSONRPC_VERSION,
            "id": request.request_id,
            "result": {
                "message": {
                    "messageId": message_id,
                    "contextId": context_id,
                    "role": RESPONSE_ROLE,
                    "parts": [
                        {
                            "data": {
                                "admission": REFERENCE_ADMITTED,
                                "referenceSha256": digest,
                            }
                        }
                    ],
                }
            },
        }
    )


def build_task_response(*, request: AdmittedSendMessageRequest) -> bytes:
    """Build one terminal A2A Task response with no Artifact/business output."""
    digest = request.reference.reference_sha256
    return canonical_json_bytes(
        {
            "jsonrpc": A2A_JSONRPC_VERSION,
            "id": request.request_id,
            "result": {
                "task": {
                    "id": correlation_id(kind="task", reference_sha256=digest),
                    "contextId": correlation_id(kind="context", reference_sha256=digest),
                    "status": {"state": COMPLETED_TASK_STATE},
                }
            },
        }
    )


def _response_root(
    *,
    raw: bytes,
    reference: A2AReference,
) -> tuple[dict[str, object], str, str]:
    """Validate common JSON-RPC response identity and return result/context metadata."""
    root = expect_object(
        load_raw_json(raw),
        label="JSON-RPC response",
        exact_keys=frozenset({"jsonrpc", "id", "result"}),
    )
    if root["jsonrpc"] != A2A_JSONRPC_VERSION:
        raise A2ABoundaryValidationError("unsupported JSON-RPC response version")
    request_id = expect_string(root["id"], label="JSON-RPC response id")
    expected_request_id = correlation_id(
        kind="request",
        reference_sha256=reference.reference_sha256,
    )
    if request_id != expected_request_id:
        raise A2ABoundaryValidationError("JSON-RPC response id is not bound to the reference")
    if type(root["result"]) is not dict:
        raise A2ABoundaryValidationError("SendMessage result must be a JSON object")
    raw_result = cast(dict[object, object], root["result"])
    if any(type(key) is not str for key in raw_result):
        raise A2ABoundaryValidationError("SendMessage result keys must be strings")
    result = cast(dict[str, object], raw_result)
    context_id = correlation_id(
        kind="context",
        reference_sha256=reference.reference_sha256,
    )
    return result, request_id, context_id


def admit_send_message_response(
    *,
    raw: bytes,
    reference: A2AReference,
) -> A2AReferenceResult:
    """Admit only bounded Message or terminal Task metadata tied to one reference."""
    if type(reference) is not A2AReference:
        raise A2ABoundaryValidationError("reference must be one admitted A2AReference")
    result, request_id, context_id = _response_root(raw=raw, reference=reference)

    if frozenset(result) == frozenset({"message"}):
        message = expect_object(
            result["message"],
            label="SendMessage response Message",
            exact_keys=frozenset({"messageId", "contextId", "role", "parts"}),
        )
        if message["role"] != RESPONSE_ROLE or message["contextId"] != context_id:
            raise A2ABoundaryValidationError("response Message authority metadata mismatch")
        message_id = expect_string(message["messageId"], label="response messageId")
        expected_message_id = correlation_id(
            kind="response-message",
            reference_sha256=reference.reference_sha256,
        )
        if message_id != expected_message_id:
            raise A2ABoundaryValidationError("response messageId is not reference-bound")
        part = expect_single_data_part(message["parts"], label="response Message parts")
        data = expect_object(
            part["data"],
            label="response Message data",
            exact_keys=frozenset({"admission", "referenceSha256"}),
        )
        if data["admission"] != REFERENCE_ADMITTED:
            raise A2ABoundaryValidationError("response Message admission is not accepted")
        if data["referenceSha256"] != reference.reference_sha256:
            raise A2ABoundaryValidationError("response Message reference digest mismatch")
        return A2AReferenceResult(
            reference_sha256=reference.reference_sha256,
            request_id=request_id,
            context_id=context_id,
            outcome=A2AResponseKind.MESSAGE,
            response_identity=message_id,
        )

    if frozenset(result) == frozenset({"task"}):
        task = expect_object(
            result["task"],
            label="SendMessage response Task",
            exact_keys=frozenset({"id", "contextId", "status"}),
        )
        if task["contextId"] != context_id:
            raise A2ABoundaryValidationError("response Task contextId is not reference-bound")
        task_id = expect_string(task["id"], label="response Task id")
        expected_task_id = correlation_id(
            kind="task",
            reference_sha256=reference.reference_sha256,
        )
        if task_id != expected_task_id:
            raise A2ABoundaryValidationError("response Task id is not reference-bound")
        status = expect_object(
            task["status"],
            label="response Task status",
            exact_keys=frozenset({"state"}),
        )
        if status["state"] != COMPLETED_TASK_STATE:
            raise A2ABoundaryValidationError("only terminal completed Tasks are admitted")
        return A2AReferenceResult(
            reference_sha256=reference.reference_sha256,
            request_id=request_id,
            context_id=context_id,
            outcome=A2AResponseKind.TASK,
            response_identity=task_id,
        )

    raise A2ABoundaryValidationError(
        "SendMessage result must contain exactly one bounded Message or Task"
    )


__all__ = [
    "admit_send_message_response",
    "build_message_response",
    "build_send_message_request",
    "build_task_response",
    "parse_send_message_request",
]
