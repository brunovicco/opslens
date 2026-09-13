"""Human-run composition root for one Gate 19.2 representative live measurement."""

import argparse
import json
import os
import re
import sys
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from hashlib import sha256
from http.client import HTTPSConnection
from pathlib import Path
from typing import cast

import boto3
from botocore.config import Config

from opslens.hybrid_retrieval.adapters.bedrock_synthesis import BedrockHybridConverseClient
from opslens.knowledge_retrieval.adapters.bedrock_retrieval import BedrockAgentRuntimeClient
from opslens.knowledge_retrieval.application.bedrock_synthesis import (
    BEDROCK_SYNTHESIS_MODEL_ID,
    BEDROCK_SYNTHESIS_REGION,
)
from opslens.knowledge_retrieval.application.corpus_config import load_corpus_manifest
from opslens.knowledge_retrieval.application.retrieval_catalog import build_retrieval_catalog
from opslens.public_analysis.adapters.exact_s3_authority_object import (
    ExactS3AuthorityObjectClient,
)
from opslens.public_analysis.adapters.representative_live_artifact_file import (
    write_new_representative_live_artifact,
)
from opslens.public_analysis.adapters.representative_live_workload import (
    RepresentativeLiveRetrievalConfig,
    build_representative_live_workload_composition,
)
from opslens.public_analysis.adapters.representative_threat_authority_reader_factory import (
    RepresentativeThreatAuthorityByteLimits,
    build_representative_threat_authority_readers,
)
from opslens.public_analysis.application.representative_live_measurement_run import (
    FROZEN_REPRESENTATIVE_REPOSITORY_COMMIT,
    FROZEN_REPRESENTATIVE_REPOSITORY_URL,
    RepresentativeLiveRunMetadata,
    execute_representative_live_measurement,
)
from opslens.public_analysis.application.representative_pre_measurement_authority import (
    materialize_pre_measurement_threat_evidence,
)
from opslens.public_analysis.application.representative_threat_evidence_coordinate_loaders import (
    parse_representative_threat_evidence_coordinates,
)
from opslens.public_analysis.application.representative_threat_evidence_preparation import (
    RepresentativeThreatEvidencePreparationSummary,
    summarize_representative_threat_evidence_preparation,
)
from opslens.repository_intelligence.adapters.github_http import (
    GitHubHttpsConnection,
    GitHubRestClientConfig,
)

_FROZEN_CVE_ID = "CVE-2026-54770"
_FROZEN_GHSA_ID = "GHSA-6hx8-3wjj-gr8g"
_FROZEN_KEV_SNAPSHOT_DATE = "2026-09-10"
_FROZEN_EPSS_SNAPSHOT_DATE = "2026-09-10"
_DEFAULT_MANIFEST = Path("knowledge/corpus/v1/manifest.json")
_DEFAULT_OUTPUT = Path("labs/evidence/phase-19-gate-19-2-live-measurement-v1.json")
_GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$", re.ASCII)


class LiveMeasurementCliError(ValueError):
    """Reject operator input or frozen-anchor drift before measured provider execution."""


def _positive_int(value: str) -> int:
    """Parse one required positive byte limit."""
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be a positive integer")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    """Build the explicit human-only live measurement command surface."""
    parser = argparse.ArgumentParser(
        description=(
            "Human-run only: materialize exact threat authority before timing, execute one "
            "frozen non-public representative workload with live GitHub/Bedrock reads, and "
            "atomically persist only the admitted bounded measurement artifact."
        )
    )
    parser.add_argument("--bundle", required=True, type=Path)
    parser.add_argument("--locator-manifest", required=True, type=Path)
    parser.add_argument("--manifest", type=Path, default=_DEFAULT_MANIFEST)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--region", required=True)
    parser.add_argument("--authority-bucket", required=True)
    parser.add_argument("--knowledge-base-id", required=True)
    parser.add_argument("--data-source-id", required=True)
    parser.add_argument("--source-bucket", required=True)
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--repository-url", required=True)
    parser.add_argument("--repository-ref", required=True)
    parser.add_argument("--repository-commit", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--opslens-commit-sha", required=True)
    parser.add_argument(
        "--github-token-env",
        help=(
            "Optional environment-variable name containing a GitHub token. The token value "
            "is never serialized or printed."
        ),
    )
    parser.add_argument("--ghsa-silver-max-bytes", required=True, type=_positive_int)
    parser.add_argument("--nvd-silver-max-bytes", required=True, type=_positive_int)
    parser.add_argument("--nvd-bronze-max-bytes", required=True, type=_positive_int)
    parser.add_argument("--kev-bronze-max-bytes", required=True, type=_positive_int)
    parser.add_argument("--epss-bronze-max-bytes", required=True, type=_positive_int)
    parser.add_argument("--output", type=Path, default=_DEFAULT_OUTPUT)
    return parser


def _load_json_object(path: Path) -> tuple[bytes, Mapping[str, object]]:
    """Read one local JSON object exactly once before provider execution."""
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise LiveMeasurementCliError(f"could not read required input {path}") from exc
    try:
        decoded = cast(object, json.loads(payload))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LiveMeasurementCliError(f"{path} must contain valid UTF-8 JSON") from exc
    if not isinstance(decoded, dict):
        raise LiveMeasurementCliError(f"{path} must contain one JSON object")
    return payload, cast(Mapping[str, object], decoded)


def _require_frozen_operator_inputs(args: argparse.Namespace) -> None:
    """Reject identity drift before constructing any physical provider client."""
    region = cast(str, args.region)
    repository_url = cast(str, args.repository_url)
    repository_ref = cast(str, args.repository_ref)
    repository_commit = cast(str, args.repository_commit)
    model_id = cast(str, args.model_id)
    run_id = cast(str, args.run_id)
    opslens_commit_sha = cast(str, args.opslens_commit_sha)
    output = cast(Path, args.output)

    if region != BEDROCK_SYNTHESIS_REGION:
        raise LiveMeasurementCliError(
            f"region must equal the retained synthesis region {BEDROCK_SYNTHESIS_REGION!r}"
        )
    if repository_url != FROZEN_REPRESENTATIVE_REPOSITORY_URL:
        raise LiveMeasurementCliError(
            "repository-url drifted from the frozen representative anchor"
        )
    if repository_ref != FROZEN_REPRESENTATIVE_REPOSITORY_COMMIT:
        raise LiveMeasurementCliError("repository-ref must equal the frozen exact commit")
    if repository_commit != FROZEN_REPRESENTATIVE_REPOSITORY_COMMIT:
        raise LiveMeasurementCliError("repository-commit must equal the frozen exact commit")
    if model_id != BEDROCK_SYNTHESIS_MODEL_ID:
        raise LiveMeasurementCliError(
            "model-id drifted from the retained hybrid synthesis model"
        )
    if not run_id or run_id != run_id.strip() or len(run_id) > 256:
        raise LiveMeasurementCliError(
            "run-id must be one normalized non-empty string of at most 256 characters"
        )
    if _GIT_SHA_RE.fullmatch(opslens_commit_sha) is None:
        raise LiveMeasurementCliError("opslens-commit-sha must be one lowercase full Git SHA")
    if output.exists():
        raise LiveMeasurementCliError(
            "output artifact already exists; refusing to overwrite evidence"
        )
    if not output.parent.is_dir():
        raise LiveMeasurementCliError("output artifact parent directory must already exist")


def _github_token(environment_name: str | None) -> str | None:
    """Read an optional token through explicit environment indirection only."""
    if environment_name is None:
        return None
    if not environment_name or environment_name != environment_name.strip():
        raise LiveMeasurementCliError("github-token-env must be a normalized environment name")
    token = os.environ.get(environment_name)
    if token is None:
        raise LiveMeasurementCliError(
            "github-token-env names an environment variable that is not set"
        )
    if not token or token != token.strip():
        raise LiveMeasurementCliError(
            "GitHub token environment value must be non-empty and trimmed"
        )
    return token


def _github_connection_factory(host: str, timeout_seconds: float) -> GitHubHttpsConnection:
    """Create only the retained fixed GitHub API HTTPS transport."""
    if host != "api.github.com":
        raise LiveMeasurementCliError(
            "GitHub transport host is outside the retained fixed host"
        )
    return cast(GitHubHttpsConnection, HTTPSConnection(host, timeout=timeout_seconds))


def _retrieval_client_config() -> Config:
    """Reuse the retained bounded direct-Retrieve SDK transport settings."""
    return Config(
        connect_timeout=5,
        read_timeout=30,
        retries={"max_attempts": 3, "mode": "standard"},
    )


def _synthesis_client_config() -> Config:
    """Reuse the retained bounded hybrid Converse SDK transport settings."""
    return Config(
        connect_timeout=5,
        read_timeout=90,
        retries={"max_attempts": 3, "mode": "standard"},
    )


def _require_frozen_threat_anchor(
    summary: RepresentativeThreatEvidencePreparationSummary,
    *,
    ghsa_ids: tuple[str, ...],
    nvd_cve_ids: tuple[str, ...],
) -> None:
    """Require the prepared authority to remain the exact frozen representative threat case."""
    if summary.cve_id != _FROZEN_CVE_ID:
        raise LiveMeasurementCliError(
            "prepared threat evidence CVE drifted from the frozen anchor"
        )
    if summary.kev_snapshot_date != _FROZEN_KEV_SNAPSHOT_DATE:
        raise LiveMeasurementCliError(
            "prepared KEV snapshot date drifted from the frozen anchor"
        )
    if summary.epss_snapshot_date != _FROZEN_EPSS_SNAPSHOT_DATE:
        raise LiveMeasurementCliError(
            "prepared EPSS snapshot date drifted from the frozen anchor"
        )
    if ghsa_ids != (_FROZEN_GHSA_ID,):
        raise LiveMeasurementCliError(
            "prepared GHSA authority does not match the frozen anchor"
        )
    if nvd_cve_ids != (_FROZEN_CVE_ID,):
        raise LiveMeasurementCliError(
            "prepared NVD authority does not match the frozen anchor"
        )


def _source_evidence_hashes(
    *,
    bundle_sha256: str,
    locator_manifest_sha256: str,
    summary: RepresentativeThreatEvidencePreparationSummary,
    ghsa_sha256: str,
    nvd_sha256: str,
) -> tuple[tuple[str, str], ...]:
    """Project sorted content identities without retaining any raw authority payload."""
    return (
        ("cross_source_bundle", bundle_sha256),
        ("epss_snapshot", summary.epss_sha256),
        ("ghsa_advisory", ghsa_sha256),
        ("kev_snapshot", summary.kev_sha256),
        ("nvd_cve", nvd_sha256),
        ("threat_locator_manifest", locator_manifest_sha256),
    )


def _run_timestamp_utc() -> str:
    """Return canonical second-resolution UTC evidence for the live run start."""
    return datetime.now(UTC).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def main(argv: Sequence[str] | None = None) -> int:
    """Cross the human boundary once; no CI workflow invokes the provider path."""
    args = build_parser().parse_args(argv)

    try:
        _require_frozen_operator_inputs(args)
        github_token = _github_token(cast(str | None, args.github_token_env))
        bundle_path = cast(Path, args.bundle)
        locator_manifest_path = cast(Path, args.locator_manifest)
        corpus_manifest_path = cast(Path, args.manifest)
        output_path = cast(Path, args.output)
        bundle_bytes, bundle = _load_json_object(bundle_path)
        locator_bytes, locator_manifest = _load_json_object(locator_manifest_path)
        retrieval_catalog = build_retrieval_catalog(
            load_corpus_manifest(corpus_manifest_path)
        )

        bundle_digest = sha256(bundle_bytes).hexdigest()
        locator_digest = sha256(locator_bytes).hexdigest()
        region = cast(str, args.region)
        session = boto3.Session(
            profile_name=cast(str, args.profile),
            region_name=region,
        )

        s3_client = cast(
            ExactS3AuthorityObjectClient,
            session.client(  # pyright: ignore[reportUnknownMemberType]
                "s3",
                config=Config(
                    retries={"mode": "standard", "total_max_attempts": 1}
                ),
            ),
        )
        readers = build_representative_threat_authority_readers(
            client=s3_client,
            bucket_name=cast(str, args.authority_bucket),
            byte_limits=RepresentativeThreatAuthorityByteLimits(
                ghsa_silver=cast(int, args.ghsa_silver_max_bytes),
                nvd_silver=cast(int, args.nvd_silver_max_bytes),
                nvd_bronze=cast(int, args.nvd_bronze_max_bytes),
                kev_bronze=cast(int, args.kev_bronze_max_bytes),
                epss_bronze=cast(int, args.epss_bronze_max_bytes),
            ),
        )
        threat_evidence = materialize_pre_measurement_threat_evidence(
            bundle,
            locator_manifest=locator_manifest,
            readers=readers,
        )
        coordinates = parse_representative_threat_evidence_coordinates(bundle)
        preparation = summarize_representative_threat_evidence_preparation(
            coordinates=coordinates,
            evidence=threat_evidence,
            bundle_sha256=bundle_digest,
            locator_manifest_sha256=locator_digest,
        )
        ghsa_ids = tuple(
            item.ghsa_id for item in threat_evidence.ghsa_vulnerabilities
        )
        nvd_ids = tuple(
            item.observed_version.cve_id for item in threat_evidence.nvd_records
        )
        _require_frozen_threat_anchor(
            preparation,
            ghsa_ids=ghsa_ids,
            nvd_cve_ids=nvd_ids,
        )
        ghsa_sha256 = threat_evidence.ghsa_vulnerabilities[0].source_advisory_sha256
        nvd_sha256 = (
            threat_evidence.nvd_records[0].observed_version.source_cve_sha256
        )
        source_evidence = _source_evidence_hashes(
            bundle_sha256=bundle_digest,
            locator_manifest_sha256=locator_digest,
            summary=preparation,
            ghsa_sha256=ghsa_sha256,
            nvd_sha256=nvd_sha256,
        )

        retrieval_client = cast(
            BedrockAgentRuntimeClient,
            session.client(  # pyright: ignore[reportUnknownMemberType]
                "bedrock-agent-runtime",
                region_name=region,
                config=_retrieval_client_config(),
            ),
        )
        synthesis_client = cast(
            BedrockHybridConverseClient,
            session.client(  # pyright: ignore[reportUnknownMemberType]
                "bedrock-runtime",
                region_name=region,
                config=_synthesis_client_config(),
            ),
        )

        composition = build_representative_live_workload_composition(
            github_connection_factory=_github_connection_factory,
            threat_evidence=threat_evidence,
            expected_repository_url=cast(str, args.repository_url),
            expected_commit_sha=cast(str, args.repository_commit),
            retrieval_client=retrieval_client,
            synthesis_client=synthesis_client,
            retrieval_catalog=retrieval_catalog,
            retrieval_config=RepresentativeLiveRetrievalConfig(
                knowledge_base_id=cast(str, args.knowledge_base_id),
                data_source_id=cast(str, args.data_source_id),
                source_bucket=cast(str, args.source_bucket),
            ),
            github_config=GitHubRestClientConfig(
                user_agent="OpsLens/phase19-gate19-2",
                token=github_token,
            ),
        )
        run = execute_representative_live_measurement(
            metadata=RepresentativeLiveRunMetadata(
                run_id=cast(str, args.run_id),
                opslens_commit_sha=cast(str, args.opslens_commit_sha),
                run_timestamp_utc=_run_timestamp_utc(),
                repository_url=cast(str, args.repository_url),
                requested_ref=cast(str, args.repository_ref),
                repository_commit_sha=cast(str, args.repository_commit),
                source_evidence=source_evidence,
                bedrock_knowledge_base_id=cast(str, args.knowledge_base_id),
                model_id=cast(str, args.model_id),
            ),
            dependencies=composition.dependencies,
        )
        write_new_representative_live_artifact(
            output_path,
            run.serialized_artifact,
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(
        json.dumps(
            {
                "artifact_path": str(output_path),
                "artifact_sha256": sha256(run.serialized_artifact).hexdigest(),
                "end_to_end_duration_ms": run.artifact.end_to_end_duration_ms,
                "outcome": run.artifact.outcome,
                "provider_classifications": [
                    {"metric": metric, "classification": classification}
                    for metric, classification in run.artifact.provider_classifications
                ],
                "provider_totals": [
                    {"metric": metric, "value": value}
                    for metric, value in run.artifact.provider_totals
                ],
                "run_id": run.artifact.run_id,
                "serialized_result_bytes": run.artifact.serialized_result_bytes,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


__all__ = ["LiveMeasurementCliError", "build_parser", "main"]