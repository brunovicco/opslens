#!/usr/bin/env python3
"""Verify the Gate 19.8 request-time threat-evidence contract without providers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

_ARTIFACT = Path("labs/evidence/phase-19-gate-19-8-threat-evidence-authority-v1.json")
_CONTRACT = Path("src/opslens/public_analysis/application/threat_evidence_authority.py")
_WORKER = Path("src/opslens/public_analysis/async_worker_lambda.py")
_CURRENT_STATE = Path("docs/current-state.md")
_ROADMAP = Path("docs/roadmap.md")

_EXPECTED_MAIN = "8700478c7fca230e5984c3ce034194ea3bd337e4"
_EXPECTED_CODEQL_RUN = 34711607099
_EXPECTED_ISSUE = 374
_EXPECTED_PHYSICAL_DECISION = "DEFERRED_PENDING_BOUNDED_RUNTIME_ADAPTER_EVIDENCE"


class Gate19_8VerificationError(ValueError):
    """Reject authority drift or accidental Gate 19.8 provider/runtime expansion."""


def _load_json(path: Path) -> dict[str, object]:
    try:
        decoded = cast(object, json.loads(path.read_text(encoding="utf-8")))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Gate19_8VerificationError(f"could not load {path}") from exc
    if not isinstance(decoded, dict):
        raise Gate19_8VerificationError(f"{path} must contain one JSON object")
    return cast(dict[str, object], decoded)


def _object(value: object, *, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise Gate19_8VerificationError(f"{label} must be an object")
    return cast(dict[str, object], value)


def _strings(value: object, *, label: str) -> tuple[str, ...]:
    if not isinstance(value, list) or any(type(item) is not str for item in value):
        raise Gate19_8VerificationError(f"{label} must be a string array")
    return tuple(cast(list[str], value))


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise Gate19_8VerificationError(f"could not read {path}") from exc


def _require(text: str, needle: str, *, label: str) -> None:
    if needle not in text:
        raise Gate19_8VerificationError(f"{label} is missing {needle!r}")


def _forbid(text: str, needle: str, *, label: str) -> None:
    if needle in text:
        raise Gate19_8VerificationError(f"{label} unexpectedly contains {needle!r}")


def _verify_identity(root: dict[str, object]) -> None:
    expected: dict[str, object] = {
        "artifact_type": "phase-19-gate-19-8-threat-evidence-authority:v1",
        "schema_version": 1,
        "phase": 19,
        "gate": "19.8",
        "issue": _EXPECTED_ISSUE,
        "source_main_sha": _EXPECTED_MAIN,
        "source_gate_19_7_issue": 361,
        "source_gate_19_7_status": "COMPLETE",
        "source_gate_19_7_post_merge_codeql_run": _EXPECTED_CODEQL_RUN,
        "status": "OFFLINE_AUTHORITY_CONTRACT",
    }
    for field, value in expected.items():
        if root.get(field) != value:
            raise Gate19_8VerificationError(f"Gate 19.8 identity drifted at {field}")


def _verify_contract(root: dict[str, object], source: str) -> None:
    contract = _object(root.get("contract"), label="contract")
    if contract.get("scope_contract") != "public-threat-evidence-scope:v1":
        raise Gate19_8VerificationError("scope contract identity drifted")
    if contract.get("request_contract") != "public-threat-evidence-request:v1":
        raise Gate19_8VerificationError("request contract identity drifted")
    if contract.get("snapshot_policy") != "latest_complete":
        raise Gate19_8VerificationError("snapshot policy drifted")
    if _strings(contract.get("structured_sources"), label="structured_sources") != (
        "GHSA",
        "NVD",
        "CISA_KEV",
        "FIRST_EPSS",
    ):
        raise Gate19_8VerificationError("structured source inventory drifted")
    if _strings(contract.get("model_authority"), label="model_authority"):
        raise Gate19_8VerificationError("Gate 19.8 unexpectedly grants model authority")

    for marker in (
        'PUBLIC_THREAT_EVIDENCE_SCOPE_CONTRACT_VERSION = "public-threat-evidence-scope:v1"',
        'PUBLIC_THREAT_EVIDENCE_REQUEST_CONTRACT_VERSION = "public-threat-evidence-request:v1"',
        'LATEST_COMPLETE = "latest_complete"',
        "class PublicThreatDependencyScope",
        "class PublicThreatEvidenceScope",
        "class PublicThreatEvidenceRequest",
        "class PublicThreatEvidenceProvenance",
        "class PublicRepositoryThreatEvidence",
        "class PublicThreatEvidenceAuthority(Protocol)",
        "def build_public_threat_evidence_scope(",
        "def load_public_repository_threat_evidence(",
        "public threat scope refuses incomplete PyPI normalization evidence",
        "public GHSA evidence is outside the admitted dependency scope",
        "public NVD evidence is unrelated to admitted scoped GHSA evidence",
    ):
        _require(source, marker, label="Gate 19.8 contract")

    for forbidden in (
        "import boto3",
        "from boto3",
        "import botocore",
        "from botocore",
        "start_query_execution",
        "get_object(",
        "retrieve(",
        "converse(",
    ):
        _forbid(source, forbidden, label="provider-neutral Gate 19.8 contract")


def _verify_physical_access_deferred(root: dict[str, object]) -> None:
    decision = _object(root.get("physical_access_decision"), label="physical_access_decision")
    if decision.get("decision") != _EXPECTED_PHYSICAL_DECISION:
        raise Gate19_8VerificationError("physical structured-threat adapter was prematurely selected")
    reasons = _strings(decision.get("reasons"), label="physical_access_decision.reasons")
    if len(reasons) < 4:
        raise Gate19_8VerificationError("physical-access deferment is not evidence-backed")


def _verify_no_authority_expansion(root: dict[str, object], worker: str) -> None:
    runtime = _object(root.get("runtime_state"), label="runtime_state")
    expected_runtime = {
        "runtime_materialized": True,
        "execute_api_endpoint_disabled": True,
        "submit_enabled": False,
        "worker_enabled": False,
        "worker_event_source_mapping_enabled": False,
        "provider_heavy_executor_composed": False,
        "custom_public_domain_present": False,
    }
    if runtime != expected_runtime:
        raise Gate19_8VerificationError("Gate 19.8 runtime safety state drifted")

    impact = _object(root.get("authority_impact"), label="authority_impact")
    if set(impact) != {
        "terraform_provider_or_backend_operations",
        "aws_mutations",
        "iam_mutations",
        "lambda_artifact_publications",
        "runtime_enablements",
        "provider_live_executions",
        "third_party_repository_code_executions",
        "pr_89_modifications",
    }:
        raise Gate19_8VerificationError("Gate 19.8 authority-impact vocabulary drifted")
    if any(type(value) is not int or value != 0 for value in impact.values()):
        raise Gate19_8VerificationError("Gate 19.8 acquired mutation or execution authority")

    _require(
        worker,
        "async worker execution is enabled but provider executor composition is not admitted",
        label="async worker",
    )
    _require(
        worker,
        "if settings.worker_enabled:",
        label="async worker",
    )


def _verify_current_facing_docs(current_state: str, roadmap: str) -> None:
    for text, label in ((current_state, "current state"), (roadmap, "roadmap")):
        _require(text, _EXPECTED_MAIN, label=label)
        _require(text, "Gate 19.8", label=label)
        _require(text, "#374", label=label)
        _require(text, "materialized != enabled", label=label)
    _require(current_state, "34711607099", label="current state")
    _require(
        roadmap,
        _EXPECTED_PHYSICAL_DECISION,
        label="roadmap",
    )


def main() -> None:
    """Verify the bounded offline Gate 19.8 contract and retained disabled worker."""
    root = _load_json(_ARTIFACT)
    source = _read(_CONTRACT)
    worker = _read(_WORKER)
    current_state = _read(_CURRENT_STATE)
    roadmap = _read(_ROADMAP)

    _verify_identity(root)
    _verify_contract(root, source)
    _verify_physical_access_deferred(root)
    _verify_no_authority_expansion(root, worker)
    _verify_current_facing_docs(current_state, roadmap)

    print(
        "phase19_gate19_8_threat_authority=PASS "
        "provider_neutral=true physical_adapter_deferred=true "
        "runtime_enabled=false provider_heavy_execution=false"
    )


if __name__ == "__main__":
    main()
