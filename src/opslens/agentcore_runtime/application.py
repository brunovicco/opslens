"""Application boundary for bounded AgentCore Runtime reasoning invocations."""

import json
from collections.abc import Mapping
from typing import cast

from opslens.agent_baseline.application.reasoning import reason_about_task
from opslens.agent_baseline.domain.models import (
    MAX_AGENT_ALLOWED_CAPABILITIES,
    AgentCapability,
    SingleAgentTask,
    create_single_agent_task,
)
from opslens.agent_baseline.ports.reasoning import AgentReasoningModel
from opslens.agentcore_runtime.domain import (
    MAX_AGENTCORE_RUNTIME_REQUEST_UTF8_BYTES,
    AgentCoreReasoningProjection,
    AgentCoreRuntimeValidationError,
)

_RUNTIME_REQUEST_KEYS = frozenset({"allowed_capabilities", "task_text"})


def admit_agentcore_runtime_request(raw_body: bytes) -> SingleAgentTask:
    """Convert one bounded untrusted HTTP JSON body into the existing task authority."""
    if type(raw_body) is not bytes:
        raise AgentCoreRuntimeValidationError("runtime request body must be bytes")
    if not raw_body:
        raise AgentCoreRuntimeValidationError("runtime request body cannot be empty")
    if len(raw_body) > MAX_AGENTCORE_RUNTIME_REQUEST_UTF8_BYTES:
        raise AgentCoreRuntimeValidationError("runtime request exceeds the UTF-8 byte limit")

    try:
        text = raw_body.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise AgentCoreRuntimeValidationError("runtime request must be valid UTF-8") from exc

    try:
        loaded: object = json.loads(text)
    except json.JSONDecodeError as exc:
        raise AgentCoreRuntimeValidationError("runtime request must be valid JSON") from exc

    if not isinstance(loaded, Mapping):
        raise AgentCoreRuntimeValidationError("runtime request must be one JSON object")
    payload = cast(Mapping[object, object], loaded)
    if any(type(key) is not str for key in payload):
        raise AgentCoreRuntimeValidationError("runtime request keys must be strings")
    typed_payload = cast(Mapping[str, object], payload)
    if frozenset(typed_payload) != _RUNTIME_REQUEST_KEYS:
        raise AgentCoreRuntimeValidationError(
            "runtime request must contain exactly task_text and allowed_capabilities"
        )

    task_text = typed_payload["task_text"]
    if type(task_text) is not str:
        raise AgentCoreRuntimeValidationError("task_text must be a string")

    raw_capabilities = typed_payload["allowed_capabilities"]
    if type(raw_capabilities) is not list:
        raise AgentCoreRuntimeValidationError("allowed_capabilities must be an array")
    capability_values = cast(list[object], raw_capabilities)
    if not capability_values:
        raise AgentCoreRuntimeValidationError("allowed_capabilities cannot be empty")
    if len(capability_values) > MAX_AGENT_ALLOWED_CAPABILITIES:
        raise AgentCoreRuntimeValidationError("allowed_capabilities exceed the v1 limit")
    if any(type(item) is not str for item in capability_values):
        raise AgentCoreRuntimeValidationError(
            "allowed_capabilities must contain only strings"
        )

    capabilities: list[AgentCapability] = []
    for item in cast(list[str], capability_values):
        try:
            capabilities.append(AgentCapability(item))
        except ValueError as exc:
            raise AgentCoreRuntimeValidationError(
                "allowed_capabilities contains an unsupported capability"
            ) from exc
    if len(set(capabilities)) != len(capabilities):
        raise AgentCoreRuntimeValidationError(
            "allowed_capabilities cannot contain duplicates"
        )

    try:
        return create_single_agent_task(
            text=task_text,
            allowed_capabilities=tuple(capabilities),
        )
    except ValueError as exc:
        raise AgentCoreRuntimeValidationError(
            "runtime request violates the existing SingleAgentTask contract"
        ) from exc


def handle_agentcore_runtime_invocation(
    *,
    raw_body: bytes,
    model: AgentReasoningModel,
) -> AgentCoreReasoningProjection:
    """Admit one request, reason exactly once, authorize deterministically, then stop."""
    task = admit_agentcore_runtime_request(raw_body)
    result = reason_about_task(task=task, model=model)
    return AgentCoreReasoningProjection.create(result)


__all__ = [
    "admit_agentcore_runtime_request",
    "handle_agentcore_runtime_invocation",
]
