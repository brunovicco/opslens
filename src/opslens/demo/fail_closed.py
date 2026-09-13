"""Fail-closed incomplete-evidence demonstration for OpsLens V1."""

import base64
import json
from dataclasses import dataclass
from hashlib import sha256

from opslens.demo.material_vulnerability import DemoContractError
from opslens.public_analysis.application import build_public_repository_evidence
from opslens.public_analysis.application.threat_evidence_authority import (
    build_public_threat_evidence_scope,
)
from opslens.public_analysis.domain import (
    PublicAnalysisValidationError,
    PublicRepositoryEvidenceExecution,
    PublicRepositoryTarget,
    create_public_analysis_request,
)
from opslens.repository_intelligence.domain import compute_git_blob_sha1

type JsonValue = str | int | float | bool | list[JsonValue] | dict[str, JsonValue] | None

FAIL_CLOSED_RESULT_CONTRACT_VERSION = "opslens-demo-fail-closed-result:v1"
FAIL_CLOSED_SCENARIO_ID = "fail-closed-incomplete-evidence"
FAIL_CLOSED_FIXTURE_VERSION = "fail-closed-incomplete-evidence-fixture:v1"

_REPOSITORY_OWNER = "opslens-demo"
_REPOSITORY_NAME = "fail-closed-incomplete-evidence-fixture"
_REPOSITORY_ID = 19_110_003
_COMMIT_SHA = "7" * 40
_TREE_SHA = "8" * 40
_EXPECTED_AUTHORITY_MESSAGE = (
    "public threat scope refuses incomplete PyPI normalization evidence"
)
_EXPECTED_REASON_CODE = "invalid_version"


def _canonical_json(value: object) -> bytes:
    """Serialize deterministic JSON for fail-closed reviewer output."""
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _uv_lock_content() -> bytes:
    """Return inert lock evidence whose PyPI version cannot be normalized."""
    return (
        b"version = 1\n"
        b"revision = 3\n"
        b'requires-python = ">=3.13"\n'
        b"[[package]]\n"
        b'name = "requests"\n'
        b'version = "not a version"\n'
        b'source = { registry = "https://pypi.org/simple" }\n'
    )


@dataclass(frozen=True, slots=True)
class OfflineIncompleteRepositorySource:
    """Serve exact inert repository evidence containing unsupported normalization."""

    def get_repository(self, owner: str, name: str) -> dict[str, object]:
        """Return source-confirmed public metadata for the synthetic fixture."""
        if (owner, name) != (_REPOSITORY_OWNER, _REPOSITORY_NAME):
            raise DemoContractError("fail-closed repository coordinates drifted")
        return {
            "id": _REPOSITORY_ID,
            "name": name,
            "full_name": f"{owner}/{name}",
            "private": False,
            "visibility": "public",
            "default_branch": "main",
            "owner": {"login": owner},
        }

    def get_commit(self, owner: str, name: str, ref: str) -> dict[str, object]:
        """Return the exact immutable synthetic commit/tree coordinates."""
        if (owner, name, ref) != (_REPOSITORY_OWNER, _REPOSITORY_NAME, "main"):
            raise DemoContractError("fail-closed commit coordinates drifted")
        return {"sha": _COMMIT_SHA, "commit": {"tree": {"sha": _TREE_SHA}}}

    def get_uv_lock(
        self,
        owner: str,
        name: str,
        commit_sha: str,
    ) -> dict[str, object]:
        """Return exact-commit inert dependency evidence without executing code."""
        if (owner, name, commit_sha) != (
            _REPOSITORY_OWNER,
            _REPOSITORY_NAME,
            _COMMIT_SHA,
        ):
            raise DemoContractError("fail-closed lockfile coordinates drifted")
        content = _uv_lock_content()
        return {
            "type": "file",
            "path": "uv.lock",
            "name": "uv.lock",
            "encoding": "base64",
            "size": len(content),
            "sha": compute_git_blob_sha1(content),
            "content": base64.encodebytes(content).decode("ascii"),
        }


@dataclass(frozen=True, slots=True)
class FailClosedDemoResult:
    """Content-addressed rejection proving incomplete evidence is not benign evidence."""

    source_execution: PublicRepositoryEvidenceExecution
    authority_message: str

    def __post_init__(self) -> None:
        """Require the exact unsupported-normalization evidence that caused rejection."""
        inventory = self.source_execution.normalization_inventory
        if inventory.normalized_dependencies:
            raise DemoContractError(
                "fail-closed fixture must not admit normalized dependencies"
            )
        if len(inventory.unsupported_normalization) != 1:
            raise DemoContractError(
                "fail-closed fixture must preserve exactly one unsupported dependency"
            )
        unsupported = inventory.unsupported_normalization[0]
        if unsupported.reason_code != _EXPECTED_REASON_CODE:
            raise DemoContractError("fail-closed fixture rejection reason drifted")
        if self.authority_message != _EXPECTED_AUTHORITY_MESSAGE:
            raise DemoContractError("fail-closed authority rejection message drifted")

    @property
    def canonical_payload(self) -> dict[str, JsonValue]:
        """Return stable JSON that keeps rejection distinct from benign evidence."""
        inventory = self.source_execution.normalization_inventory
        unsupported = inventory.unsupported_normalization[0]
        return {
            "contract_version": FAIL_CLOSED_RESULT_CONTRACT_VERSION,
            "scenario": {
                "id": FAIL_CLOSED_SCENARIO_ID,
                "fixture_version": FAIL_CLOSED_FIXTURE_VERSION,
                "source_kind": "offline_synthetic_fixture",
            },
            "authority": {
                "mode": "OFFLINE_DETERMINISTIC",
                "aws_credentials_required": False,
                "network_access": False,
                "live_provider_execution": False,
                "model_execution": False,
                "third_party_repository_code_execution": False,
            },
            "outcome": {
                "state": "REJECTED_INCOMPLETE_EVIDENCE",
                "stage": "PUBLIC_THREAT_SCOPE_ADMISSION",
                "reason_code": "INCOMPLETE_PYPI_NORMALIZATION",
                "authority_message": self.authority_message,
                "analysis_performed": False,
                "risk_prioritization_performed": False,
                "benign_conclusion": False,
                "missing_evidence_treated_as_benign": False,
            },
            "unsupported_dependency": {
                "record_index": unsupported.record_index,
                "name_original": unsupported.source_record.name_original,
                "version_original": unsupported.source_record.version_original,
                "reason_code": unsupported.reason_code,
            },
            "identities": {
                "repository_execution_id": self.source_execution.execution_id,
                "repository_execution_sha256": self.source_execution.evidence_sha256,
            },
        }

    @property
    def canonical_json(self) -> bytes:
        """Return stable canonical JSON for machine comparison."""
        return _canonical_json(self.canonical_payload)

    @property
    def evidence_sha256(self) -> str:
        """Return SHA-256 of the complete fail-closed projection."""
        return sha256(self.canonical_json).hexdigest()

    @property
    def result_id(self) -> str:
        """Return the content-addressed fail-closed result identity."""
        return f"{FAIL_CLOSED_RESULT_CONTRACT_VERSION}@sha256:{self.evidence_sha256}"

    def to_text(self) -> str:
        """Render a reviewer summary that explicitly refuses a benign conclusion."""
        unsupported = self.source_execution.normalization_inventory.unsupported_normalization[0]
        return "\n".join(
            (
                "OpsLens V1 deterministic offline demo",
                f"scenario: {FAIL_CLOSED_SCENARIO_ID}",
                "outcome: REJECTED_INCOMPLETE_EVIDENCE",
                "stage: PUBLIC_THREAT_SCOPE_ADMISSION",
                (
                    "unsupported dependency: "
                    f"{unsupported.source_record.name_original}=="
                    f"{unsupported.source_record.version_original}"
                ),
                f"normalization reason: {unsupported.reason_code}",
                f"authority rejection: {self.authority_message}",
                "analysis performed: NO",
                "risk prioritization performed: NO",
                "benign conclusion: NO",
                "invariant: missing evidence != benign evidence",
                f"demo result: {self.result_id}",
                "safety: READ, NEVER EXECUTE third-party repository code",
                "",
            )
        )


def build_fail_closed_incomplete_evidence_demo() -> FailClosedDemoResult:
    """Reject incomplete dependency identity before threat or risk truth is created."""
    request = create_public_analysis_request(
        PublicRepositoryTarget(
            owner=_REPOSITORY_OWNER,
            name=_REPOSITORY_NAME,
            requested_ref="main",
        )
    )
    execution = build_public_repository_evidence(
        request,
        OfflineIncompleteRepositorySource(),
    )

    try:
        build_public_threat_evidence_scope(execution)
    except PublicAnalysisValidationError as exc:
        message = str(exc)
        if message != _EXPECTED_AUTHORITY_MESSAGE:
            raise DemoContractError(
                "fail-closed fixture reached an unexpected authority rejection"
            ) from exc
        return FailClosedDemoResult(
            source_execution=execution,
            authority_message=message,
        )

    raise DemoContractError("incomplete dependency evidence was unexpectedly admitted")


__all__ = [
    "FAIL_CLOSED_FIXTURE_VERSION",
    "FAIL_CLOSED_RESULT_CONTRACT_VERSION",
    "FAIL_CLOSED_SCENARIO_ID",
    "FailClosedDemoResult",
    "OfflineIncompleteRepositorySource",
    "build_fail_closed_incomplete_evidence_demo",
]
