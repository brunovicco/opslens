"""Deterministically review one persisted Gate 19.2 live-measurement artifact."""

import json
import re
from collections.abc import Mapping
from typing import Final, cast

from opslens.knowledge_retrieval.application.bedrock_synthesis import (
    BEDROCK_SYNTHESIS_MODEL_ID,
)
from opslens.public_analysis.application.representative_live_measurement_artifact import (
    RepresentativeLiveMeasurementArtifact,
    RepresentativeLiveMeasurementArtifactError,
)
from opslens.public_analysis.application.representative_live_measurement_run import (
    FROZEN_REPRESENTATIVE_REPOSITORY_COMMIT,
    FROZEN_REPRESENTATIVE_REPOSITORY_URL,
)
from opslens.public_analysis.domain import (
    PROVIDER_RESOURCE_METRICS,
    REPRESENTATIVE_PUBLIC_ANALYSIS_WORKLOAD_ID,
    MeasurementClassification,
    ProviderResourceMetric,
)

FROZEN_REPRESENTATIVE_BEDROCK_KNOWLEDGE_BASE_ID: Final = "BTVJ2PBR2A"
_GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$", re.ASCII)
_EXPECTED_JSON_KEYS = frozenset(
    {
        "artifact_type",
        "bedrock_knowledge_base_id",
        "end_to_end_duration_ms",
        "final_result_sha256",
        "model_id",
        "new_aws_resource_count",
        "new_iam_role_policy_count",
        "opslens_commit_sha",
        "outcome",
        "provider_classifications",
        "provider_totals",
        "public_endpoint_count",
        "repository_commit_sha",
        "repository_url",
        "run_id",
        "run_timestamp_utc",
        "schema_version",
        "serialized_result_bytes",
        "source_evidence",
        "stage_durations_ms",
        "third_party_repository_code_execution_count",
        "workload_id",
    }
)
_EXPECTED_SOURCE_EVIDENCE_NAMES = (
    "cross_source_bundle",
    "epss_snapshot",
    "ghsa_advisory",
    "kev_snapshot",
    "nvd_cve",
    "threat_locator_manifest",
)


class RepresentativeLiveMeasurementReviewError(ValueError):
    """Reject persisted evidence that cannot authorize topology evaluation."""


def _object(value: object, *, label: str) -> dict[str, object]:
    """Require one JSON object."""
    if not isinstance(value, dict):
        raise RepresentativeLiveMeasurementReviewError(f"{label} must be a JSON object")
    return cast(dict[str, object], value)


def _array(value: object, *, label: str) -> list[object]:
    """Require one JSON array."""
    if not isinstance(value, list):
        raise RepresentativeLiveMeasurementReviewError(f"{label} must be a JSON array")
    return cast(list[object], value)


def _string(value: object, *, label: str) -> str:
    """Require one JSON string."""
    if not isinstance(value, str):
        raise RepresentativeLiveMeasurementReviewError(f"{label} must be a string")
    return value


def _integer(value: object, *, label: str) -> int:
    """Require one JSON integer without bool coercion."""
    if type(value) is not int:
        raise RepresentativeLiveMeasurementReviewError(f"{label} must be an integer")
    return value


def _require_exact_keys(
    value: Mapping[str, object],
    *,
    expected: frozenset[str],
    label: str,
) -> None:
    """Reject missing or unknown persisted fields."""
    if frozenset(value) != expected:
        raise RepresentativeLiveMeasurementReviewError(
            f"{label} must contain the exact frozen field set"
        )


def _source_evidence(value: object) -> tuple[tuple[str, str], ...]:
    """Rehydrate named source hashes from canonical JSON rows."""
    rows = _array(value, label="source_evidence")
    admitted: list[tuple[str, str]] = []
    for index, item in enumerate(rows):
        row = _object(item, label=f"source_evidence[{index}]")
        _require_exact_keys(
            row,
            expected=frozenset({"name", "sha256"}),
            label=f"source_evidence[{index}]",
        )
        admitted.append(
            (
                _string(row["name"], label=f"source_evidence[{index}].name"),
                _string(row["sha256"], label=f"source_evidence[{index}].sha256"),
            )
        )
    return tuple(admitted)


def _stage_durations(value: object) -> tuple[tuple[str, int], ...]:
    """Rehydrate ordered stage durations from canonical JSON rows."""
    rows = _array(value, label="stage_durations_ms")
    admitted: list[tuple[str, int]] = []
    for index, item in enumerate(rows):
        row = _object(item, label=f"stage_durations_ms[{index}]")
        _require_exact_keys(
            row,
            expected=frozenset({"duration_ms", "stage"}),
            label=f"stage_durations_ms[{index}]",
        )
        admitted.append(
            (
                _string(row["stage"], label=f"stage_durations_ms[{index}].stage"),
                _integer(
                    row["duration_ms"],
                    label=f"stage_durations_ms[{index}].duration_ms",
                ),
            )
        )
    return tuple(admitted)


def _provider_totals(value: object) -> tuple[tuple[str, int], ...]:
    """Rehydrate ordered provider totals without changing measurement semantics."""
    rows = _array(value, label="provider_totals")
    admitted: list[tuple[str, int]] = []
    for index, item in enumerate(rows):
        row = _object(item, label=f"provider_totals[{index}]")
        _require_exact_keys(
            row,
            expected=frozenset({"metric", "value"}),
            label=f"provider_totals[{index}]",
        )
        admitted.append(
            (
                _string(row["metric"], label=f"provider_totals[{index}].metric"),
                _integer(row["value"], label=f"provider_totals[{index}].value"),
            )
        )
    return tuple(admitted)


def _provider_classifications(value: object) -> tuple[tuple[str, str], ...]:
    """Rehydrate ordered provider measurement classifications."""
    rows = _array(value, label="provider_classifications")
    admitted: list[tuple[str, str]] = []
    for index, item in enumerate(rows):
        row = _object(item, label=f"provider_classifications[{index}]")
        _require_exact_keys(
            row,
            expected=frozenset({"classification", "metric"}),
            label=f"provider_classifications[{index}]",
        )
        admitted.append(
            (
                _string(
                    row["metric"],
                    label=f"provider_classifications[{index}].metric",
                ),
                _string(
                    row["classification"],
                    label=f"provider_classifications[{index}].classification",
                ),
            )
        )
    return tuple(admitted)


def parse_representative_live_measurement_artifact(
    serialized: bytes,
) -> RepresentativeLiveMeasurementArtifact:
    """Rehydrate one persisted artifact only when its bytes remain canonical."""
    if type(serialized) is not bytes or not serialized:
        raise RepresentativeLiveMeasurementReviewError(
            "persisted live measurement artifact must be non-empty bytes"
        )
    try:
        parsed = cast(object, json.loads(serialized.decode("utf-8")))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RepresentativeLiveMeasurementReviewError(
            "persisted live measurement artifact must be valid UTF-8 JSON"
        ) from exc
    root = _object(parsed, label="live measurement artifact")
    _require_exact_keys(
        root,
        expected=_EXPECTED_JSON_KEYS,
        label="live measurement artifact",
    )

    try:
        artifact = RepresentativeLiveMeasurementArtifact(
            opslens_commit_sha=_string(
                root["opslens_commit_sha"], label="opslens_commit_sha"
            ),
            run_timestamp_utc=_string(
                root["run_timestamp_utc"], label="run_timestamp_utc"
            ),
            repository_url=_string(root["repository_url"], label="repository_url"),
            repository_commit_sha=_string(
                root["repository_commit_sha"], label="repository_commit_sha"
            ),
            source_evidence=_source_evidence(root["source_evidence"]),
            bedrock_knowledge_base_id=_string(
                root["bedrock_knowledge_base_id"],
                label="bedrock_knowledge_base_id",
            ),
            model_id=_string(root["model_id"], label="model_id"),
            run_id=_string(root["run_id"], label="run_id"),
            workload_id=_string(root["workload_id"], label="workload_id"),
            end_to_end_duration_ms=_integer(
                root["end_to_end_duration_ms"], label="end_to_end_duration_ms"
            ),
            stage_durations_ms=_stage_durations(root["stage_durations_ms"]),
            provider_totals=_provider_totals(root["provider_totals"]),
            provider_classifications=_provider_classifications(
                root["provider_classifications"]
            ),
            serialized_result_bytes=_integer(
                root["serialized_result_bytes"], label="serialized_result_bytes"
            ),
            final_result_sha256=_string(
                root["final_result_sha256"], label="final_result_sha256"
            ),
            public_endpoint_count=_integer(
                root["public_endpoint_count"], label="public_endpoint_count"
            ),
            new_aws_resource_count=_integer(
                root["new_aws_resource_count"], label="new_aws_resource_count"
            ),
            new_iam_role_policy_count=_integer(
                root["new_iam_role_policy_count"],
                label="new_iam_role_policy_count",
            ),
            third_party_repository_code_execution_count=_integer(
                root["third_party_repository_code_execution_count"],
                label="third_party_repository_code_execution_count",
            ),
            schema_version=_integer(root["schema_version"], label="schema_version"),
            artifact_type=_string(root["artifact_type"], label="artifact_type"),
            outcome=_string(root["outcome"], label="outcome"),
        )
    except RepresentativeLiveMeasurementArtifactError as exc:
        raise RepresentativeLiveMeasurementReviewError(str(exc)) from exc

    if artifact.serialize() != serialized:
        raise RepresentativeLiveMeasurementReviewError(
            "persisted live measurement artifact must use exact canonical serialization"
        )
    return artifact


def _expected_provider_classifications() -> tuple[tuple[str, str], ...]:
    """Return the frozen Gate 19.2 evidence semantics in provider metric order."""
    return tuple(
        (
            metric.value,
            (
                MeasurementClassification.NOT_APPLICABLE.value
                if metric
                in {
                    ProviderResourceMetric.ATHENA_QUERY_COUNT,
                    ProviderResourceMetric.ATHENA_BYTES_SCANNED,
                }
                else (
                    MeasurementClassification.UNMEASURED.value
                    if metric is ProviderResourceMetric.THROTTLE_COUNT
                    else MeasurementClassification.MEASURED.value
                )
            ),
        )
        for metric in PROVIDER_RESOURCE_METRICS
    )


def review_representative_live_measurement_artifact(
    serialized: bytes,
    *,
    expected_opslens_commit_sha: str,
) -> RepresentativeLiveMeasurementArtifact:
    """Admit persisted evidence for topology evaluation without invoking providers."""
    if _GIT_SHA_RE.fullmatch(expected_opslens_commit_sha) is None:
        raise RepresentativeLiveMeasurementReviewError(
            "expected_opslens_commit_sha must be one lowercase full Git SHA"
        )
    artifact = parse_representative_live_measurement_artifact(serialized)

    if artifact.opslens_commit_sha != expected_opslens_commit_sha:
        raise RepresentativeLiveMeasurementReviewError(
            "persisted evidence is bound to a different OpsLens commit"
        )
    if artifact.repository_url != FROZEN_REPRESENTATIVE_REPOSITORY_URL:
        raise RepresentativeLiveMeasurementReviewError(
            "persisted repository URL drifted from the frozen representative anchor"
        )
    if artifact.repository_commit_sha != FROZEN_REPRESENTATIVE_REPOSITORY_COMMIT:
        raise RepresentativeLiveMeasurementReviewError(
            "persisted repository commit drifted from the frozen representative anchor"
        )
    if (
        artifact.bedrock_knowledge_base_id
        != FROZEN_REPRESENTATIVE_BEDROCK_KNOWLEDGE_BASE_ID
    ):
        raise RepresentativeLiveMeasurementReviewError(
            "persisted Knowledge Base id drifted from the retained Gate 19.2 resource"
        )
    if artifact.model_id != BEDROCK_SYNTHESIS_MODEL_ID:
        raise RepresentativeLiveMeasurementReviewError(
            "persisted model id drifted from the retained synthesis model"
        )
    if artifact.workload_id != REPRESENTATIVE_PUBLIC_ANALYSIS_WORKLOAD_ID:
        raise RepresentativeLiveMeasurementReviewError(
            "persisted workload id drifted from the frozen representative workload"
        )
    if tuple(name for name, _digest in artifact.source_evidence) != (
        _EXPECTED_SOURCE_EVIDENCE_NAMES
    ):
        raise RepresentativeLiveMeasurementReviewError(
            "persisted source-evidence identity set drifted from the live CLI contract"
        )
    if artifact.provider_classifications != _expected_provider_classifications():
        raise RepresentativeLiveMeasurementReviewError(
            "persisted provider measurement classifications drifted"
        )
    return artifact


__all__ = [
    "FROZEN_REPRESENTATIVE_BEDROCK_KNOWLEDGE_BASE_ID",
    "RepresentativeLiveMeasurementReviewError",
    "parse_representative_live_measurement_artifact",
    "review_representative_live_measurement_artifact",
]
