"""Check the frozen OpsLens A2A profile against the official Python SDK."""

import importlib
import json
from importlib.metadata import version
from time import perf_counter_ns
from typing import Any, cast

from _bootstrap import ensure_repository_src_on_path

ensure_repository_src_on_path()

from opslens.a2a_boundary.adapters import (  # noqa: E402
    A2A_PROTOCOL_BINDING,
    A2A_PROTOCOL_VERSION,
    A2AResponseKind,
    OfflineA2AReferencePeer,
    build_agent_card,
    build_send_message_request,
)
from opslens.a2a_boundary.application.registry import A2AReferenceRegistry  # noqa: E402
from opslens.agent_baseline.domain.models import (  # noqa: E402
    AgentCapability,
    create_single_agent_task,
)
from opslens.multi_agent.application.handoff import admit_multi_agent_handoff  # noqa: E402
from opslens.multi_agent.domain.handoff import (  # noqa: E402
    AgentSpecialization,
    MultiAgentHandoffDecision,
    SpecialistAgentTask,
    create_multi_agent_handoff_proposal,
    create_triage_agent_task,
)

SDK_VERSION = "1.1.4"
SDK_TAG = "v1.1.4"
SDK_SOURCE_COMMIT = "2d4d3048b245d2af854bad804f0e722ea9febc08"
SDK_ACQUISITION = "EXACT_GITHUB_SOURCE_COMMIT_IN_CI_ONLY"


def _object(value: object, *, label: str) -> dict[str, object]:
    """Require one JSON object with string keys."""
    if type(value) is not dict:
        raise RuntimeError(f"{label} must be a JSON object")
    raw = cast(dict[object, object], value)
    if any(type(key) is not str for key in raw):
        raise RuntimeError(f"{label} keys must be strings")
    return cast(dict[str, object], raw)


def _list(value: object, *, label: str) -> list[object]:
    """Require one JSON array."""
    if type(value) is not list:
        raise RuntimeError(f"{label} must be a JSON array")
    return cast(list[object], value)


def _json(raw: bytes, *, label: str) -> dict[str, object]:
    """Decode one OpsLens-owned JSON payload for SDK-oracle inspection."""
    value = json.loads(raw.decode("utf-8"))
    return _object(value, label=label)


def _specialist_task() -> SpecialistAgentTask:
    """Create one already-admitted specialist task without model execution."""
    source_task = create_single_agent_task(
        text="Which admitted security capability should analyze this evidence?",
        allowed_capabilities=(
            AgentCapability.PUBLIC_REPOSITORY_ANALYSIS,
            AgentCapability.STRUCTURED_SECURITY_QUERY,
        ),
    )
    proposal = create_multi_agent_handoff_proposal(
        source_task_id=source_task.task_id,
        decision=MultiAgentHandoffDecision.HANDOFF,
        target_specialization=AgentSpecialization.EVIDENCE_ANALYSIS,
    )
    admitted = admit_multi_agent_handoff(
        source=create_triage_agent_task(task=source_task),
        proposal=proposal,
    )
    if not isinstance(admitted, SpecialistAgentTask):
        raise RuntimeError("SDK conformance probe requires one admitted specialist task")
    return admitted


def _sdk_modules() -> tuple[Any, Any, Any]:
    """Load exact-version external SDK modules only inside the isolated probe."""
    installed = version("a2a-sdk")
    if installed != SDK_VERSION:
        raise RuntimeError(f"expected a2a-sdk {SDK_VERSION}, found {installed}")
    return (
        importlib.import_module("a2a.types"),
        importlib.import_module("google.protobuf.json_format"),
        importlib.import_module("jsonrpc.jsonrpc2"),
    )


def _parse_with_sdk(
    *,
    json_format_module: Any,
    message_type: Any,
    value: dict[str, object],
) -> tuple[Any, dict[str, object]]:
    """Parse and round-trip one dictionary through one official protobuf type."""
    message = message_type()
    json_format_module.ParseDict(value, message)
    roundtrip = json_format_module.MessageToDict(message)
    return message, _object(roundtrip, label="SDK protobuf JSON round-trip")


def _agent_card_check(*, sdk_types: Any, json_format_module: Any) -> dict[str, object]:
    """Verify the bounded Agent Card against the SDK proto and semantic round-trip."""
    original = _json(build_agent_card(), label="OpsLens Agent Card")
    proto, roundtrip = _parse_with_sdk(
        json_format_module=json_format_module,
        message_type=sdk_types.AgentCard,
        value=original,
    )
    interfaces = _list(roundtrip.get("supportedInterfaces"), label="supportedInterfaces")
    if len(interfaces) != 1:
        raise RuntimeError("SDK Agent Card round-trip must preserve one supportedInterface")
    interface = _object(interfaces[0], label="supportedInterface")
    if interface.get("protocolBinding") != A2A_PROTOCOL_BINDING:
        raise RuntimeError("SDK changed the selected protocolBinding")
    if interface.get("protocolVersion") != A2A_PROTOCOL_VERSION:
        raise RuntimeError("SDK changed the selected protocolVersion")

    capabilities = _object(original["capabilities"], label="original capabilities")
    roundtrip_capabilities = _object(
        roundtrip.get("capabilities", {}),
        label="round-trip capabilities",
    )
    omitted_default_false = sorted(
        key
        for key, value in capabilities.items()
        if value is False and key not in roundtrip_capabilities
    )
    return {
        "parse": "PASS",
        "semantic_roundtrip": "PASS",
        "supported_interface_count": len(interfaces),
        "protocol_binding": interface["protocolBinding"],
        "protocol_version": interface["protocolVersion"],
        "sdk_message_type": type(proto).__name__,
        "omitted_default_false_fields": omitted_default_false,
    }


def _request_check(
    *,
    sdk_types: Any,
    json_format_module: Any,
    jsonrpc_module: Any,
    raw_request: bytes,
) -> dict[str, object]:
    """Verify SendMessage params and JSON-RPC construction through official libraries."""
    root = _json(raw_request, label="OpsLens SendMessage JSON-RPC request")
    params = _object(root["params"], label="SendMessage params")
    _, roundtrip = _parse_with_sdk(
        json_format_module=json_format_module,
        message_type=sdk_types.SendMessageRequest,
        value=params,
    )
    message = _object(roundtrip.get("message"), label="SDK SendMessage message")
    if message.get("role") != "ROLE_USER":
        raise RuntimeError("SDK changed the SendMessage request role")
    parts = _list(message.get("parts"), label="SDK SendMessage parts")
    if len(parts) != 1:
        raise RuntimeError("SDK must preserve exactly one bounded data Part")
    part = _object(parts[0], label="SDK SendMessage Part")
    data = _object(part.get("data"), label="SDK SendMessage data")
    if frozenset(data) != frozenset(
        {"handoff_id", "specialist_task_id", "reference_sha256"}
    ):
        raise RuntimeError("SDK changed the bounded reference data fields")

    rpc = jsonrpc_module.JSONRPC20Request(
        method="SendMessage",
        params=roundtrip,
        _id=root["id"],
    )
    rpc_data = _object(dict(rpc.data), label="official JSON-RPC request")
    if rpc_data.get("jsonrpc") != "2.0" or rpc_data.get("method") != "SendMessage":
        raise RuntimeError("official JSON-RPC library changed the selected request semantics")
    if rpc_data.get("id") != root["id"]:
        raise RuntimeError("official JSON-RPC library did not preserve the string request id")
    return {
        "parse": "PASS",
        "semantic_roundtrip": "PASS",
        "jsonrpc_construction": "PASS",
        "role": message["role"],
        "reference_fields": sorted(data),
        "jsonrpc_version": rpc_data["jsonrpc"],
        "method": rpc_data["method"],
        "request_id_preserved": True,
    }


def _response_check(
    *,
    sdk_types: Any,
    json_format_module: Any,
    raw_response: bytes,
    expected_kind: str,
) -> dict[str, object]:
    """Verify one OpsLens JSON-RPC result as official SendMessageResponse."""
    root = _json(raw_response, label=f"OpsLens {expected_kind} response")
    result = _object(root["result"], label=f"{expected_kind} result")
    _, roundtrip = _parse_with_sdk(
        json_format_module=json_format_module,
        message_type=sdk_types.SendMessageResponse,
        value=result,
    )
    if frozenset(roundtrip) != frozenset({expected_kind}):
        raise RuntimeError(f"SDK did not preserve SendMessageResponse {expected_kind}")
    return {
        "parse": "PASS",
        "semantic_roundtrip": "PASS",
        "result_kind": expected_kind,
    }


def main() -> None:
    """Emit machine-readable independent SDK conformance evidence."""
    started_ns = perf_counter_ns()
    sdk_types, json_format_module, jsonrpc_module = _sdk_modules()

    specialist = _specialist_task()
    registry = A2AReferenceRegistry()
    reference = registry.register(specialist_task=specialist)
    raw_request = build_send_message_request(reference=reference)

    message_peer = OfflineA2AReferencePeer(registry=registry)
    raw_message, _ = message_peer.handle(
        raw=raw_request,
        response_kind=A2AResponseKind.MESSAGE,
    )
    task_peer = OfflineA2AReferencePeer(registry=registry)
    raw_task, _ = task_peer.handle(
        raw=raw_request,
        response_kind=A2AResponseKind.TASK,
    )

    payload = {
        "gate": "Phase 15 Gate 15.3",
        "sdk": {
            "distribution": "a2a-sdk",
            "version": version("a2a-sdk"),
            "release_tag": SDK_TAG,
            "source_commit": SDK_SOURCE_COMMIT,
            "acquisition": SDK_ACQUISITION,
        },
        "agent_card": _agent_card_check(
            sdk_types=sdk_types,
            json_format_module=json_format_module,
        ),
        "send_message_request": _request_check(
            sdk_types=sdk_types,
            json_format_module=json_format_module,
            jsonrpc_module=jsonrpc_module,
            raw_request=raw_request,
        ),
        "message_response": _response_check(
            sdk_types=sdk_types,
            json_format_module=json_format_module,
            raw_response=raw_message,
            expected_kind="message",
        ),
        "task_response": _response_check(
            sdk_types=sdk_types,
            json_format_module=json_format_module,
            raw_response=raw_task,
            expected_kind="task",
        ),
        "authority": {
            "sdk_is_protocol_oracle_only": True,
            "opslens_raw_validation_remains_authoritative": True,
            "opslens_content_identity_remains_authoritative": True,
        },
        "impact": {
            "protocol_network_requests": 0,
            "dependency_acquisition_network_is_ci_setup_only": True,
            "model_invocations": 0,
            "capability_executions": 0,
            "new_aws_resources": 0,
            "new_iam_roles_or_policies": 0,
            "business_result_transport": 0,
            "incremental_aws_cost_usd": 0.0,
        },
        "elapsed_ms": (perf_counter_ns() - started_ns) / 1_000_000,
    }
    print(json.dumps(payload, allow_nan=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
