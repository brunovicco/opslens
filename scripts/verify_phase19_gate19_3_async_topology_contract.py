#!/usr/bin/env python3
"""Verify the Gate 19.3 concrete async topology contract without AWS access."""

import json
from hashlib import sha256
from pathlib import Path
from typing import cast

_ARTIFACT = Path("labs/evidence/phase-19-gate-19-3-async-topology-contract-v1.json")
_GATE19_2_LIVE = Path("labs/evidence/phase-19-gate-19-2-live-measurement-v1.json")
_GATE19_2_CLOSEOUT = Path("labs/evidence/phase-19-gate-19-2-closeout-v1.json")
_EXPECTED_SOURCE_MAIN_SHA = "71eda2650889d3047259d37be226862ed2a09092"
_EXPECTED_LIVE_SHA256 = "04ab754a12e25c4aeda0075d41b92693fec464aec4431b3734981488ff470114"
_EXPECTED_DECISION = "HTTP_API_LAMBDA_SQS_LAMBDA_DYNAMODB"
_EXPECTED_GATE19_2_DECISION = "ASYNC_SUBMIT_STATUS_RESULT"

_EXPECTED_STATES = {
    "SUBMITTING",
    "ACCEPTED",
    "RUNNING",
    "SUCCEEDED",
    "FAILED",
    "EXPIRED",
}

_EXPECTED_TRANSITIONS = {
    "SUBMITTING->ACCEPTED",
    "SUBMITTING->RUNNING",
    "SUBMITTING->FAILED",
    "ACCEPTED->RUNNING",
    "ACCEPTED->FAILED",
    "RUNNING->RUNNING",
    "RUNNING->SUCCEEDED",
    "RUNNING->FAILED",
    "SUBMITTING->EXPIRED",
    "ACCEPTED->EXPIRED",
    "RUNNING->EXPIRED",
    "SUCCEEDED->EXPIRED",
    "FAILED->EXPIRED",
}

_EXPECTED_CANDIDATES = {
    "HTTP_API_LAMBDA_SQS_LAMBDA_DYNAMODB": "SELECTED",
    "HTTP_API_LAMBDA_DYNAMODB_STREAMS_LAMBDA": "REJECTED",
    "HTTP_API_LAMBDA_STEP_FUNCTIONS_STANDARD_LAMBDA": "REJECTED",
    "FUNCTION_URL_LAMBDA_SQS_LAMBDA_DYNAMODB": "REJECTED",
    "HTTP_API_LAMBDA_SQS_FARGATE_DYNAMODB": "REJECTED",
}

_EXPECTED_SERVICES = {
    "ingress": "Amazon API Gateway HTTP API",
    "api_handler": "AWS Lambda",
    "job_queue": "Amazon SQS standard queue",
    "dead_letter_queue": "Amazon SQS standard queue",
    "worker": "AWS Lambda",
    "job_store": "Amazon DynamoDB",
}

_EXPECTED_API_ACTIONS = {
    "sqs:SendMessage",
    "dynamodb:GetItem",
    "dynamodb:PutItem",
    "dynamodb:UpdateItem",
    "dynamodb:TransactWriteItems",
}

_EXPECTED_WORKER_ACTIONS = {
    "sqs:ReceiveMessage",
    "sqs:DeleteMessage",
    "sqs:ChangeMessageVisibility",
    "sqs:GetQueueAttributes",
    "dynamodb:GetItem",
    "dynamodb:UpdateItem",
    "bedrock:Retrieve",
    "bedrock:InvokeModel",
}

_EXPECTED_OBSERVABILITY = {
    "request_id",
    "job_id",
    "trace_id",
    "state_transition",
    "attempt_number",
    "stage",
    "duration_ms",
    "outcome",
    "failure_category",
    "provider_service_call_count",
    "bedrock_input_tokens_when_available",
    "bedrock_output_tokens_when_available",
    "retry_count",
    "throttle_count",
    "queue_age_ms",
    "result_bytes",
}

_EXPECTED_FORBIDDEN_TELEMETRY = {
    "full_prompt",
    "repository_source_code",
    "repository_file_contents",
    "full_model_response",
    "credentials",
    "raw_user_payload",
}

_EXPECTED_DISABLE_CONTROLS = {
    "disable_new_submit_route",
    "disable_queue_event_source_mapping",
    "set_worker_reserved_concurrency_to_zero",
    "disable_model_invocation_in_worker_policy_or_runtime_guard",
    "preserve_status_result_reads_during_submit_pause",
}


class Gate19_3TopologyVerificationError(ValueError):
    """Reject contradictory or drifted Gate 19.3 design evidence."""


def _object(value: object, *, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise Gate19_3TopologyVerificationError(f"{label} must be a JSON object")
    return cast(dict[str, object], value)


def _objects(value: object, *, label: str) -> list[dict[str, object]]:
    if not isinstance(value, list):
        raise Gate19_3TopologyVerificationError(f"{label} must be a JSON array")
    result: list[dict[str, object]] = []
    for index, item in enumerate(cast(list[object], value)):
        result.append(_object(item, label=f"{label}[{index}]"))
    return result


def _strings(value: object, *, label: str) -> list[str]:
    if not isinstance(value, list):
        raise Gate19_3TopologyVerificationError(f"{label} must be a string array")
    values = cast(list[object], value)
    if any(not isinstance(item, str) for item in values):
        raise Gate19_3TopologyVerificationError(f"{label} must be a string array")
    return cast(list[str], values)


def _string(value: object, *, label: str) -> str:
    if not isinstance(value, str):
        raise Gate19_3TopologyVerificationError(f"{label} must be a string")
    return value


def _integer(value: object, *, label: str) -> int:
    if type(value) is not int:
        raise Gate19_3TopologyVerificationError(f"{label} must be an integer")
    return value


def _boolean(value: object, *, label: str) -> bool:
    if type(value) is not bool:
        raise Gate19_3TopologyVerificationError(f"{label} must be a boolean")
    return value


def _load(path: Path) -> dict[str, object]:
    try:
        parsed = cast(object, json.loads(path.read_text(encoding="utf-8")))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Gate19_3TopologyVerificationError(f"could not load {path}") from exc
    return _object(parsed, label=str(path))


def _require_exact_keys(
    value: dict[str, object], *, expected: set[str], label: str
) -> None:
    if set(value) != expected:
        raise Gate19_3TopologyVerificationError(
            f"{label} must preserve the exact frozen field set"
        )


def _verify_source_evidence(repo_root: Path, root: dict[str, object]) -> dict[str, object]:
    live_path = repo_root / _GATE19_2_LIVE
    try:
        live_bytes = live_path.read_bytes()
    except OSError as exc:
        raise Gate19_3TopologyVerificationError("Gate 19.2 live artifact is missing") from exc

    if sha256(live_bytes).hexdigest() != _EXPECTED_LIVE_SHA256:
        raise Gate19_3TopologyVerificationError("Gate 19.2 live artifact bytes drifted")

    live = _object(json.loads(live_bytes), label="Gate 19.2 live artifact")
    closeout = _load(repo_root / _GATE19_2_CLOSEOUT)

    if closeout.get("decision") != _EXPECTED_GATE19_2_DECISION:
        raise Gate19_3TopologyVerificationError("Gate 19.2 interaction decision drifted")
    authorization = _object(closeout.get("authorization"), label="Gate 19.2 authorization")
    if authorization.get("concrete_aws_topology_selected") is not False:
        raise Gate19_3TopologyVerificationError(
            "Gate 19.3 must start from an unselected concrete topology"
        )
    if authorization.get("public_runtime_deployment_authorized") is not False:
        raise Gate19_3TopologyVerificationError(
            "Gate 19.2 must not authorize public deployment"
        )

    if root.get("source_main_sha") != _EXPECTED_SOURCE_MAIN_SHA:
        raise Gate19_3TopologyVerificationError("Gate 19.3 source main SHA drifted")
    if root.get("source_gate_19_2_live_artifact_sha256") != _EXPECTED_LIVE_SHA256:
        raise Gate19_3TopologyVerificationError("Gate 19.3 source live SHA drifted")
    if root.get("source_gate_19_2_decision") != _EXPECTED_GATE19_2_DECISION:
        raise Gate19_3TopologyVerificationError("Gate 19.3 source decision drifted")

    return live


def _verify_identity(root: dict[str, object]) -> None:
    expected: dict[str, object] = {
        "artifact_type": "phase-19-gate-19-3-async-topology-contract:v1",
        "schema_version": 1,
        "phase": 19,
        "gate": "19.3",
        "issue": 348,
        "source_main_sha": _EXPECTED_SOURCE_MAIN_SHA,
        "source_gate_19_2_pr": 347,
        "source_gate_19_2_live_artifact_sha256": _EXPECTED_LIVE_SHA256,
        "source_gate_19_2_decision": _EXPECTED_GATE19_2_DECISION,
        "status": "DESIGN_SELECTED_NO_DEPLOYMENT",
        "decision": _EXPECTED_DECISION,
        "deployment_authorized": False,
    }
    for field, expected_value in expected.items():
        if root.get(field) != expected_value:
            raise Gate19_3TopologyVerificationError(
                f"Gate 19.3 identity drifted at {field}"
            )

    authority = _object(root.get("authority_impact"), label="authority_impact")
    expected_authority = {
        "public_endpoints_created": 0,
        "new_aws_resources_created": 0,
        "new_iam_roles_or_policies_created": 0,
        "aws_or_provider_live_executions": 0,
        "third_party_repository_code_executions": 0,
        "pr_89_modifications": 0,
    }
    if authority != expected_authority:
        raise Gate19_3TopologyVerificationError("Gate 19.3 acquired runtime authority")


def _verify_measured_basis(root: dict[str, object], live: dict[str, object]) -> None:
    measured = _object(root.get("measured_basis"), label="measured_basis")
    if measured.get("classification") != "MEASURED":
        raise Gate19_3TopologyVerificationError("measured basis lost MEASURED classification")

    provider_totals = {
        _string(item.get("metric"), label="provider metric"): _integer(
            item.get("value"), label="provider value"
        )
        for item in _objects(live.get("provider_totals"), label="provider_totals")
    }
    provider_classifications = {
        _string(item.get("metric"), label="classification metric"): _string(
            item.get("classification"), label="classification value"
        )
        for item in _objects(
            live.get("provider_classifications"), label="provider_classifications"
        )
    }

    expected_values = {
        "end_to_end_duration_ms": _integer(
            live.get("end_to_end_duration_ms"), label="live.end_to_end_duration_ms"
        ),
        "serialized_result_bytes": _integer(
            live.get("serialized_result_bytes"), label="live.serialized_result_bytes"
        ),
        "github_http_request_count": provider_totals["github_http_request_count"],
        "bedrock_retrieve_client_elapsed_ms": provider_totals[
            "bedrock_retrieve_client_elapsed_ms"
        ],
        "bedrock_model_client_elapsed_ms": provider_totals[
            "bedrock_model_client_elapsed_ms"
        ],
        "bedrock_model_latency_ms": provider_totals["bedrock_model_latency_ms"],
        "bedrock_input_tokens": provider_totals["bedrock_input_tokens"],
        "bedrock_output_tokens": provider_totals["bedrock_output_tokens"],
        "retry_count": provider_totals["retry_count"],
    }
    for field, expected_value in expected_values.items():
        if _integer(measured.get(field), label=f"measured_basis.{field}") != expected_value:
            raise Gate19_3TopologyVerificationError(
                f"Gate 19.3 measured basis contradicts live evidence at {field}"
            )

    if measured.get("throttle_count_classification") != "UNMEASURED":
        raise Gate19_3TopologyVerificationError("throttle count must remain UNMEASURED")
    if provider_classifications.get("throttle_count") != "UNMEASURED":
        raise Gate19_3TopologyVerificationError(
            "Gate 19.2 throttle classification no longer matches"
        )


def _verify_interaction_and_lifecycle(root: dict[str, object]) -> None:
    interaction = _object(root.get("interaction_contract"), label="interaction_contract")
    submit = _object(interaction.get("submit"), label="interaction_contract.submit")
    if submit != {
        "method": "POST",
        "path": "/v1/analyses",
        "success_status": 202,
        "returns": ["job_id", "status_url", "result_url"],
    }:
        raise Gate19_3TopologyVerificationError("submit contract drifted")

    status = _object(interaction.get("status"), label="interaction_contract.status")
    if status.get("method") != "GET" or status.get("path") != "/v1/analyses/{job_id}":
        raise Gate19_3TopologyVerificationError("status route drifted")
    if set(_strings(status.get("states"), label="status.states")) != _EXPECTED_STATES:
        raise Gate19_3TopologyVerificationError("job state vocabulary drifted")

    result = _object(interaction.get("result"), label="interaction_contract.result")
    if result != {
        "method": "GET",
        "path": "/v1/analyses/{job_id}/result",
        "available_only_when": "SUCCEEDED",
        "expired_status": 410,
    }:
        raise Gate19_3TopologyVerificationError("result contract drifted")

    lifecycle = _object(root.get("job_lifecycle"), label="job_lifecycle")
    if lifecycle.get("initial_state") != "SUBMITTING":
        raise Gate19_3TopologyVerificationError("initial state drifted")
    if set(_strings(lifecycle.get("terminal_states"), label="terminal_states")) != {
        "SUCCEEDED",
        "FAILED",
        "EXPIRED",
    }:
        raise Gate19_3TopologyVerificationError("terminal states drifted")
    if set(_strings(lifecycle.get("allowed_transitions"), label="allowed_transitions")) != (
        _EXPECTED_TRANSITIONS
    ):
        raise Gate19_3TopologyVerificationError("allowed lifecycle transitions drifted")
    if lifecycle.get("state_authority") != "DYNAMODB_CONDITIONAL_WRITE":
        raise Gate19_3TopologyVerificationError("state authority drifted")
    if lifecycle.get("result_authority") != "ADMITTED_SERIALIZED_RESULT_ONLY":
        raise Gate19_3TopologyVerificationError("result authority drifted")


def _verify_idempotency_and_delivery(root: dict[str, object]) -> None:
    idempotency = _object(root.get("idempotency_contract"), label="idempotency_contract")
    expected_idempotency = {
        "required_header": "Idempotency-Key",
        "request_fingerprint": "SHA256_CANONICAL_PUBLIC_ANALYSIS_REQUEST_V1",
        "same_key_same_fingerprint": "RETURN_EXISTING_JOB",
        "same_key_different_fingerprint": "HTTP_409",
        "storage": "SAME_DYNAMODB_TABLE",
        "write_authority": "CONDITIONAL_OR_TRANSACTIONAL_WRITE",
    }
    if idempotency != expected_idempotency:
        raise Gate19_3TopologyVerificationError("idempotency contract drifted")

    delivery = _object(root.get("delivery_contract"), label="delivery_contract")
    if delivery.get("queue_semantics") != "AT_LEAST_ONCE":
        raise Gate19_3TopologyVerificationError("queue semantics drifted")
    if _integer(delivery.get("batch_size"), label="delivery.batch_size") != 1:
        raise Gate19_3TopologyVerificationError("worker batch size drifted")
    if delivery.get("duplicate_handling") != (
        "DYNAMODB_CONDITIONAL_STATE_AND_ATTEMPT_ADMISSION"
    ):
        raise Gate19_3TopologyVerificationError("duplicate handling drifted")
    if _boolean(delivery.get("dead_letter_queue_required"), label="dlq required") is not True:
        raise Gate19_3TopologyVerificationError("DLQ requirement drifted")
    if _boolean(delivery.get("automatic_unbounded_retry"), label="unbounded retry"):
        raise Gate19_3TopologyVerificationError("unbounded retry became authorized")
    if delivery.get("backpressure_authority") != (
        "SQS_QUEUE_DEPTH_PLUS_LAMBDA_RESERVED_CONCURRENCY"
    ):
        raise Gate19_3TopologyVerificationError("backpressure authority drifted")


def _verify_topology(root: dict[str, object]) -> None:
    topology = _object(root.get("selected_topology"), label="selected_topology")
    if set(topology) != set(_EXPECTED_SERVICES):
        raise Gate19_3TopologyVerificationError("selected topology component set drifted")
    for component, expected_service in _EXPECTED_SERVICES.items():
        item = _object(topology.get(component), label=f"selected_topology.{component}")
        if item.get("service") != expected_service:
            raise Gate19_3TopologyVerificationError(
                f"selected service drifted for {component}"
            )
        if not _string(item.get("responsibility"), label=f"{component}.responsibility"):
            raise Gate19_3TopologyVerificationError(
                f"responsibility missing for {component}"
            )
        if not _string(item.get("why_selected"), label=f"{component}.why_selected"):
            raise Gate19_3TopologyVerificationError(
                f"selection reason missing for {component}"
            )

    candidates = _objects(root.get("candidate_topologies"), label="candidate_topologies")
    by_id = {
        _string(item.get("id"), label="candidate.id"): _string(
            item.get("status"), label="candidate.status"
        )
        for item in candidates
    }
    if by_id != _EXPECTED_CANDIDATES or len(by_id) != len(candidates):
        raise Gate19_3TopologyVerificationError("candidate topology matrix drifted")


def _verify_iam(root: dict[str, object]) -> None:
    rows = _objects(
        root.get("iam_responsibility_contract"), label="iam_responsibility_contract"
    )
    by_principal = {
        _string(row.get("principal"), label="iam principal"): row for row in rows
    }
    if set(by_principal) != {"api_handler_role", "worker_role"} or len(rows) != 2:
        raise Gate19_3TopologyVerificationError("IAM responsibility split drifted")

    api_actions = set(
        _strings(by_principal["api_handler_role"].get("allowed_actions"), label="api actions")
    )
    if api_actions != _EXPECTED_API_ACTIONS:
        raise Gate19_3TopologyVerificationError("API handler IAM actions drifted")
    api_forbidden = set(
        _strings(
            by_principal["api_handler_role"].get("explicitly_forbidden"),
            label="api forbidden actions",
        )
    )
    if not {"bedrock:InvokeModel", "bedrock:Retrieve", "sqs:ReceiveMessage"}.issubset(
        api_forbidden
    ):
        raise Gate19_3TopologyVerificationError("API handler gained worker authority")

    worker_actions = set(
        _strings(by_principal["worker_role"].get("allowed_actions"), label="worker actions")
    )
    if worker_actions != _EXPECTED_WORKER_ACTIONS:
        raise Gate19_3TopologyVerificationError("worker IAM actions drifted")
    if "iam:*" not in set(
        _strings(
            by_principal["worker_role"].get("explicitly_forbidden"),
            label="worker forbidden actions",
        )
    ):
        raise Gate19_3TopologyVerificationError("worker IAM wildcard prohibition drifted")


def _verify_observability_and_recovery(root: dict[str, object]) -> None:
    observability = _object(
        root.get("observability_contract"), label="observability_contract"
    )
    if set(
        _strings(observability.get("required_fields"), label="observability.required_fields")
    ) != _EXPECTED_OBSERVABILITY:
        raise Gate19_3TopologyVerificationError("observability field contract drifted")
    if set(
        _strings(observability.get("forbidden_fields"), label="observability.forbidden_fields")
    ) != _EXPECTED_FORBIDDEN_TELEMETRY:
        raise Gate19_3TopologyVerificationError("telemetry minimization contract drifted")

    recovery = _object(
        root.get("disable_recovery_contract"), label="disable_recovery_contract"
    )
    if set(_strings(recovery.get("controls"), label="disable controls")) != (
        _EXPECTED_DISABLE_CONTROLS
    ):
        raise Gate19_3TopologyVerificationError("disable/recovery controls drifted")
    if _boolean(recovery.get("global_kill_switch_claimed"), label="global kill switch"):
        raise Gate19_3TopologyVerificationError("global kill switch was falsely claimed")


def main() -> int:
    """Verify the Gate 19.3 topology decision deterministically and offline."""
    repo_root = Path(__file__).resolve().parents[1]
    root = _load(repo_root / _ARTIFACT)

    _require_exact_keys(
        root,
        expected={
            "artifact_type",
            "schema_version",
            "phase",
            "gate",
            "issue",
            "source_main_sha",
            "source_gate_19_2_pr",
            "source_gate_19_2_live_artifact_sha256",
            "source_gate_19_2_decision",
            "status",
            "decision",
            "deployment_authorized",
            "authority_impact",
            "measured_basis",
            "interaction_contract",
            "job_lifecycle",
            "idempotency_contract",
            "delivery_contract",
            "selected_topology",
            "candidate_topologies",
            "iam_responsibility_contract",
            "observability_contract",
            "disable_recovery_contract",
            "next_boundary",
        },
        label="Gate 19.3 artifact",
    )

    live = _verify_source_evidence(repo_root, root)
    _verify_identity(root)
    _verify_measured_basis(root, live)
    _verify_interaction_and_lifecycle(root)
    _verify_idempotency_and_delivery(root)
    _verify_topology(root)
    _verify_iam(root)
    _verify_observability_and_recovery(root)

    print(
        "phase19_gate19_3_topology_contract=PASS "
        f"decision={_EXPECTED_DECISION} "
        "interaction=ASYNC_SUBMIT_STATUS_RESULT "
        "deployment_authorized=false "
        "public_endpoints_created=0 new_aws_resources_created=0 "
        "new_iam_roles_or_policies_created=0 provider_live_executions=0"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
