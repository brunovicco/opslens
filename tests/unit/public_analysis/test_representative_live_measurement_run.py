"""Tests for one-shot human live-measurement execution and artifact admission."""

from __future__ import annotations

from typing import cast

import pytest

from opslens.knowledge_retrieval.application.bedrock_synthesis import BEDROCK_SYNTHESIS_MODEL_ID
from opslens.public_analysis.application.representative_live_measurement_run import (
    FROZEN_REPRESENTATIVE_REPOSITORY_COMMIT,
    FROZEN_REPRESENTATIVE_REPOSITORY_URL,
    RepresentativeLiveMeasurementRunError,
    RepresentativeLiveRunMetadata,
    execute_representative_live_measurement,
)
from opslens.public_analysis.application.representative_workload_execution import (
    REPRESENTATIVE_DEFAULT_PROVIDER_COVERAGE,
    RepresentativeWorkloadDependencies,
    RepresentativeWorkloadExecution,
)
from opslens.public_analysis.domain import (
    MeasurementClassification,
    ProviderResourceMetric,
    ProviderResourceUsage,
    RepresentativePublicAnalysisResult,
    RepresentativeStageMeasurement,
    RepresentativeWorkloadMeasurement,
    RepresentativeWorkloadStage,
)

_RESULT_BYTES = b'{"outcome":"completed"}\n'


class _FakeResult:
    """Expose only deterministic serialized bytes needed by artifact admission."""

    def serialize(self) -> bytes:
        """Return one stable admitted-result representation."""
        return _RESULT_BYTES


class RecordingExecutor:
    """Record one exact workload invocation and return a typed offline execution sentinel."""

    def __init__(self, execution: RepresentativeWorkloadExecution) -> None:
        """Store the deterministic result returned by this injected execution port."""
        self.execution = execution
        self.call_count = 0
        self.raw_body: bytes | None = None

    def __call__(
        self,
        *,
        run_id: str,
        raw_body: bytes,
        dependencies: RepresentativeWorkloadDependencies,
    ) -> RepresentativeWorkloadExecution:
        """Record one invocation without provider I/O."""
        assert run_id == "gate19.2-live-test-001"
        assert type(dependencies) is RepresentativeWorkloadDependencies
        self.call_count += 1
        self.raw_body = raw_body
        return self.execution


class FailingExecutor:
    """Model one provider/admission failure before any artifact can be returned."""

    def __init__(self) -> None:
        """Initialize exact invocation count."""
        self.call_count = 0

    def __call__(
        self,
        *,
        run_id: str,
        raw_body: bytes,
        dependencies: RepresentativeWorkloadDependencies,
    ) -> RepresentativeWorkloadExecution:
        """Fail closed instead of manufacturing a partial measurement."""
        del run_id, raw_body, dependencies
        self.call_count += 1
        raise RuntimeError("provider boundary failed")


def _metadata(**overrides: object) -> RepresentativeLiveRunMetadata:
    """Build one exact frozen run metadata record with optional test drift."""
    values: dict[str, object] = {
        "run_id": "gate19.2-live-test-001",
        "opslens_commit_sha": "a" * 40,
        "run_timestamp_utc": "2026-09-11T12:00:00Z",
        "repository_url": FROZEN_REPRESENTATIVE_REPOSITORY_URL,
        "requested_ref": FROZEN_REPRESENTATIVE_REPOSITORY_COMMIT,
        "repository_commit_sha": FROZEN_REPRESENTATIVE_REPOSITORY_COMMIT,
        "source_evidence": (
            ("cross_source_bundle", "b" * 64),
            ("epss_snapshot", "c" * 64),
            ("kev_snapshot", "d" * 64),
            ("threat_locator_manifest", "e" * 64),
        ),
        "bedrock_knowledge_base_id": "BTVJ2PBR2A",
        "model_id": BEDROCK_SYNTHESIS_MODEL_ID,
    }
    values.update(overrides)
    return RepresentativeLiveRunMetadata(
        run_id=cast(str, values["run_id"]),
        opslens_commit_sha=cast(str, values["opslens_commit_sha"]),
        run_timestamp_utc=cast(str, values["run_timestamp_utc"]),
        repository_url=cast(str, values["repository_url"]),
        requested_ref=cast(str, values["requested_ref"]),
        repository_commit_sha=cast(str, values["repository_commit_sha"]),
        source_evidence=cast(tuple[tuple[str, str], ...], values["source_evidence"]),
        bedrock_knowledge_base_id=cast(str, values["bedrock_knowledge_base_id"]),
        model_id=cast(str, values["model_id"]),
    )


def _execution() -> RepresentativeWorkloadExecution:
    """Create exact typed execution evidence without reproducing the nine-stage fixture graph."""
    stages = tuple(
        RepresentativeStageMeasurement(
            stage=stage,
            duration_ms=1,
            usage=ProviderResourceUsage(),
        )
        for stage in RepresentativeWorkloadStage
    )
    measurement = RepresentativeWorkloadMeasurement(
        run_id="gate19.2-live-test-001",
        workload_id="public-analysis-workload:v1",
        stage_measurements=stages,
        end_to_end_duration_ms=10,
        serialized_result_bytes=len(_RESULT_BYTES),
        provider_totals=ProviderResourceUsage(),
        provider_coverage=REPRESENTATIVE_DEFAULT_PROVIDER_COVERAGE,
    )
    execution = object.__new__(RepresentativeWorkloadExecution)
    object.__setattr__(
        execution,
        "result",
        cast(RepresentativePublicAnalysisResult, _FakeResult()),
    )
    object.__setattr__(execution, "measurement", measurement)
    return execution


def _dependencies() -> RepresentativeWorkloadDependencies:
    """Create one exact-type dependency sentinel that the injected executor never dereferences."""
    return object.__new__(RepresentativeWorkloadDependencies)


def test_executes_exactly_once_and_admits_canonical_live_artifact() -> None:
    """Execute one workload call then preserve frozen classification semantics in the artifact."""
    executor = RecordingExecutor(_execution())

    run = execute_representative_live_measurement(
        metadata=_metadata(),
        dependencies=_dependencies(),
        executor=executor,
    )

    assert executor.call_count == 1
    assert executor.raw_body == (
        b'{"repository_url":"https://github.com/openedx/mockprock",'
        b'"requested_ref":"18c954d8604df4740c829ba17fa2f3640b92b900"}'
    )
    assert run.serialized_artifact == run.artifact.serialize()
    classifications = dict(run.artifact.provider_classifications)
    assert classifications[ProviderResourceMetric.ATHENA_QUERY_COUNT.value] == (
        MeasurementClassification.NOT_APPLICABLE.value
    )
    assert classifications[ProviderResourceMetric.ATHENA_BYTES_SCANNED.value] == (
        MeasurementClassification.NOT_APPLICABLE.value
    )
    assert classifications[ProviderResourceMetric.THROTTLE_COUNT.value] == (
        MeasurementClassification.UNMEASURED.value
    )
    assert run.artifact.public_endpoint_count == 0
    assert run.artifact.new_aws_resource_count == 0
    assert run.artifact.new_iam_role_policy_count == 0
    assert run.artifact.third_party_repository_code_execution_count == 0


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("repository_url", "https://github.com/example/other", "repository_url"),
        ("requested_ref", "main", "requested_ref"),
        ("repository_commit_sha", "f" * 40, "repository_commit_sha"),
        ("model_id", "different-model", "model_id"),
    ],
)
def test_frozen_identity_drift_is_rejected_before_execution(
    field: str,
    value: object,
    message: str,
) -> None:
    """Keep repository and model drift outside the live provider execution boundary."""
    with pytest.raises(RepresentativeLiveMeasurementRunError, match=message):
        _metadata(**{field: value})


def test_executor_failure_does_not_become_partial_success() -> None:
    """Propagate workload failure without constructing fabricated success evidence."""
    executor = FailingExecutor()

    with pytest.raises(RuntimeError, match="provider boundary failed"):
        execute_representative_live_measurement(
            metadata=_metadata(),
            dependencies=_dependencies(),
            executor=executor,
        )

    assert executor.call_count == 1
