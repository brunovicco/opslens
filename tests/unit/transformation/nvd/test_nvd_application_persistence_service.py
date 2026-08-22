"""Tests for NVD Silver persistence and COMPLETE preparation orchestration."""

from datetime import UTC, datetime
from hashlib import sha256

import pytest

from opslens.transformation.nvd.application.errors import (
    NvdSilverParquetAlreadyExistsError,
)
from opslens.transformation.nvd.application.models import (
    NvdSilverPreparedBatchV1,
)
from opslens.transformation.nvd.application.persistence_service import (
    NvdSilverPersistenceServiceV1,
)
from opslens.transformation.nvd.application.ports import (
    NvdSilverParquetReplayVerifier,
    NvdSilverParquetRepository,
)
from opslens.transformation.nvd.completion.key_factory import (
    NvdSilverKeyFactoryV1,
)
from opslens.transformation.nvd.completion.manifest import (
    NvdSilverCompletionManifestFactoryV1,
    NvdSilverCompletionManifestSerializerV1,
    NvdSilverStoredObjectV1,
)
from opslens.transformation.nvd.provenance.models import (
    NvdBronzeObjectReferenceV1,
    NvdBronzeObjectRole,
    VerifiedNvdBronzeEvidenceV1,
)
from opslens.transformation.nvd.serialization.models import (
    NvdSilverParquetArtifactV1,
    NvdSilverSourceKind,
)
from opslens.transformation.nvd.serialization.parquet import (
    NvdSilverParquetSerializerV1,
)


class CreatedRepository:
    """Return exact evidence for one newly persisted deterministic artifact."""

    def __init__(
        self,
        *,
        version_id: str,
    ) -> None:
        """Initialize the created-object VersionId."""
        self._version_id = version_id
        self.calls = 0

    def put_if_absent(
        self,
        *,
        key: str,
        artifact: NvdSilverParquetArtifactV1,
    ) -> NvdSilverStoredObjectV1:
        """Return exact persisted evidence for the supplied artifact."""
        self.calls += 1

        return NvdSilverStoredObjectV1(
            key=key,
            version_id=self._version_id,
            sha256=artifact.parquet_sha256,
            size_bytes=artifact.size_bytes,
            row_count=artifact.row_count,
        )


class ExistingRepository:
    """Report that the deterministic Parquet key already exists."""

    def __init__(self) -> None:
        """Initialize call accounting."""
        self.calls = 0

    def put_if_absent(
        self,
        *,
        key: str,
        artifact: NvdSilverParquetArtifactV1,
    ) -> NvdSilverStoredObjectV1:
        """Require exact replay verification for the existing key."""
        self.calls += 1

        raise NvdSilverParquetAlreadyExistsError("Existing deterministic Silver object.")


class RecordingReplayVerifier:
    """Return configured exact persisted replay evidence."""

    def __init__(
        self,
        *,
        version_id: str,
    ) -> None:
        """Initialize replay evidence."""
        self._version_id = version_id
        self.calls = 0

    def verify_current(
        self,
        *,
        key: str,
        artifact: NvdSilverParquetArtifactV1,
    ) -> NvdSilverStoredObjectV1:
        """Return exact evidence matching the deterministic artifact."""
        self.calls += 1

        return NvdSilverStoredObjectV1(
            key=key,
            version_id=self._version_id,
            sha256=artifact.parquet_sha256,
            size_bytes=artifact.size_bytes,
            row_count=artifact.row_count,
        )


class FailingReplayVerifier:
    """Fail when replay verification should never be invoked."""

    def verify_current(
        self,
        *,
        key: str,
        artifact: NvdSilverParquetArtifactV1,
    ) -> NvdSilverStoredObjectV1:
        """Raise if the created-object path incorrectly invokes replay."""
        raise AssertionError("Replay verification was not expected.")


class WrongEvidenceRepository:
    """Return structurally valid but incorrect persisted evidence."""

    def put_if_absent(
        self,
        *,
        key: str,
        artifact: NvdSilverParquetArtifactV1,
    ) -> NvdSilverStoredObjectV1:
        """Return a valid object whose SHA-256 is intentionally incorrect."""
        return NvdSilverStoredObjectV1(
            key=key,
            version_id="silver-version-wrong",
            sha256="f" * 64,
            size_bytes=artifact.size_bytes,
            row_count=artifact.row_count,
        )


def _prepared() -> NvdSilverPreparedBatchV1:
    """Build one valid zero-result incremental prepared batch."""
    update_id = "a" * 64
    page_bytes = b'{"vulnerabilities":[]}'

    page_reference = NvdBronzeObjectReferenceV1(
        role=NvdBronzeObjectRole.PAGE,
        key=(f"bronze/nvd/cve/updates/update_id={update_id}/page_start=000000/response.json"),
        version_id="bronze-page-version-1",
        size_bytes=len(page_bytes),
        sha256=sha256(page_bytes).hexdigest(),
        page_start=0,
        source_timestamp="2026-08-22T12:00:00.000",
    )

    evidence = VerifiedNvdBronzeEvidenceV1(
        source_kind=NvdSilverSourceKind.INCREMENTAL,
        source_batch_id=update_id,
        manifest_key=(f"bronze/nvd/cve/updates/update_id={update_id}/manifest.json"),
        manifest_version_id="bronze-manifest-version-1",
        manifest_sha256="b" * 64,
        manifest_size_bytes=123,
        objects=(page_reference,),
        bootstrap_feed_year=None,
        bootstrap_feed_revision=None,
        bootstrap_source_observed_at=None,
        incremental_update_id=update_id,
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

    parquet_artifact = NvdSilverParquetSerializerV1().serialize_empty(
        source_kind=NvdSilverSourceKind.INCREMENTAL,
        source_batch_id=update_id,
    )

    return NvdSilverPreparedBatchV1(
        evidence=evidence,
        records=(),
        parquet_artifact=parquet_artifact,
        keys=NvdSilverKeyFactoryV1().build(evidence),
    )


def _service(
    *,
    repository: NvdSilverParquetRepository,
    replay_verifier: NvdSilverParquetReplayVerifier,
) -> NvdSilverPersistenceServiceV1:
    """Build the persistence service with real completion components."""
    return NvdSilverPersistenceServiceV1(
        parquet_repository=repository,
        replay_verifier=replay_verifier,
        completion_factory=NvdSilverCompletionManifestFactoryV1(),
        completion_serializer=NvdSilverCompletionManifestSerializerV1(),
    )


def test_created_parquet_prepares_complete_manifest() -> None:
    """Bind a newly created Parquet VersionId into deterministic COMPLETE."""
    prepared = _prepared()
    repository = CreatedRepository(
        version_id="silver-version-created",
    )

    completion = _service(
        repository=repository,
        replay_verifier=FailingReplayVerifier(),
    ).prepare_completion(prepared)

    assert repository.calls == 1
    assert completion.manifest_key == prepared.keys.manifest_key
    assert completion.manifest.silver_object.version_id == ("silver-version-created")
    assert completion.manifest.silver_object.sha256 == (prepared.parquet_artifact.parquet_sha256)
    assert completion.manifest.silver_object.key == (prepared.keys.parquet_key)

    assert completion.manifest_bytes
    assert completion.manifest_sha256 == sha256(completion.manifest_bytes).hexdigest()


def test_existing_parquet_requires_exact_replay_before_completion() -> None:
    """Accept a 412 path only after the replay verifier proves exact equality."""
    prepared = _prepared()
    repository = ExistingRepository()
    replay = RecordingReplayVerifier(
        version_id="silver-version-replayed",
    )

    completion = _service(
        repository=repository,
        replay_verifier=replay,
    ).prepare_completion(prepared)

    assert repository.calls == 1
    assert replay.calls == 1
    assert completion.manifest.silver_object.version_id == ("silver-version-replayed")


def test_rejects_persistence_evidence_with_wrong_sha256() -> None:
    """Fail closed when a repository violates the persisted-object contract."""
    prepared = _prepared()

    with pytest.raises(
        ValueError,
        match="SHA-256",
    ):
        _service(
            repository=WrongEvidenceRepository(),
            replay_verifier=FailingReplayVerifier(),
        ).prepare_completion(prepared)


def test_same_persisted_version_produces_same_complete_bytes() -> None:
    """Keep COMPLETE serialization deterministic for identical evidence."""
    prepared = _prepared()

    first = _service(
        repository=CreatedRepository(
            version_id="silver-version-stable",
        ),
        replay_verifier=FailingReplayVerifier(),
    ).prepare_completion(prepared)

    second = _service(
        repository=CreatedRepository(
            version_id="silver-version-stable",
        ),
        replay_verifier=FailingReplayVerifier(),
    ).prepare_completion(prepared)

    assert first.manifest_bytes == second.manifest_bytes
    assert first.manifest_sha256 == second.manifest_sha256
