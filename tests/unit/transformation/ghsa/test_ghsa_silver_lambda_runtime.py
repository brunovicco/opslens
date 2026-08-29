"""Tests for GHSA Silver Lambda invocation and runtime orchestration."""

from collections.abc import Mapping
from contextlib import AbstractContextManager, nullcontext

import pytest

from opslens.transformation.ghsa.adapters.inbound.invocation import (
    GhsaSilverInvocationParserV1,
    InvalidGhsaSilverInvocationError,
)
from opslens.transformation.ghsa.application.runtime_models import (
    GhsaSilverRuntimeRequestV1,
    GhsaSilverRuntimeResultV1,
)
from opslens.transformation.ghsa.completion.key_factory import GhsaSilverKeyFactoryV1
from opslens.transformation.ghsa.completion.manifest import (
    GhsaSilverCompletionManifestFactoryV1,
    GhsaSilverCompletionManifestSerializerV1,
)
from opslens.transformation.ghsa.completion.models import (
    GhsaSilverStoredCompletionV1,
)
from opslens.transformation.ghsa.completion.service import (
    GhsaSilverPersistenceResultV1,
)
from opslens.transformation.ghsa.lambda_handler import (
    execute_transformation_request,
)
from opslens.transformation.ghsa.runtime.materializer import (
    GhsaSilverAttemptContextV1,
    GhsaSilverMaterializationV1,
    GhsaSilverMaterializerV1,
)
from opslens.transformation.ghsa.runtime.processor import (
    GhsaSilverRuntimeProcessorV1,
)
from opslens.transformation.ghsa.serialization.logical_hash import (
    GhsaLogicalRecordSetHasherV1,
)

SYNC_ID = "1" * 64
ATTEMPT_ID = "2" * 64
MANIFEST_KEY = (
    "bronze/ghsa/advisories/"
    "mode=published/"
    f"sync_id={SYNC_ID}/"
    f"attempt_id={ATTEMPT_ID}/"
    "manifest.json"
)
MANIFEST_VERSION_ID = "bronze-manifest-version"


class RecordingTelemetry:
    """Record telemetry emitted by the Lambda execution boundary."""

    def __init__(self) -> None:
        """Initialize event collections."""
        self.info_events: list[tuple[str, Mapping[str, object] | None]] = []
        self.exception_events: list[
            tuple[str, Mapping[str, object] | None]
        ] = []
        self.metrics: list[tuple[str, float, str]] = []
        self.spans: list[str] = []

    def info(
        self,
        message: str,
        *,
        fields: Mapping[str, object] | None = None,
    ) -> None:
        """Record one informational event."""
        self.info_events.append((message, fields))

    def exception(
        self,
        message: str,
        *,
        fields: Mapping[str, object] | None = None,
    ) -> None:
        """Record one exception event."""
        self.exception_events.append((message, fields))

    def metric(self, name: str, value: float, unit: str) -> None:
        """Record one metric sample."""
        self.metrics.append((name, value, unit))

    def span(self, name: str) -> AbstractContextManager[object]:
        """Record one span and return a no-op context manager."""
        self.spans.append(name)
        return nullcontext(object())


class FakePreparationService:
    """Return one configured logical materialization."""

    def __init__(self, materialization: GhsaSilverMaterializationV1) -> None:
        """Initialize preparation fixture."""
        self._materialization = materialization
        self.calls: list[tuple[str, str]] = []

    def prepare(
        self,
        *,
        manifest_key: str,
        manifest_version_id: str,
    ) -> GhsaSilverMaterializationV1:
        """Record exact requested coordinates and return the fixture."""
        self.calls.append((manifest_key, manifest_version_id))
        return self._materialization


class FakePersistenceService:
    """Return one configured exact persistence result."""

    def __init__(self, result: GhsaSilverPersistenceResultV1) -> None:
        """Initialize persistence fixture."""
        self._result = result
        self.calls: list[GhsaSilverMaterializationV1] = []

    def persist(
        self,
        materialization: GhsaSilverMaterializationV1,
    ) -> GhsaSilverPersistenceResultV1:
        """Record logical materialization and return stored evidence."""
        self.calls.append(materialization)
        return self._result


class FakeLambdaProcessor:
    """Return one configured runtime result at the Lambda boundary."""

    def __init__(
        self,
        result: GhsaSilverRuntimeResultV1 | None = None,
        error: Exception | None = None,
    ) -> None:
        """Initialize processor fixture."""
        self._result = result
        self._error = error
        self.calls: list[GhsaSilverRuntimeRequestV1] = []

    def process(
        self,
        request: GhsaSilverRuntimeRequestV1,
    ) -> GhsaSilverRuntimeResultV1:
        """Return configured completion evidence or raise configured failure."""
        self.calls.append(request)

        if self._error is not None:
            raise self._error

        if self._result is None:
            raise AssertionError("Fake Lambda processor requires a result.")

        return self._result


def _materialization() -> GhsaSilverMaterializationV1:
    """Build one valid zero-result logical attempt."""
    context = GhsaSilverAttemptContextV1(
        sync_id=SYNC_ID,
        attempt_id=ATTEMPT_ID,
        manifest_key=MANIFEST_KEY,
        manifest_version_id=MANIFEST_VERSION_ID,
    )

    return GhsaSilverMaterializerV1(
        logical_hasher=GhsaLogicalRecordSetHasherV1(),
    ).materialize(context=context, bindings=())


def _persistence_result(
    materialization: GhsaSilverMaterializationV1,
) -> GhsaSilverPersistenceResultV1:
    """Build exact COMPLETE persistence evidence for one empty attempt."""
    key_factory = GhsaSilverKeyFactoryV1()
    manifest = GhsaSilverCompletionManifestFactoryV1(
        key_factory=key_factory,
    ).build(
        materialization=materialization,
        stored_objects=(),
    )
    artifact = GhsaSilverCompletionManifestSerializerV1(
        key_factory=key_factory,
    ).serialize(manifest)
    stored = GhsaSilverStoredCompletionV1(
        key=artifact.key,
        version_id="complete-version",
        sha256=artifact.manifest_sha256,
        size_bytes=len(artifact.manifest_bytes),
    )

    return GhsaSilverPersistenceResultV1(
        materialization=materialization,
        stored_content_objects=(),
        completion_artifact=artifact,
        stored_completion=stored,
    )


def _runtime_result() -> GhsaSilverRuntimeResultV1:
    """Build bounded exact Lambda completion evidence."""
    return GhsaSilverRuntimeResultV1(
        sync_id=SYNC_ID,
        attempt_id=ATTEMPT_ID,
        bronze_manifest_key=MANIFEST_KEY,
        bronze_manifest_version_id=MANIFEST_VERSION_ID,
        logical_record_set_sha256="3" * 64,
        silver_complete_key="silver/ghsa/completions/manifest.json",
        silver_complete_version_id="complete-version",
        silver_complete_sha256="4" * 64,
        row_count=0,
        content_object_count=0,
    )


def test_invocation_accepts_only_exact_manifest_coordinate() -> None:
    """Parse the minimal versioned runtime envelope."""
    request = GhsaSilverInvocationParserV1().parse(
        {
            "schema_version": "1",
            "manifest_key": MANIFEST_KEY,
            "manifest_version_id": MANIFEST_VERSION_ID,
        }
    )

    assert request.manifest_key == MANIFEST_KEY
    assert request.manifest_version_id == MANIFEST_VERSION_ID


@pytest.mark.parametrize(
    "event",
    [
        {
            "schema_version": "2",
            "manifest_key": MANIFEST_KEY,
            "manifest_version_id": MANIFEST_VERSION_ID,
        },
        {
            "schema_version": "1",
            "manifest_key": "bronze/nvd/cve/manifest.json",
            "manifest_version_id": MANIFEST_VERSION_ID,
        },
        {
            "schema_version": "1",
            "manifest_key": MANIFEST_KEY,
            "manifest_version_id": MANIFEST_VERSION_ID,
            "mode": "published",
        },
    ],
)
def test_invocation_rejects_competing_or_invalid_fields(
    event: dict[str, object],
) -> None:
    """Reject unsupported authority and invalid Bronze coordinates."""
    with pytest.raises(InvalidGhsaSilverInvocationError):
        GhsaSilverInvocationParserV1().parse(event)


def test_runtime_processor_preserves_exact_invocation_and_complete_evidence() -> None:
    """Bind invocation, logical preparation, persistence, and COMPLETE result."""
    materialization = _materialization()
    persisted = _persistence_result(materialization)
    preparation = FakePreparationService(materialization)
    persistence = FakePersistenceService(persisted)
    processor = GhsaSilverRuntimeProcessorV1(
        preparation_service=preparation,
        persistence_service=persistence,
    )
    request = GhsaSilverRuntimeRequestV1(
        manifest_key=MANIFEST_KEY,
        manifest_version_id=MANIFEST_VERSION_ID,
    )

    result = processor.process(request)

    assert preparation.calls == [(MANIFEST_KEY, MANIFEST_VERSION_ID)]
    assert persistence.calls == [materialization]
    assert result.sync_id == SYNC_ID
    assert result.attempt_id == ATTEMPT_ID
    assert result.bronze_manifest_key == MANIFEST_KEY
    assert result.bronze_manifest_version_id == MANIFEST_VERSION_ID
    assert result.logical_record_set_sha256 == (
        materialization.logical_record_set_sha256
    )
    assert result.silver_complete_key == persisted.stored_completion.key
    assert result.silver_complete_version_id == "complete-version"
    assert result.row_count == 0
    assert result.content_object_count == 0


def test_lambda_execution_returns_bounded_complete_evidence() -> None:
    """Return COMPLETE authority without an unbounded content-object listing."""
    runtime_result = _runtime_result()
    processor = FakeLambdaProcessor(result=runtime_result)
    telemetry = RecordingTelemetry()
    request = GhsaSilverRuntimeRequestV1(
        manifest_key=MANIFEST_KEY,
        manifest_version_id=MANIFEST_VERSION_ID,
    )

    response = execute_transformation_request(
        request=request,
        processor=processor,
        telemetry=telemetry,
        request_id="request-123",
    )

    assert response == {
        "request_id": "request-123",
        "status": "complete",
        "sync_id": SYNC_ID,
        "attempt_id": ATTEMPT_ID,
        "bronze_manifest_key": MANIFEST_KEY,
        "bronze_manifest_version_id": MANIFEST_VERSION_ID,
        "logical_record_set_sha256": "3" * 64,
        "silver_complete_key": "silver/ghsa/completions/manifest.json",
        "silver_complete_version_id": "complete-version",
        "silver_complete_sha256": "4" * 64,
        "row_count": 0,
        "content_object_count": 0,
    }
    assert processor.calls == [request]
    assert (
        "GhsaSilverTransformationSuccess",
        1.0,
        "Count",
    ) in telemetry.metrics


def test_lambda_execution_records_failure_without_fabricating_result() -> None:
    """Propagate processing failures while recording bounded telemetry."""
    processor = FakeLambdaProcessor(error=RuntimeError("persist failed"))
    telemetry = RecordingTelemetry()
    request = GhsaSilverRuntimeRequestV1(
        manifest_key=MANIFEST_KEY,
        manifest_version_id=MANIFEST_VERSION_ID,
    )

    with pytest.raises(RuntimeError, match="persist failed"):
        execute_transformation_request(
            request=request,
            processor=processor,
            telemetry=telemetry,
            request_id="request-123",
        )

    assert (
        "GhsaSilverTransformationFailure",
        1.0,
        "Count",
    ) in telemetry.metrics
