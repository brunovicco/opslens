"""Tests for bounded Gate 19.2 live-measurement evidence artifacts."""

from dataclasses import replace

import pytest

from opslens.public_analysis.application.representative_live_measurement_artifact import (
    RepresentativeLiveMeasurementArtifact,
    RepresentativeLiveMeasurementArtifactError,
    admit_serialized_representative_live_measurement_artifact,
)
from opslens.public_analysis.domain import (
    PROVIDER_RESOURCE_METRICS,
    MeasurementClassification,
    ProviderResourceMetric,
    RepresentativeWorkloadStage,
)

_DIGEST_A = "a" * 64
_DIGEST_B = "b" * 64
_GIT_SHA = "c" * 40
_REPOSITORY_SHA = "d" * 40


def _artifact() -> RepresentativeLiveMeasurementArtifact:
    """Build one deterministic successful artifact without any provider execution."""
    classifications = tuple(
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
    totals = tuple(
        (
            metric.value,
            {
                ProviderResourceMetric.GITHUB_HTTP_REQUEST_COUNT: 4,
                ProviderResourceMetric.BEDROCK_RETRIEVE_COUNT: 1,
                ProviderResourceMetric.BEDROCK_RETRIEVE_CLIENT_ELAPSED_MS: 31,
                ProviderResourceMetric.BEDROCK_MODEL_CALL_COUNT: 1,
                ProviderResourceMetric.BEDROCK_INPUT_TOKENS: 120,
                ProviderResourceMetric.BEDROCK_OUTPUT_TOKENS: 42,
                ProviderResourceMetric.BEDROCK_MODEL_CLIENT_ELAPSED_MS: 85,
                ProviderResourceMetric.BEDROCK_MODEL_LATENCY_MS: 70,
            }.get(metric, 0),
        )
        for metric in PROVIDER_RESOURCE_METRICS
    )
    return RepresentativeLiveMeasurementArtifact(
        opslens_commit_sha=_GIT_SHA,
        run_timestamp_utc="2026-09-11T04:20:00Z",
        repository_url="https://github.com/openedx/mockprock",
        repository_commit_sha=_REPOSITORY_SHA,
        source_evidence=(
            ("cross_source_bundle", _DIGEST_A),
            ("threat_locator_manifest", _DIGEST_B),
        ),
        bedrock_knowledge_base_id="BTVJ2PBR2A",
        model_id="us.amazon.nova-pro-v1:0",
        run_id="gate19.2-live-001",
        workload_id="public-analysis-workload:v1",
        end_to_end_duration_ms=240,
        stage_durations_ms=tuple(
            (stage.value, index + 1)
            for index, stage in enumerate(RepresentativeWorkloadStage)
        ),
        provider_totals=totals,
        provider_classifications=classifications,
        serialized_result_bytes=4096,
        final_result_sha256=_DIGEST_A,
    )


def test_serialization_is_deterministic_and_round_trip_admitted() -> None:
    """Preserve explicit classifications and canonical bytes exactly."""
    artifact = _artifact()

    serialized = artifact.serialize()

    assert serialized == artifact.serialize()
    assert serialized.endswith(b"\n")
    assert admit_serialized_representative_live_measurement_artifact(
        serialized,
        expected=artifact,
    ) is artifact
    classifications = dict(artifact.provider_classifications)
    assert classifications["athena_query_count"] == (
        MeasurementClassification.NOT_APPLICABLE.value
    )
    assert classifications["athena_bytes_scanned"] == (
        MeasurementClassification.NOT_APPLICABLE.value
    )
    assert classifications["throttle_count"] == MeasurementClassification.UNMEASURED.value


def test_serialized_artifact_drift_fails_closed() -> None:
    """Reject any byte-level mutation instead of treating it as equivalent evidence."""
    artifact = _artifact()
    serialized = artifact.serialize().replace(_DIGEST_A.encode(), _DIGEST_B.encode(), 1)

    with pytest.raises(
        RepresentativeLiveMeasurementArtifactError,
        match="does not match admitted evidence",
    ):
        admit_serialized_representative_live_measurement_artifact(
            serialized,
            expected=artifact,
        )


def test_stage_order_drift_is_rejected() -> None:
    """Keep the exact nine-stage measurement order authoritative."""
    artifact = _artifact()
    reordered = tuple(reversed(artifact.stage_durations_ms))

    with pytest.raises(
        RepresentativeLiveMeasurementArtifactError,
        match="exact representative stage order",
    ):
        replace(artifact, stage_durations_ms=reordered)


@pytest.mark.parametrize(
    ("field_name", "value", "error"),
    [
        ("opslens_commit_sha", "bad", "40-hex"),
        ("repository_commit_sha", "bad", "40-hex"),
        ("run_timestamp_utc", "2026-09-11T04:20:00+00:00", "UTC Z notation"),
        ("final_result_sha256", "bad", "SHA-256"),
        ("public_endpoint_count", 1, "exactly zero"),
        ("new_aws_resource_count", 1, "exactly zero"),
        ("new_iam_role_policy_count", 1, "exactly zero"),
        ("third_party_repository_code_execution_count", 1, "exactly zero"),
    ],
)
def test_invalid_identity_or_mutation_evidence_is_rejected(
    field_name: str,
    value: object,
    error: str,
) -> None:
    """Reject malformed identity and every non-zero prohibited-mutation count."""
    artifact = _artifact()

    with pytest.raises(RepresentativeLiveMeasurementArtifactError, match=error):
        replace(artifact, **{field_name: value})


def test_source_evidence_must_be_sorted_unique_sha256_pairs() -> None:
    """Prevent ambiguous or unstable source-evidence identity serialization."""
    artifact = _artifact()

    with pytest.raises(RepresentativeLiveMeasurementArtifactError, match="sorted"):
        replace(
            artifact,
            source_evidence=(
                ("threat_locator_manifest", _DIGEST_B),
                ("cross_source_bundle", _DIGEST_A),
            ),
        )

    with pytest.raises(RepresentativeLiveMeasurementArtifactError, match="unique"):
        replace(
            artifact,
            source_evidence=(
                ("cross_source_bundle", _DIGEST_A),
                ("cross_source_bundle", _DIGEST_B),
            ),
        )
