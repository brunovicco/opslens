#!/usr/bin/env python3
"""Verify the Gate 19.2 non-public representative measurement design contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import cast

from opslens.public_analysis.domain import (
    REPRESENTATIVE_PUBLIC_ANALYSIS_WORKLOAD_ID,
    REPRESENTATIVE_WORKLOAD_STAGE_ORDER,
)

_ARTIFACT = Path("labs/evidence/phase-19-gate-19-2-measurement-contract-v1.json")
_GATE19_1 = Path("labs/evidence/phase-19-gate-19-1-public-runtime-contract-v1.json")
_RUNBOOK = Path("labs/phase-19-gate-19-2-human-live-measurement-runbook.md")

_EXPECTED_MEASUREMENTS = {
    "end_to_end_duration_ms",
    "stage_duration_ms",
    "github_http_request_count",
    "athena_query_count",
    "athena_bytes_scanned",
    "bedrock_retrieve_count",
    "bedrock_retrieve_client_elapsed_ms",
    "bedrock_model_call_count",
    "bedrock_input_tokens",
    "bedrock_output_tokens",
    "bedrock_model_client_elapsed_ms",
    "bedrock_model_latency_ms",
    "retry_count",
    "throttle_count",
    "serialized_result_bytes",
}

_EXPECTED_COMPONENTS = {
    "provider_neutral_measurement_contract": (
        "src/opslens/public_analysis/domain/representative_measurement.py"
    ),
    "provider_neutral_measurement_harness": (
        "src/opslens/public_analysis/application/representative_measurement.py"
    ),
    "deterministic_repository_analysis_composition": (
        "src/opslens/public_analysis/application/representative_repository_analysis.py"
    ),
    "structured_evidence_projection": (
        "src/opslens/public_analysis/application/representative_structured_evidence.py"
    ),
    "semantic_evidence_retrieval": (
        "src/opslens/public_analysis/application/representative_semantic_evidence.py"
    ),
    "hybrid_evidence_composition": (
        "src/opslens/public_analysis/application/representative_hybrid_evidence.py"
    ),
    "bounded_model_reasoning": (
        "src/opslens/public_analysis/application/representative_model_reasoning.py"
    ),
    "deterministic_result_admission": (
        "src/opslens/public_analysis/domain/representative_result.py"
    ),
    "complete_representative_workload_execution": (
        "src/opslens/public_analysis/application/representative_workload_execution.py"
    ),
    "github_physical_transport_measurement": (
        "src/opslens/public_analysis/adapters/github_measurement.py"
    ),
}

_EXPECTED_CLASSIFICATIONS = {
    "github_http_request_count": "MEASURED",
    "athena_query_count": "NOT_APPLICABLE",
    "athena_bytes_scanned": "NOT_APPLICABLE",
    "bedrock_retrieve_count": "MEASURED",
    "bedrock_retrieve_client_elapsed_ms": "MEASURED",
    "bedrock_model_call_count": "MEASURED",
    "bedrock_input_tokens": "MEASURED",
    "bedrock_output_tokens": "MEASURED",
    "bedrock_model_client_elapsed_ms": "MEASURED",
    "bedrock_model_latency_ms": "MEASURED",
    "retry_count": "MEASURED",
    "throttle_count": "UNMEASURED",
}

_EXPECTED_RULES = {
    "measurement_layer_does_not_reimplement_business_truth",
    "complete_exact_stage_order_required",
    "provider_totals_equal_exact_stage_sum",
    "negative_counters_rejected",
    "empty_serialized_result_rejected",
    "clock_regression_rejected",
    "missing_instrumentation_must_not_be_reported_as_measured_zero",
    "physical_github_requests_measured_at_transport_boundary",
    "provider_latency_must_come_from_retained_invocation_evidence",
    "not_applicable_is_not_measured_zero",
}

_REQUIRED_INVARIANTS = {
    "Agents reason. Code verifies evidence.",
    "READ, NEVER EXECUTE third-party repository code.",
    "Repository Risk != Runtime Exposure.",
    "retrieved content != instruction authority",
    "model proposal != authorization",
    "tool/protocol success != business truth",
    "MEASURED != DERIVED",
    "UNMEASURED != zero",
    "configured limit != measured utilization",
}

_REQUIRED_CURRENT_DOC_MARKERS = {
    "README.md": (
        "19.1  Public Runtime Hypothesis & Launch Contract       COMPLETE",
        "original runtime decision: DEFERRED_PENDING_MEASUREMENT",
        "19.2  Representative Workload Measurement              CLOSEOUT IN REVIEW",
        "selected interaction pattern: ASYNC_SUBMIT_STATUS_RESULT",
        "concrete AWS topology selected: NO",
    ),
    "README.pt-br.md": (
        "19.1  Public Runtime Hypothesis & Launch Contract       COMPLETE",
        "decisão original: DEFERRED_PENDING_MEASUREMENT",
        "19.2  Representative Workload Measurement              CLOSEOUT IN REVIEW",
        "padrão de interação selecionado: ASYNC_SUBMIT_STATUS_RESULT",
        "topologia AWS concreta selecionada: NÃO",
    ),
    "docs/current-state.md": (
        "Gate 19.1",
        "DEFERRED_PENDING_MEASUREMENT",
        "Gate 19.2 — Representative Workload Measurement              CLOSEOUT IN REVIEW",
        "selected interaction pattern: ASYNC_SUBMIT_STATUS_RESULT",
        "concrete AWS topology selected: NO",
    ),
    "docs/roadmap.md": (
        "Gate 19.1",
        "DEFERRED_PENDING_MEASUREMENT",
        "Gate 19.2 — Representative Workload Measurement — CLOSEOUT IN REVIEW",
        "Selected interaction pattern:",
        "ASYNC_SUBMIT_STATUS_RESULT",
    ),
    "docs/README.md": (
        "Gate 19.1 — complete",
        "runtime decision: DEFERRED_PENDING_MEASUREMENT",
        "Gate 19.2 — closeout in review",
        "ASYNC_SUBMIT_STATUS_RESULT",
    ),
}


def _parser() -> argparse.ArgumentParser:
    """Build the read-only verifier CLI."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    return parser


def _object(value: object, *, label: str) -> dict[str, object]:
    """Return one JSON object or fail the evidence contract."""
    if not isinstance(value, dict):
        raise SystemExit(f"{label} must be a JSON object")
    return cast(dict[str, object], value)


def _strings(value: object, *, label: str) -> list[str]:
    """Return one JSON string array or fail the evidence contract."""
    if not isinstance(value, list):
        raise SystemExit(f"{label} must be a string array")
    values = cast(list[object], value)
    if any(not isinstance(item, str) for item in values):
        raise SystemExit(f"{label} must be a string array")
    return cast(list[str], values)


def _load(path: Path) -> dict[str, object]:
    """Load one machine-readable evidence object."""
    return _object(json.loads(path.read_text(encoding="utf-8")), label=str(path))


def _verify_identity(root: dict[str, object]) -> None:
    """Verify exact Gate 19.2 source and decision identity."""
    expected: dict[str, object] = {
        "artifact_version": "phase-19-gate-19-2-measurement-contract:v1",
        "phase": 19,
        "gate": "19.2",
        "issue": 295,
        "draft_pr": 297,
        "source_main_sha": "ed1d7a5bc72c2a4d6926a820ce22dd347060b3c1",
        "source_gate_19_1_pr": 292,
        "source_gate_19_1_exact_head_sha": (
            "484e2b85fc1996b2419b4057c2cf585ab1f675a1"
        ),
        "workload_id": REPRESENTATIVE_PUBLIC_ANALYSIS_WORKLOAD_ID,
        "status": "IMPLEMENTATION_IN_PROGRESS_NO_LIVE_MEASUREMENT",
        "retained_runtime_decision": "DEFERRED_PENDING_MEASUREMENT",
        "retained_leading_hypothesis": "ASYNC_SUBMIT_STATUS_RESULT",
        "runtime_selection_allowed": False,
    }
    for key, expected_value in expected.items():
        if root.get(key) != expected_value:
            raise SystemExit(f"Gate 19.2 identity drifted at {key}")


def _verify_stage_and_measurement_contract(root: dict[str, object]) -> None:
    """Bind machine-readable evidence to the executable measurement contract."""
    expected_stage_order = [stage.value for stage in REPRESENTATIVE_WORKLOAD_STAGE_ORDER]
    if _strings(root.get("stage_order"), label="stage_order") != expected_stage_order:
        raise SystemExit("Gate 19.2 stage order drifted from the executable contract")

    measurements = set(
        _strings(root.get("required_measurements"), label="required_measurements")
    )
    if measurements != _EXPECTED_MEASUREMENTS:
        raise SystemExit("Gate 19.2 required measurement set drifted")

    rules = set(_strings(root.get("measurement_rules"), label="measurement_rules"))
    if rules != _EXPECTED_RULES:
        raise SystemExit("Gate 19.2 measurement rules drifted")


def _verify_components(root: dict[str, object], repo_root: Path) -> None:
    """Require every declared implementation component to exist at the frozen path."""
    components = _object(root.get("implemented_components"), label="implemented_components")
    if components != _EXPECTED_COMPONENTS:
        raise SystemExit("Gate 19.2 implementation component inventory drifted")
    for path_text in _EXPECTED_COMPONENTS.values():
        if not (repo_root / path_text).is_file():
            raise SystemExit(f"Gate 19.2 implementation component missing: {path_text}")


def _verify_input_and_classifications(root: dict[str, object]) -> None:
    """Freeze historical input coordinates and explicit provider evidence semantics."""
    representative_input = _object(
        root.get("representative_input"),
        label="representative_input",
    )
    expected_input: dict[str, object] = {
        "status": "FROZEN_FOR_PRE_LIVE_MEASUREMENT",
        "repository_full_name": "whotracksme/whotracks.me",
        "requested_ref": "468f6e211a307f5f20d1d95c478ddd89efdb9b6b",
        "dependency_evidence_path": "uv.lock",
        "dependency_name": "requests",
        "dependency_version": "2.31.0",
    }
    for key, value in expected_input.items():
        if representative_input.get(key) != value:
            raise SystemExit(f"Gate 19.2 representative input drifted at {key}")

    vulnerability = _object(
        representative_input.get("vulnerability_anchor"),
        label="representative_input.vulnerability_anchor",
    )
    if vulnerability != {
        "ghsa_id": "GHSA-9wx4-h78v-vm56",
        "cve_id": "CVE-2024-35195",
        "affected_version_range": "< 2.32.0",
        "first_patched_version": "2.32.0",
    }:
        raise SystemExit("Gate 19.2 vulnerability anchor drifted")

    classifications = _object(
        root.get("provider_measurement_classification"),
        label="provider_measurement_classification",
    )
    if classifications != _EXPECTED_CLASSIFICATIONS:
        raise SystemExit("Gate 19.2 provider measurement classifications drifted")


def _verify_boundaries(root: dict[str, object], repo_root: Path) -> None:
    """Keep the historical live-execution boundary and authority impact immutable."""
    live = _object(root.get("live_execution_boundary"), label="live_execution_boundary")
    if live != {
        "aws_or_model_execution": "HUMAN_EXECUTION_REQUIRED",
        "public_endpoint_required_for_measurement": False,
        "public_endpoint_authorized": False,
    }:
        raise SystemExit("Gate 19.2 live execution boundary drifted")

    authority = _object(root.get("authority_impact"), label="authority_impact")
    if authority != {
        "public_endpoints": 0,
        "new_aws_resources": 0,
        "new_iam_roles_or_policies": 0,
        "third_party_repository_code_executions": 0,
        "pr_89_touched": False,
    }:
        raise SystemExit("Gate 19.2 acquired unauthorized runtime authority")

    invariants = set(
        _strings(root.get("retained_invariants"), label="retained_invariants")
    )
    if not _REQUIRED_INVARIANTS.issubset(invariants):
        raise SystemExit("Gate 19.2 retained invariants are incomplete")
    if not (repo_root / _RUNBOOK).is_file():
        raise SystemExit("Gate 19.2 human live-measurement runbook is missing")


def _verify_gate19_1_history(repo_root: Path) -> None:
    """Require Gate 19.2 to remain downstream of the exact Gate 19.1 decision."""
    previous = _load(repo_root / _GATE19_1)
    if previous.get("workload_id") != REPRESENTATIVE_PUBLIC_ANALYSIS_WORKLOAD_ID:
        raise SystemExit("Gate 19.1 workload identity drifted")
    if previous.get("decision") != "DEFERRED_PENDING_MEASUREMENT":
        raise SystemExit("Gate 19.2 cannot rewrite the retained Gate 19.1 decision")
    if previous.get("leading_runtime_hypothesis") != "ASYNC_SUBMIT_STATUS_RESULT":
        raise SystemExit("Gate 19.2 cannot rewrite the retained Gate 19.1 hypothesis")


def _verify_docs(repo_root: Path) -> None:
    """Require current docs to preserve Gate 19.1 history and expose Gate 19.2 closeout."""
    for path_text, markers in _REQUIRED_CURRENT_DOC_MARKERS.items():
        text = (repo_root / path_text).read_text(encoding="utf-8")
        for marker in markers:
            if marker not in text:
                raise SystemExit(f"{path_text} is missing Gate 19.2 marker {marker!r}")


def main() -> int:
    """Run the deterministic read-only Gate 19.2 design verification."""
    args = _parser().parse_args()
    repo_root = args.repo_root.resolve()
    root = _load(repo_root / _ARTIFACT)

    _verify_identity(root)
    _verify_stage_and_measurement_contract(root)
    _verify_components(root, repo_root)
    _verify_input_and_classifications(root)
    _verify_boundaries(root, repo_root)
    _verify_gate19_1_history(repo_root)
    _verify_docs(repo_root)

    print(
        "phase19_gate19_2_contract=PASS "
        "runtime_decision=DEFERRED_PENDING_MEASUREMENT "
        "live_execution=HUMAN_BOUNDARY public_endpoints=0 "
        "new_aws_resources=0 new_iam_roles_or_policies=0"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
