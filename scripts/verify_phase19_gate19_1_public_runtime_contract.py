#!/usr/bin/env python3
"""Verify the frozen Gate 19.1 public-runtime launch contract without AWS access."""

import argparse
import json
from pathlib import Path
from typing import cast

_ARTIFACT = Path("labs/evidence/phase-19-gate-19-1-public-runtime-contract-v1.json")
_PHASE18 = Path("labs/evidence/phase-18-closeout-v1.json")

_EXPECTED_CLASSIFICATIONS = {
    "MEASURED",
    "DERIVED",
    "UNMEASURED",
    "NOT_APPLICABLE",
    "CONFIGURED_LIMIT",
}

_EXPECTED_PIPELINE_STAGES = {
    "public_request_admission",
    "repository_acquisition",
    "dependency_evidence",
    "vulnerability_correlation",
    "risk_prioritization",
    "structured_evidence",
    "semantic_evidence",
    "model_reasoning",
    "result_admission",
    "http_transport",
}

_EXPECTED_REQUIRED_EVIDENCE = {
    "remediation_guidance",
    "risk_priority",
    "vulnerability_facts",
}

_EXPECTED_THREATS = {
    "oversized_request",
    "malformed_json",
    "repository_url_abuse",
    "ssrf_style_source_redirection",
    "repository_enumeration",
    "large_repository_amplification",
    "dependency_explosion",
    "github_api_abuse",
    "prompt_injection_from_repository_content",
    "retrieval_poisoning",
    "model_amplification",
    "athena_scan_amplification",
    "bedrock_token_amplification",
    "retry_amplification",
    "concurrency_exhaustion",
    "cost_denial_of_wallet",
    "result_tampering",
    "identity_replay",
    "telemetry_data_leakage",
}

_EXPECTED_IAM_RESPONSIBILITIES = {
    "public_ingress",
    "repository_acquisition",
    "athena_structured_retrieval",
    "bedrock_knowledge_retrieval",
    "bedrock_model_invocation",
    "result_persistence",
    "telemetry_emission",
    "async_queue_job_coordination",
}

_REQUIRED_OBSERVABILITY = {
    "request_id",
    "trace_id",
    "workload_id",
    "repository_identity_hash",
    "stage",
    "duration_ms",
    "outcome",
    "failure_category",
    "provider_service_call_count",
    "bedrock_input_tokens_when_available",
    "bedrock_output_tokens_when_available",
    "athena_bytes_scanned",
    "retry_count",
    "throttle_count",
    "admission_rejection_reason",
    "cost_attribution_identifier_when_available",
}

_FORBIDDEN_TELEMETRY = {
    "full_prompt",
    "repository_source_code",
    "repository_file_contents",
    "full_model_response",
    "sensitive_tokens",
    "credentials",
    "raw_user_payload",
}

_EXPECTED_DISABLE_CONTROLS = {
    "ingress_disable",
    "new_job_admission_disable",
    "queue_consumer_pause",
    "model_invocation_disable",
    "athena_execution_disable",
    "background_ingestion_pause",
}

_REQUIRED_GATE19_2_MEASUREMENTS = {
    "end_to_end_duration_ms",
    "stage_duration_ms",
    "github_http_request_count",
    "athena_query_count_and_bytes_scanned_if_used",
    "bedrock_retrieve_count_and_latency_if_used",
    "bedrock_model_call_count_tokens_latency_if_used",
    "retry_and_throttle_counts",
    "serialized_result_bytes",
}

_REQUIRED_LIVE_DOC_MARKERS = {
    "README.md": (
        "Phases 0\u201318 are complete.",
        "Phase 19 — Bounded Public Runtime & Productization",
        "DEFERRED_PENDING_MEASUREMENT",
    ),
    "README.pt-br.md": (
        "Phases 0\u201318 estão completas.",
        "Phase 19 — Bounded Public Runtime & Productization",
        "DEFERRED_PENDING_MEASUREMENT",
    ),
    "docs/current-state.md": (
        "Phase 18",
        "COMPLETE",
        "Gate 19.1",
        "DEFERRED_PENDING_MEASUREMENT",
        "PublicAnalysisAdmissionHandoff",
    ),
    "docs/roadmap.md": (
        "Phase 19 — Bounded Public Runtime & Productization",
        "Gate 19.1",
        "DEFERRED_PENDING_MEASUREMENT",
        "Gate 19.2",
    ),
    "docs/architecture.md": (
        "Phase 19 — Bounded Public Runtime & Productization",
        "public-analysis-workload:v1",
        "DEFERRED_PENDING_MEASUREMENT",
    ),
    "docs/architecture.pt-br.md": (
        "Phase 19 — Bounded Public Runtime & Productization",
        "public-analysis-workload:v1",
        "DEFERRED_PENDING_MEASUREMENT",
    ),
}

_FORBIDDEN_LIVE_DOC_MARKERS = (
    "Phase 18 complete pending Gate 18.5 merge",
    "Gate 18.5 IN PROGRESS",
    "Phase 18 evidence-backed closeout          IN PROGRESS",
    "Phase 18 evidence-backed closeout           IN PROGRESS",
    "Gate 18.5 — Phase 18 closeout — IN PROGRESS",
    "Gate 18.5 — Phase 18 closeout                               IN PROGRESS",
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    return parser


def _object(value: object, *, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise SystemExit(f"{label} must be a JSON object")
    return cast(dict[str, object], value)


def _objects(value: object, *, label: str) -> list[dict[str, object]]:
    if not isinstance(value, list):
        raise SystemExit(f"{label} must be a JSON array")
    result: list[dict[str, object]] = []
    for index, item in enumerate(cast(list[object], value)):
        result.append(_object(item, label=f"{label}[{index}]"))
    return result


def _strings(value: object, *, label: str) -> list[str]:
    if not isinstance(value, list):
        raise SystemExit(f"{label} must be a string array")
    result: list[str] = []
    for item in cast(list[object], value):
        if not isinstance(item, str):
            raise SystemExit(f"{label} must be a string array")
        result.append(item)
    return result


def _load(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    return _object(value, label=str(path))


def _classified_value(
    mapping: dict[str, object],
    field: str,
    *,
    classification: str,
    value: object,
) -> None:
    item = _object(mapping.get(field), label=field)
    if item.get("classification") != classification or item.get("value") != value:
        raise SystemExit(f"{field} drifted from the frozen classified value")


def _verify_phase18_history(repo_root: Path) -> None:
    """Prove Phase 19 did not rewrite the historical pre-merge closeout artifact."""
    historical = _load(repo_root / _PHASE18)
    if historical.get("artifact_version") != "phase-18-closeout:v1":
        raise SystemExit("Phase 18 historical closeout artifact identity drifted")
    if historical.get("source_main_sha") != "4a8e5d3d98504451cef26df4e9f274f2f9fd8dd0":
        raise SystemExit("Phase 18 historical closeout source SHA drifted")
    if historical.get("status") != "PHASE_18_COMPLETE_PENDING_GATE_18_5_PROTECTED_MERGE":
        raise SystemExit("Phase 18 historical pre-merge status was rewritten")


def _verify_identity(root: dict[str, object]) -> None:
    expected = {
        "artifact_version": "phase-19-gate-19-1-public-runtime-contract:v1",
        "workload_id": "public-analysis-workload:v1",
        "phase": 19,
        "gate": "19.1",
        "issue": 291,
        "source_main_sha": "feca774535b7d83f57c26f4e9fe7da71ce268f0f",
        "source_phase18_closeout_pr": 290,
        "source_phase18_closeout_issue": 289,
        "decision": "DEFERRED_PENDING_MEASUREMENT",
        "leading_runtime_hypothesis": "ASYNC_SUBMIT_STATUS_RESULT",
    }
    for key, expected_value in expected.items():
        if root.get(key) != expected_value:
            raise SystemExit(f"Gate 19.1 identity drifted: {key}")

    classifications = set(
        _strings(root.get("classification_vocabulary"), label="classification_vocabulary")
    )
    if classifications != _EXPECTED_CLASSIFICATIONS:
        raise SystemExit("Gate 19.1 classification vocabulary drifted")

    authority = _object(root.get("authority_impact"), label="authority_impact")
    expected_authority: dict[str, object] = {
        "aws_mutations": 0,
        "iam_mutations": 0,
        "new_aws_resources": 0,
        "model_invocations": 0,
        "capability_executions": 0,
        "public_endpoints": 0,
        "pr_89_touched": False,
    }
    if authority != expected_authority:
        raise SystemExit("Gate 19.1 authority impact drifted")


def _verify_pipeline(root: dict[str, object]) -> None:
    repository_evidence = _object(root.get("repository_evidence"), label="repository_evidence")
    closeout = _object(repository_evidence.get("phase18_closeout"), label="phase18_closeout")
    if closeout != {
        "main_sha": "feca774535b7d83f57c26f4e9fe7da71ce268f0f",
        "pr_290_merged": True,
        "issue_289_closed_completed": True,
        "historical_closeout_artifact_remains_pre_merge_evidence": True,
    }:
        raise SystemExit("Phase 18 post-merge checkpoint drifted")

    stages = _objects(repository_evidence.get("public_pipeline"), label="public_pipeline")
    by_stage = {cast(str, item.get("stage")): item for item in stages}
    if set(by_stage) != _EXPECTED_PIPELINE_STAGES or len(by_stage) != len(stages):
        raise SystemExit("Public pipeline stage inventory drifted")
    if by_stage["result_admission"].get("status") != "MISSING_PUBLIC_END_TO_END_RESULT":
        raise SystemExit("Gate 19.1 must preserve the missing final public result gap")
    if by_stage["http_transport"].get("status") != "NOT_IMPLEMENTED":
        raise SystemExit("Gate 19.1 must not claim a retained public HTTP transport")
    for stage in (
        "vulnerability_correlation",
        "risk_prioritization",
        "structured_evidence",
        "semantic_evidence",
        "model_reasoning",
    ):
        if "NOT_PUBLICLY_COMPOSED" not in cast(str, by_stage[stage].get("status")):
            raise SystemExit(f"{stage} was promoted into the public path without evidence")


def _verify_workload(root: dict[str, object]) -> None:
    workload = _object(root.get("workload"), label="workload")
    request = _object(workload.get("request"), label="workload.request")
    if request.get("contract") != "public-analysis-request:v1":
        raise SystemExit("Public request contract drifted")
    _classified_value(
        request,
        "max_body_bytes",
        classification="CONFIGURED_LIMIT",
        value=2048,
    )
    _classified_value(
        request,
        "max_repository_url_chars",
        classification="CONFIGURED_LIMIT",
        value=256,
    )

    repository = _object(workload.get("repository"), label="workload.repository")
    if repository.get("provider") != "github" or repository.get("visibility") != "public_only":
        raise SystemExit("Gate 19.1 supports only public GitHub repositories")
    if repository.get("repositories_per_request") != 1:
        raise SystemExit("Public workload repository cardinality drifted")
    if repository.get("third_party_code_execution") != "FORBIDDEN":
        raise SystemExit("Third-party repository execution became authorized")
    _classified_value(
        repository,
        "max_repository_files_read",
        classification="CONFIGURED_LIMIT",
        value=1,
    )
    _classified_value(
        repository,
        "max_dependency_records",
        classification="CONFIGURED_LIMIT",
        value=5000,
    )
    evidence_needs = set(
        _strings(workload.get("required_evidence_needs"), label="required_evidence_needs")
    )
    if evidence_needs != _EXPECTED_REQUIRED_EVIDENCE:
        raise SystemExit("Public v1 required evidence needs drifted")
    if workload.get("evidence_completeness") != "ALL_REQUIRED":
        raise SystemExit("Public v1 evidence completeness weakened")

    response = _object(workload.get("response_model"), label="response_model")
    if response.get("status") != "UNMEASURED":
        raise SystemExit("Public response model was claimed as measured")
    _classified_value(
        response,
        "max_response_bytes",
        classification="UNMEASURED",
        value=None,
    )

    latency = _object(workload.get("latency"), label="latency")
    for field in ("end_to_end_timeout_target_ms", "end_to_end_p50_ms", "end_to_end_p95_ms"):
        _classified_value(latency, field, classification="UNMEASURED", value=None)

    calls = _object(workload.get("call_envelopes"), label="call_envelopes")
    _classified_value(
        calls,
        "github_http_success_path_calls",
        classification="DERIVED",
        value=4,
    )
    _classified_value(
        calls,
        "github_http_automatic_retries",
        classification="CONFIGURED_LIMIT",
        value=0,
    )
    _classified_value(
        calls,
        "github_http_timeout_seconds_per_call",
        classification="CONFIGURED_LIMIT",
        value=10.0,
    )
    for field in (
        "athena_queries_per_public_analysis",
        "bedrock_retrieve_calls_per_public_analysis",
        "bedrock_model_calls_per_public_analysis",
        "capability_executions_per_public_analysis",
    ):
        _classified_value(calls, field, classification="UNMEASURED", value=None)

    limits = _object(workload.get("retained_component_limits"), label="retained_component_limits")
    expected_limits = {
        "athena_bytes_scanned_cutoff_per_query": 10485760,
        "semantic_planner_max_output_tokens": 256,
        "knowledge_retrieval_top_k_max": 10,
        "knowledge_context_max_utf8_bytes": 16384,
        "knowledge_synthesis_max_output_tokens": 2048,
        "ghsa_occurrences_per_repository_scan": 50000,
        "vulnerability_candidate_evaluations_per_repository_scan": 100000,
    }
    for field, value in expected_limits.items():
        _classified_value(limits, field, classification="CONFIGURED_LIMIT", value=value)


def _verify_security_and_iam(root: dict[str, object]) -> None:
    threats = set(_strings(root.get("threat_abuse_model"), label="threat_abuse_model"))
    if threats != _EXPECTED_THREATS:
        raise SystemExit("Gate 19.1 threat/abuse inventory drifted")
    controls = _object(root.get("threat_controls"), label="threat_controls")
    if set(controls) != _EXPECTED_THREATS:
        raise SystemExit("Every frozen public threat must have exactly one control statement")

    rows = _objects(root.get("iam_responsibility_matrix"), label="iam_responsibility_matrix")
    by_responsibility = {cast(str, row.get("responsibility")): row for row in rows}
    if set(by_responsibility) != _EXPECTED_IAM_RESPONSIBILITIES or len(rows) != len(
        by_responsibility
    ):
        raise SystemExit("IAM responsibility decomposition drifted")

    for row in rows:
        actions = _strings(row.get("required_service_actions"), label="required_service_actions")
        if "*" in actions or any(action.endswith(":*") for action in actions):
            raise SystemExit("Gate 19.1 IAM design cannot contain wildcard actions")
        if row.get("iam_statement") not in {
            "NOT_AUTHORIZED",
            "NONE_FOR_CURRENT_RESPONSIBILITY",
            "DESIGN_ONLY_NO_MUTATION",
        }:
            raise SystemExit("Gate 19.1 IAM matrix acquired mutation/allow authority")

    expected_athena = {
        "athena:StartQueryExecution",
        "athena:GetQueryExecution",
        "athena:GetQueryResults",
        "athena:StopQueryExecution",
    }
    athena_actions = set(
        _strings(
            by_responsibility["athena_structured_retrieval"].get("required_service_actions"),
            label="athena actions",
        )
    )
    if athena_actions != expected_athena:
        raise SystemExit("Athena runtime responsibility actions drifted")
    if _strings(
        by_responsibility["bedrock_knowledge_retrieval"].get("required_service_actions"),
        label="Bedrock Retrieve actions",
    ) != ["bedrock:Retrieve"]:
        raise SystemExit("Bedrock retrieval responsibility drifted")
    if _strings(
        by_responsibility["bedrock_model_invocation"].get("required_service_actions"),
        label="Bedrock model actions",
    ) != ["bedrock:InvokeModel"]:
        raise SystemExit("Bedrock model responsibility drifted")
    for responsibility in ("result_persistence", "async_queue_job_coordination"):
        if by_responsibility[responsibility].get("iam_statement") != "NOT_AUTHORIZED":
            raise SystemExit(f"{responsibility} became authorized before topology selection")


def _verify_operability(root: dict[str, object]) -> None:
    observability = _object(root.get("observability_contract"), label="observability_contract")
    if set(
        _strings(observability.get("required_signals"), label="required_signals")
    ) != _REQUIRED_OBSERVABILITY:
        raise SystemExit("Gate 19.1 observability signals drifted")
    if set(
        _strings(observability.get("forbidden_by_default"), label="forbidden_by_default")
    ) != _FORBIDDEN_TELEMETRY:
        raise SystemExit("Gate 19.1 telemetry minimization boundary drifted")

    disable = _objects(root.get("disable_recovery_contract"), label="disable_recovery_contract")
    by_control = {cast(str, row.get("control")): row for row in disable}
    if set(by_control) != _EXPECTED_DISABLE_CONTROLS or len(by_control) != len(disable):
        raise SystemExit("Gate 19.1 disable/recovery control set drifted")
    if by_control["background_ingestion_pause"].get("status") != "EXISTING_SEPARATE_CONTROL":
        raise SystemExit("Scheduled ingestion pause was relabeled as broader runtime authority")
    if by_control["ingress_disable"].get("current_mechanism") is not None:
        raise SystemExit("Gate 19.1 must not claim a current public ingress disable mechanism")

    experiment = _object(
        root.get("gate19_2_minimum_experiment"),
        label="gate19_2_minimum_experiment",
    )
    if experiment.get("status") != (
        "AUTHORIZED_DESIGN_ONLY_REQUIRES_HUMAN_EXECUTION_FOR_LIVE_AWS_CALLS"
    ):
        raise SystemExit("Gate 19.2 live AWS execution crossed the human boundary")
    if set(
        _strings(
            experiment.get("must_measure"),
            label="gate19_2_minimum_experiment.must_measure",
        )
    ) != _REQUIRED_GATE19_2_MEASUREMENTS:
        raise SystemExit("Gate 19.2 measurement contract drifted")
    must_not_create = set(
        _strings(
            experiment.get("must_not_create"),
            label="gate19_2_minimum_experiment.must_not_create",
        )
    )
    if "public_endpoint" not in must_not_create or "broad_runtime_role" not in must_not_create:
        raise SystemExit(
            "Gate 19.2 experiment silently authorized a public/runtime authority surface"
        )


def _verify_live_docs(repo_root: Path) -> None:
    for path_text, markers in _REQUIRED_LIVE_DOC_MARKERS.items():
        text = (repo_root / path_text).read_text(encoding="utf-8")
        for marker in markers:
            if marker not in text:
                raise SystemExit(f"{path_text} is missing Gate 19.1 marker {marker!r}")
        for marker in _FORBIDDEN_LIVE_DOC_MARKERS:
            if marker in text:
                raise SystemExit(f"{path_text} still contains stale post-merge marker {marker!r}")


def main() -> int:
    """Validate the frozen Gate 19.1 contract and current repository projection."""
    args = _parser().parse_args()
    repo_root = args.repo_root.resolve()
    root = _load(repo_root / _ARTIFACT)

    _verify_phase18_history(repo_root)
    _verify_identity(root)
    _verify_pipeline(root)
    _verify_workload(root)
    _verify_security_and_iam(root)
    _verify_operability(root)
    _verify_live_docs(repo_root)

    print(
        "phase19_gate19_1=PASS "
        "runtime_decision=DEFERRED_PENDING_MEASUREMENT "
        "leading_hypothesis=ASYNC_SUBMIT_STATUS_RESULT "
        "aws_mutations=0 iam_mutations=0 new_aws_resources=0 "
        "model_invocations=0 capability_executions=0 public_endpoints=0 pr_89_touched=false"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
