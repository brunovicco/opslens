"""Measured replay contract for the bounded AgentCore Runtime experiment."""

from __future__ import annotations

import json
import re
import time
from collections.abc import Mapping
from hashlib import sha256
from typing import Protocol, cast, runtime_checkable

from opslens.agent_baseline.domain.reasoning_evaluation import (
    AgentReasoningEvaluationCase,
    AgentReasoningEvaluationDataset,
)

AGENTCORE_RUNTIME_REPLAY_ARTIFACT_VERSION = "agentcore-runtime-replay:v1"
PHASE11_REFERENCE_CORPUS_SHA256 = (
    "3501237bcc8fac320db7e4583892a1dcaf182015e04b28ca585ef0509c7f36bc"
)
_EXPECTED_CASE_COUNT = 6
_APPLICATION_JSON = "application/json"
_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$", re.ASCII)


class AgentCoreRuntimeReplayError(RuntimeError):
    """Raised when authenticated runtime replay evidence violates the frozen contract."""


@runtime_checkable
class _ReadableBody(Protocol):
    """Minimum SDK response body surface required by the replay."""

    def read(self) -> bytes:
        """Read the complete response body."""
        ...

    def close(self) -> None:
        """Close the response body."""
        ...


class AgentCoreRuntimeInvokeClient(Protocol):
    """Narrow data-plane client allowed to invoke one AgentCore Runtime."""

    def invoke_agent_runtime(
        self,
        *,
        agentRuntimeArn: str,
        runtimeSessionId: str,
        payload: bytes,
        contentType: str,
        accept: str,
    ) -> Mapping[str, object]:
        """Invoke one authenticated Runtime request."""
        ...


def _canonical_json(value: object) -> bytes:
    """Serialize one deterministic replay identity payload."""
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _canonical_sha256(value: object) -> str:
    """Hash one canonical replay identity payload."""
    return sha256(_canonical_json(value)).hexdigest()


def _require_string(mapping: Mapping[str, object], key: str) -> str:
    value = mapping.get(key)
    if type(value) is not str or not value:
        raise AgentCoreRuntimeReplayError(f"runtime response {key} must be a non-empty string")
    return value


def _require_int(mapping: Mapping[str, object], key: str) -> int:
    value = mapping.get(key)
    if type(value) is not int:
        raise AgentCoreRuntimeReplayError(f"runtime response {key} must be an integer")
    return value


def _response_bytes(response: Mapping[str, object]) -> bytes:
    body = response.get("response")
    if type(body) is bytes:
        return body
    if not isinstance(body, _ReadableBody):
        raise AgentCoreRuntimeReplayError("runtime response is missing a readable response body")
    try:
        raw = body.read()
    finally:
        body.close()
    if type(raw) is not bytes:
        raise AgentCoreRuntimeReplayError("runtime response body must resolve to bytes")
    return raw


def _response_json(response: Mapping[str, object]) -> Mapping[str, object]:
    raw = _response_bytes(response)
    try:
        loaded: object = json.loads(raw.decode("utf-8", errors="strict"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AgentCoreRuntimeReplayError("runtime response must be valid UTF-8 JSON") from exc
    if not isinstance(loaded, Mapping):
        raise AgentCoreRuntimeReplayError("runtime response JSON must contain one object")
    return cast(Mapping[str, object], loaded)


def _session_id(*, source_head_sha: str, replay_run_id: str, case_key: str) -> str:
    digest = sha256(f"{source_head_sha}:{replay_run_id}:{case_key}".encode()).hexdigest()
    return f"opslens-phase14-replay-{digest}"


def _validate_replay_inputs(
    *,
    runtime_arn: str,
    source_head_sha: str,
    replay_run_id: str,
    dataset: AgentReasoningEvaluationDataset,
) -> None:
    if type(runtime_arn) is not str or not runtime_arn.strip():
        raise AgentCoreRuntimeReplayError("runtime_arn must be a non-empty string")
    if type(source_head_sha) is not str or _SHA_PATTERN.fullmatch(source_head_sha) is None:
        raise AgentCoreRuntimeReplayError("source_head_sha must be one exact Git commit SHA")
    if type(replay_run_id) is not str or not replay_run_id.strip():
        raise AgentCoreRuntimeReplayError("replay_run_id must be a non-empty string")
    if type(dataset) is not AgentReasoningEvaluationDataset:
        raise AgentCoreRuntimeReplayError("dataset must be an admitted reasoning evaluation dataset")
    if dataset.corpus_sha256 != PHASE11_REFERENCE_CORPUS_SHA256:
        raise AgentCoreRuntimeReplayError("Phase 11 reference corpus identity has drifted")
    if len(dataset.cases) != _EXPECTED_CASE_COUNT:
        raise AgentCoreRuntimeReplayError("Phase 11 reference corpus must contain exactly six cases")


def _request_payload(case: AgentReasoningEvaluationCase) -> bytes:
    """Project one frozen Phase 11 task into the AgentCore runtime request contract."""
    return _canonical_json(
        {
            "allowed_capabilities": [item.value for item in case.task.allowed_capabilities],
            "task_text": case.task.text,
        }
    )


def _score_case(
    *,
    case: AgentReasoningEvaluationCase,
    payload: Mapping[str, object],
) -> dict[str, bool]:
    """Score runtime output against the existing deterministic Phase 11 expectation."""
    expected_capability = (
        case.expectation.capability.value if case.expectation.capability is not None else None
    )
    actual_decision = payload.get("decision")
    actual_capability = payload.get("capability")
    actual_authorization = payload.get("authorization_outcome")
    invocation_evidence = payload.get("invocation_evidence")
    if not isinstance(invocation_evidence, Mapping):
        raise AgentCoreRuntimeReplayError("successful runtime response lacks invocation_evidence")
    typed_evidence = cast(Mapping[str, object], invocation_evidence)
    retry_attempts = typed_evidence.get("retry_attempts")
    if type(retry_attempts) is not int:
        raise AgentCoreRuntimeReplayError("invocation_evidence retry_attempts must be an integer")

    decision_match = actual_decision == case.expectation.decision.value
    capability_match = actual_capability == expected_capability
    authorization_match = actual_authorization == case.expectation.authorization_outcome.value
    bounds_compliant = retry_attempts == 0
    passed = decision_match and capability_match and authorization_match and bounds_compliant

    return {
        "authorization_match": authorization_match,
        "bounds_compliant": bounds_compliant,
        "capability_match": capability_match,
        "decision_match": decision_match,
        "passed": passed,
    }


def execute_agentcore_runtime_replay(
    *,
    client: AgentCoreRuntimeInvokeClient,
    runtime_arn: str,
    source_head_sha: str,
    replay_run_id: str,
    dataset: AgentReasoningEvaluationDataset,
) -> dict[str, object]:
    """Replay the unchanged Phase 11 corpus through one authenticated Runtime boundary."""
    _validate_replay_inputs(
        runtime_arn=runtime_arn,
        source_head_sha=source_head_sha,
        replay_run_id=replay_run_id,
        dataset=dataset,
    )

    observations: list[dict[str, object]] = []
    total_transport_elapsed_ms = 0
    input_tokens = 0
    output_tokens = 0
    total_tokens = 0
    sdk_retry_attempts = 0
    passed_cases = 0

    for case in dataset.cases:
        session_id = _session_id(
            source_head_sha=source_head_sha,
            replay_run_id=replay_run_id,
            case_key=case.case_key,
        )
        started = time.perf_counter()
        response = client.invoke_agent_runtime(
            agentRuntimeArn=runtime_arn,
            runtimeSessionId=session_id,
            payload=_request_payload(case),
            contentType=_APPLICATION_JSON,
            accept=_APPLICATION_JSON,
        )
        elapsed_ms = round((time.perf_counter() - started) * 1000)
        total_transport_elapsed_ms += elapsed_ms

        status_code = _require_int(response, "statusCode")
        if status_code != 200:
            raise AgentCoreRuntimeReplayError(
                f"case {case.case_key} returned unexpected runtime status {status_code}"
            )
        content_type = _require_string(response, "contentType")
        if not content_type.startswith(_APPLICATION_JSON):
            raise AgentCoreRuntimeReplayError(
                f"case {case.case_key} returned unexpected content type {content_type}"
            )
        returned_session_id = _require_string(response, "runtimeSessionId")
        if returned_session_id != session_id:
            raise AgentCoreRuntimeReplayError(
                f"case {case.case_key} returned a different runtime session identity"
            )

        payload = _response_json(response)
        score = _score_case(case=case, payload=payload)
        if score["passed"]:
            passed_cases += 1

        invocation_evidence = payload.get("invocation_evidence")
        if not isinstance(invocation_evidence, Mapping):
            raise AgentCoreRuntimeReplayError("successful runtime response lacks invocation_evidence")
        typed_evidence = cast(Mapping[str, object], invocation_evidence)
        for key in ("input_tokens", "output_tokens", "total_tokens", "retry_attempts"):
            if type(typed_evidence.get(key)) is not int:
                raise AgentCoreRuntimeReplayError(
                    f"case {case.case_key} invocation_evidence {key} must be an integer"
                )
        input_tokens += cast(int, typed_evidence["input_tokens"])
        output_tokens += cast(int, typed_evidence["output_tokens"])
        total_tokens += cast(int, typed_evidence["total_tokens"])
        sdk_retry_attempts += cast(int, typed_evidence["retry_attempts"])

        observations.append(
            {
                "case_key": case.case_key,
                "runtime_session_id": session_id,
                "transport_elapsed_ms": elapsed_ms,
                "status_code": status_code,
                "projection": payload,
                "score": score,
            }
        )

    metrics = {
        "passed_cases": passed_cases,
        "total_cases": len(dataset.cases),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "sdk_retry_attempts_sum": sdk_retry_attempts,
        "transport_elapsed_ms_sum": total_transport_elapsed_ms,
    }
    report_identity = {
        "artifact_version": AGENTCORE_RUNTIME_REPLAY_ARTIFACT_VERSION,
        "corpus_sha256": dataset.corpus_sha256,
        "metrics": metrics,
        "observations": observations,
        "replay_run_id": replay_run_id,
        "runtime_arn": runtime_arn,
        "source_head_sha": source_head_sha,
    }
    digest = _canonical_sha256(report_identity)
    return {
        **report_identity,
        "capability_executions": 0,
        "report_sha256": digest,
        "report_id": f"{AGENTCORE_RUNTIME_REPLAY_ARTIFACT_VERSION}:report:{digest}",
    }


__all__ = [
    "AGENTCORE_RUNTIME_REPLAY_ARTIFACT_VERSION",
    "PHASE11_REFERENCE_CORPUS_SHA256",
    "AgentCoreRuntimeInvokeClient",
    "AgentCoreRuntimeReplayError",
    "execute_agentcore_runtime_replay",
]
