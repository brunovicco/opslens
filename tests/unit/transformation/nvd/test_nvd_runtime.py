"""Tests for NVD Silver runtime orchestration."""

from datetime import UTC, datetime
from hashlib import sha256

import pytest

from opslens.transformation.nvd.application.models import (
    NvdSilverPreparedBatchV1,
    NvdSilverTransformRequestV1,
)
from opslens.transformation.nvd.application.persistence_models import (
    NvdSilverStoredCompletionV1,
)
from opslens.transformation.nvd.application.runtime_models import (
    NvdSilverRuntimeRequestV1,
)
from opslens.transformation.nvd.completion.key_factory import (
    NvdSilverKeyFactoryV1,
)
from opslens.transformation.nvd.completion.manifest import (
    NvdSilverCompletionArtifactV1,
    NvdSilverCompletionManifestFactoryV1,
    NvdSilverCompletionManifestSerializerV1,
)
from opslens.transformation.nvd.provenance.models import (
    NvdBronzeObjectPayloadV1,
    NvdBronzeObjectReferenceV1,
    NvdBronzeObjectRole,
    VerifiedNvdBronzeEvidenceV1,
)
from opslens.transformation.nvd.runtime import (
    NvdSilverRuntimeProcessor,
)
from opslens.transformation.nvd.serialization.models import (
    NvdSilverSourceKind,
)
from opslens.transformation.nvd.serialization.parquet import (
    NvdSilverParquetSerializerV1,
)

UPDATE_ID = "a" * 64
MANIFEST_KEY = f"bronze/nvd/cve/updates/update_id={UPDATE_ID}/manifest.json"
MANIFEST_VERSION = "bronze-manifest-v1"


def _transform_request() -> NvdSilverTransformRequestV1:
    """Build one runtime transform-request envelope."""
    return NvdSilverTransformRequestV1(
        source_kind=NvdSilverSourceKind.INCREMENTAL,
        manifest_key=MANIFEST_KEY,
        manifest_version_id=MANIFEST_VERSION,
        manifest_bytes=b"manifest",
        object_payloads=(
            NvdBronzeObjectPayloadV1(
                key=(
                    f"bronze/nvd/cve/updates/update_id={UPDATE_ID}/page_start=000000/response.json"
                ),
                version_id="page-v1",
                raw_bytes=b'{"vulnerabilities":[]}',
            ),
        ),
    )


def _prepared() -> NvdSilverPreparedBatchV1:
    """Build one valid zero-result incremental prepared batch."""
    page_bytes = b'{"vulnerabilities":[]}'

    evidence = VerifiedNvdBronzeEvidenceV1(
        source_kind=NvdSilverSourceKind.INCREMENTAL,
        source_batch_id=UPDATE_ID,
        manifest_key=MANIFEST_KEY,
        manifest_version_id=MANIFEST_VERSION,
        manifest_sha256="b" * 64,
        manifest_size_bytes=100,
        objects=(
            NvdBronzeObjectReferenceV1(
                role=NvdBronzeObjectRole.PAGE,
                key=(
                    f"bronze/nvd/cve/updates/update_id={UPDATE_ID}/page_start=000000/response.json"
                ),
                version_id="page-v1",
                size_bytes=len(page_bytes),
                sha256=sha256(page_bytes).hexdigest(),
                page_start=0,
                source_timestamp="2026-08-22T12:00:00.000",
            ),
        ),
        bootstrap_feed_year=None,
        bootstrap_feed_revision=None,
        bootstrap_source_observed_at=None,
        incremental_update_id=UPDATE_ID,
        incremental_total_results=0,
        incremental_window_start_at=datetime(
            2026,
            8,
            21,
            tzinfo=UTC,
        ),
        incremental_window_end_at=datetime(
            2026,
            8,
            22,
            tzinfo=UTC,
        ),
    )

    artifact = NvdSilverParquetSerializerV1().serialize_empty(
        source_kind=NvdSilverSourceKind.INCREMENTAL,
        source_batch_id=UPDATE_ID,
    )

    return NvdSilverPreparedBatchV1(
        evidence=evidence,
        records=(),
        parquet_artifact=artifact,
        keys=NvdSilverKeyFactoryV1().build(evidence),
    )


def _completion(
    prepared: NvdSilverPreparedBatchV1,
) -> NvdSilverCompletionArtifactV1:
    """Build deterministic COMPLETE evidence from persisted Parquet."""
    manifest, keys = NvdSilverCompletionManifestFactoryV1().build(
        evidence=prepared.evidence,
        records=prepared.records,
        parquet_artifact=prepared.parquet_artifact,
        silver_object_version_id="silver-parquet-v1",
    )

    return NvdSilverCompletionManifestSerializerV1().serialize(
        manifest=manifest,
        manifest_key=keys.manifest_key,
    )


class RecordingLoader:
    """Return one configured exact transform request."""

    def __init__(
        self,
        result: NvdSilverTransformRequestV1,
    ) -> None:
        """Initialize loader output."""
        self.result = result
        self.calls = 0

    def load(
        self,
        *,
        source_kind: NvdSilverSourceKind,
        manifest_key: str,
        manifest_version_id: str,
    ) -> NvdSilverTransformRequestV1:
        """Return configured transform request."""
        self.calls += 1
        return self.result


class RecordingPrepareService:
    """Return one configured prepared batch."""

    def __init__(
        self,
        result: NvdSilverPreparedBatchV1,
    ) -> None:
        """Initialize prepared output."""
        self.result = result
        self.calls = 0

    def prepare(
        self,
        request: NvdSilverTransformRequestV1,
    ) -> NvdSilverPreparedBatchV1:
        """Return configured prepared batch."""
        self.calls += 1
        return self.result


class RecordingParquetPersistence:
    """Return one configured COMPLETE artifact."""

    def __init__(
        self,
        result: NvdSilverCompletionArtifactV1,
    ) -> None:
        """Initialize COMPLETE output."""
        self.result = result
        self.calls = 0

    def prepare_completion(
        self,
        prepared: NvdSilverPreparedBatchV1,
    ) -> NvdSilverCompletionArtifactV1:
        """Return configured COMPLETE artifact."""
        self.calls += 1
        return self.result


class RecordingCompletionPersistence:
    """Return final persisted COMPLETE evidence."""

    def __init__(
        self,
        result: NvdSilverStoredCompletionV1,
    ) -> None:
        """Initialize persisted COMPLETE output."""
        self.result = result
        self.calls = 0

    def persist(
        self,
        artifact: NvdSilverCompletionArtifactV1,
    ) -> NvdSilverStoredCompletionV1:
        """Return configured persisted COMPLETE evidence."""
        self.calls += 1
        return self.result


class FailingPrepareService:
    """Fail if preparation should not be reached."""

    def prepare(
        self,
        request: NvdSilverTransformRequestV1,
    ) -> NvdSilverPreparedBatchV1:
        """Raise when runtime coordinate validation should fail first."""
        raise AssertionError("Prepare service was not expected.")


def test_processes_exact_manifest_through_final_complete() -> None:
    """Coordinate the full application flow and return exact evidence."""
    transform_request = _transform_request()
    prepared = _prepared()
    completion = _completion(prepared)

    loader = RecordingLoader(transform_request)
    prepare = RecordingPrepareService(prepared)
    parquet = RecordingParquetPersistence(completion)
    complete = RecordingCompletionPersistence(
        NvdSilverStoredCompletionV1(
            key=completion.manifest_key,
            version_id="silver-complete-v1",
            sha256=completion.manifest_sha256,
            size_bytes=len(completion.manifest_bytes),
        )
    )

    result = NvdSilverRuntimeProcessor(
        request_loader=loader,
        prepare_service=prepare,
        parquet_persistence_service=parquet,
        completion_persistence_service=complete,
    ).process(
        NvdSilverRuntimeRequestV1(
            source_kind=NvdSilverSourceKind.INCREMENTAL,
            manifest_key=MANIFEST_KEY,
            manifest_version_id=MANIFEST_VERSION,
        )
    )

    assert loader.calls == 1
    assert prepare.calls == 1
    assert parquet.calls == 1
    assert complete.calls == 1

    assert result.source_kind is NvdSilverSourceKind.INCREMENTAL
    assert result.source_batch_id == UPDATE_ID
    assert result.bronze_manifest_key == MANIFEST_KEY
    assert result.bronze_manifest_version_id == MANIFEST_VERSION
    assert result.silver_parquet_version_id == "silver-parquet-v1"
    assert result.silver_complete_version_id == "silver-complete-v1"
    assert result.row_count == 0


def test_rejects_loader_coordinate_drift_before_prepare() -> None:
    """Fail closed when loader output changes the requested VersionId."""
    transform_request = _transform_request()

    drifted = NvdSilverTransformRequestV1(
        source_kind=transform_request.source_kind,
        manifest_key=transform_request.manifest_key,
        manifest_version_id="different-version",
        manifest_bytes=transform_request.manifest_bytes,
        object_payloads=transform_request.object_payloads,
    )

    prepared = _prepared()
    completion = _completion(prepared)

    with pytest.raises(
        ValueError,
        match="VersionId",
    ):
        NvdSilverRuntimeProcessor(
            request_loader=RecordingLoader(drifted),
            prepare_service=FailingPrepareService(),
            parquet_persistence_service=(RecordingParquetPersistence(completion)),
            completion_persistence_service=(
                RecordingCompletionPersistence(
                    NvdSilverStoredCompletionV1(
                        key=completion.manifest_key,
                        version_id="unused",
                        sha256=completion.manifest_sha256,
                        size_bytes=len(completion.manifest_bytes),
                    )
                )
            ),
        ).process(
            NvdSilverRuntimeRequestV1(
                source_kind=NvdSilverSourceKind.INCREMENTAL,
                manifest_key=MANIFEST_KEY,
                manifest_version_id=MANIFEST_VERSION,
            )
        )


def test_rejects_stored_complete_with_wrong_hash() -> None:
    """Fail closed when final persistence evidence violates binding."""
    transform_request = _transform_request()
    prepared = _prepared()
    completion = _completion(prepared)

    with pytest.raises(
        ValueError,
        match="COMPLETE SHA-256",
    ):
        NvdSilverRuntimeProcessor(
            request_loader=RecordingLoader(transform_request),
            prepare_service=RecordingPrepareService(prepared),
            parquet_persistence_service=(RecordingParquetPersistence(completion)),
            completion_persistence_service=(
                RecordingCompletionPersistence(
                    NvdSilverStoredCompletionV1(
                        key=completion.manifest_key,
                        version_id="complete-v1",
                        sha256="f" * 64,
                        size_bytes=len(completion.manifest_bytes),
                    )
                )
            ),
        ).process(
            NvdSilverRuntimeRequestV1(
                source_kind=NvdSilverSourceKind.INCREMENTAL,
                manifest_key=MANIFEST_KEY,
                manifest_version_id=MANIFEST_VERSION,
            )
        )


def test_runtime_request_requires_exact_manifest_version() -> None:
    """Reject an invocation that does not identify an exact Bronze version."""
    with pytest.raises(
        ValueError,
        match="VersionId",
    ):
        NvdSilverRuntimeRequestV1(
            source_kind=NvdSilverSourceKind.INCREMENTAL,
            manifest_key=MANIFEST_KEY,
            manifest_version_id=" ",
        )
