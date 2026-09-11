"""Tests for deterministic review of persisted Gate 19.2 live evidence."""

from __future__ import annotations

import json
from dataclasses import replace

import pytest

from opslens.knowledge_retrieval.application.bedrock_synthesis import (
    BEDROCK_SYNTHESIS_MODEL_ID,
)
from opslens.public_analysis.application.representative_live_measurement_artifact import (
    RepresentativeLiveMeasurementArtifact,
)
from opslens.public_analysis.application.representative_live_measurement_review import (
    FROZEN_REPRESENTATIVE_BEDROCK_KNOWLEDGE_BASE_ID,
    RepresentativeLiveMeasurementReviewError,
    parse_representative_live_measurement_artifact,
    review_representative_live_measurement_artifact,
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
    RepresentativeWorkloadStage,
)

_OPSLENS_SHA = "a" * 40
_DIGESTS = tuple(character * 64 for character in "abcdef")


def _classifications() -> tuple[tuple[str, str], ...]:
    """Return the exact frozen Gate 19.2 provider evidence semantics."""
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


def _artifact() -> RepresentativeLiveMeasurementArtifact:
    """Build one canonical frozen-anchor artifact without provider execution."""
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
        opslens_commit_sha=_OPSLENS_SHA,
        run_timestamp_utc="2026-09-11T12:20:00Z",
        repository_url=FROZEN_REPRESENTATIVE_REPOSITORY_URL,
        repository_commit_sha=FROZEN_REPRESENTATIVE_REPOSITORY_COMMIT,
        source_evidence=(
            ("cross_source_bundle", _DIGESTS[0]),
            ("epss_snapshot", _DIGESTS[1]),
            ("ghsa_advisory", _DIGESTS[2]),
            ("kev_snapshot", _DIGESTS[3]),
            ("nvd_cve", _DIGESTS[4]),
            ("threat_locator_manifest", _DIGESTS[5]),
        ),
        bedrock_knowledge_base_id=FROZEN_REPRESENTATIVE_BEDROCK_KNOWLEDGE_BASE_ID,
        model_id=BEDROCK_SYNTHESIS_MODEL_ID,
        run_id="gate19.2-live-20260911T122000Z",
        workload_id=REPRESENTATIVE_PUBLIC_ANALYSIS_WORKLOAD_ID,
        end_to_end_duration_ms=240,
        stage_durations_ms=tuple(
            (stage.value, index + 1)
            for index, stage in enumerate(RepresentativeWorkloadStage)
        ),
        provider_totals=totals,
        provider_classifications=_classifications(),
        serialized_result_bytes=4096,
        final_result_sha256=_DIGESTS[0],
    )


def test_canonical_persisted_artifact_is_admitted_for_topology_evaluation() -> None:
    """Rehydrate canonical bytes and preserve the exact reviewed execution commit."""
    artifact = _artifact()

    reviewed = review_representative_live_measurement_artifact(
        artifact.serialize(),
        expected_opslens_commit_sha=_OPSLENS_SHA,
    )

    assert reviewed == artifact
    assert parse_representative_live_measurement_artifact(artifact.serialize()) == artifact


def test_non_canonical_json_is_rejected_even_when_semantically_equivalent() -> None:
    """Prevent pretty-print or key-order rewrites from becoming equivalent evidence."""
    artifact = _artifact()
    non_canonical = (
        json.dumps(artifact.to_json_dict(), indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")

    with pytest.raises(
        RepresentativeLiveMeasurementReviewError,
        match="canonical serialization",
    ):
        review_representative_live_measurement_artifact(
            non_canonical,
            expected_opslens_commit_sha=_OPSLENS_SHA,
        )


def test_opslens_commit_drift_is_rejected() -> None:
    """Bind the persisted measurement to the exact reviewed execution commit."""
    with pytest.raises(
        RepresentativeLiveMeasurementReviewError,
        match="different OpsLens commit",
    ):
        review_representative_live_measurement_artifact(
            _artifact().serialize(),
            expected_opslens_commit_sha="b" * 40,
        )


def test_repository_anchor_drift_is_rejected() -> None:
    """Do not admit a different repository merely because its artifact shape is valid."""
    drifted = replace(
        _artifact(),
        repository_url="https://github.com/example/other",
    )

    with pytest.raises(
        RepresentativeLiveMeasurementReviewError,
        match="repository URL drifted",
    ):
        review_representative_live_measurement_artifact(
            drifted.serialize(),
            expected_opslens_commit_sha=_OPSLENS_SHA,
        )


def test_source_evidence_identity_drift_is_rejected() -> None:
    """Require the exact six content identities emitted by the retained live CLI."""
    drifted = replace(
        _artifact(),
        source_evidence=(
            ("cross_source_bundle", _DIGESTS[0]),
            ("epss_snapshot", _DIGESTS[1]),
            ("ghsa_advisory", _DIGESTS[2]),
            ("kev_snapshot", _DIGESTS[3]),
            ("nvd_record", _DIGESTS[4]),
            ("threat_locator_manifest", _DIGESTS[5]),
        ),
    )

    with pytest.raises(
        RepresentativeLiveMeasurementReviewError,
        match="source-evidence identity set drifted",
    ):
        review_representative_live_measurement_artifact(
            drifted.serialize(),
            expected_opslens_commit_sha=_OPSLENS_SHA,
        )


def test_provider_classification_drift_is_rejected() -> None:
    """Keep UNMEASURED and NOT_APPLICABLE semantics independent of numeric totals."""
    classifications = dict(_artifact().provider_classifications)
    classifications[ProviderResourceMetric.THROTTLE_COUNT.value] = (
        MeasurementClassification.MEASURED.value
    )
    drifted = replace(
        _artifact(),
        provider_classifications=tuple(
            (metric.value, classifications[metric.value])
            for metric in PROVIDER_RESOURCE_METRICS
        ),
    )

    with pytest.raises(
        RepresentativeLiveMeasurementReviewError,
        match="provider measurement classifications drifted",
    ):
        review_representative_live_measurement_artifact(
            drifted.serialize(),
            expected_opslens_commit_sha=_OPSLENS_SHA,
        )


def test_unknown_persisted_field_is_rejected() -> None:
    """Reject post-hoc extension of the immutable v1 evidence shape."""
    artifact = _artifact()
    payload = artifact.to_json_dict()
    payload["unexpected"] = True
    serialized = (
        json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        + "\n"
    ).encode("utf-8")

    with pytest.raises(
        RepresentativeLiveMeasurementReviewError,
        match="exact frozen field set",
    ):
        parse_representative_live_measurement_artifact(serialized)
