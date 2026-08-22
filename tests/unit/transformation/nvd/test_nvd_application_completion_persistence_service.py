"""Tests for final NVD Silver COMPLETE persistence orchestration."""

from datetime import UTC, datetime
from hashlib import sha256

import pytest

from opslens.transformation.nvd.application.completion_persistence_service import (
    NvdSilverCompletionPersistenceServiceV1,
)
from opslens.transformation.nvd.application.errors import (
    NvdSilverCompletionAlreadyExistsError,
)
from opslens.transformation.nvd.application.persistence_models import (
    NvdSilverStoredCompletionV1,
)
from opslens.transformation.nvd.completion.manifest import (
    NvdSilverCompletionArtifactV1,
    NvdSilverCompletionManifestV1,
    NvdSilverStoredObjectV1,
)
from opslens.transformation.nvd.provenance.models import (
    NvdBronzeObjectReferenceV1,
    NvdBronzeObjectRole,
    VerifiedNvdBronzeEvidenceV1,
)
from opslens.transformation.nvd.serialization.models import (
    NvdSilverSourceKind,
)


class CreatedCompletionRepository:
    """Return evidence for one newly persisted COMPLETE object."""

    def __init__(self, *, version_id: str) -> None:
        """Initialize the persisted COMPLETE VersionId."""
        self._version_id = version_id
        self.calls = 0

    def put_if_absent(
        self,
        *,
        artifact: NvdSilverCompletionArtifactV1,
    ) -> NvdSilverStoredCompletionV1:
        """Return exact persisted evidence for the supplied artifact."""
        self.calls += 1

        return NvdSilverStoredCompletionV1(
            key=artifact.manifest_key,
            version_id=self._version_id,
            sha256=artifact.manifest_sha256,
            size_bytes=len(artifact.manifest_bytes),
        )


class ExistingCompletionRepository:
    """Report that the deterministic COMPLETE key already exists."""

    def __init__(self) -> None:
        """Initialize call accounting."""
        self.calls = 0

    def put_if_absent(
        self,
        *,
        artifact: NvdSilverCompletionArtifactV1,
    ) -> NvdSilverStoredCompletionV1:
        """Require exact replay verification."""
        self.calls += 1

        raise NvdSilverCompletionAlreadyExistsError("Existing deterministic COMPLETE.")


class RecordingCompletionReplayVerifier:
    """Return configured exact replay evidence."""

    def __init__(self, *, version_id: str) -> None:
        """Initialize replay VersionId."""
        self._version_id = version_id
        self.calls = 0

    def verify_current(
        self,
        *,
        artifact: NvdSilverCompletionArtifactV1,
    ) -> NvdSilverStoredCompletionV1:
        """Return exact evidence matching the expected COMPLETE artifact."""
        self.calls += 1

        return NvdSilverStoredCompletionV1(
            key=artifact.manifest_key,
            version_id=self._version_id,
            sha256=artifact.manifest_sha256,
            size_bytes=len(artifact.manifest_bytes),
        )


class FailingCompletionReplayVerifier:
    """Fail when replay must not be invoked."""

    def verify_current(
        self,
        *,
        artifact: NvdSilverCompletionArtifactV1,
    ) -> NvdSilverStoredCompletionV1:
        """Raise if a newly created COMPLETE incorrectly invokes replay."""
        raise AssertionError("COMPLETE replay verification was not expected.")


class WrongHashCompletionRepository:
    """Return structurally valid but incorrect COMPLETE evidence."""

    def put_if_absent(
        self,
        *,
        artifact: NvdSilverCompletionArtifactV1,
    ) -> NvdSilverStoredCompletionV1:
        """Return persistence evidence with an incorrect SHA-256."""
        return NvdSilverStoredCompletionV1(
            key=artifact.manifest_key,
            version_id="wrong-evidence-version",
            sha256="f" * 64,
            size_bytes=len(artifact.manifest_bytes),
        )


def _artifact() -> NvdSilverCompletionArtifactV1:
    """Build one valid deterministic COMPLETE artifact."""
    update_id = "a" * 64
    page_bytes = b"page"

    evidence = VerifiedNvdBronzeEvidenceV1(
        source_kind=NvdSilverSourceKind.INCREMENTAL,
        source_batch_id=update_id,
        manifest_key=(f"bronze/nvd/cve/updates/update_id={update_id}/manifest.json"),
        manifest_version_id="bronze-manifest-v1",
        manifest_sha256="b" * 64,
        manifest_size_bytes=100,
        objects=(
            NvdBronzeObjectReferenceV1(
                role=NvdBronzeObjectRole.PAGE,
                key=(
                    f"bronze/nvd/cve/updates/update_id={update_id}/page_start=000000/response.json"
                ),
                version_id="bronze-page-v1",
                size_bytes=len(page_bytes),
                sha256=sha256(page_bytes).hexdigest(),
                page_start=0,
                source_timestamp="2026-08-22T12:00:00.000",
            ),
        ),
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

    manifest = NvdSilverCompletionManifestV1(
        bronze_evidence=evidence,
        silver_object=NvdSilverStoredObjectV1(
            key=(
                "silver/nvd/cve/"
                "schema_version=1/"
                "source_kind=incremental/"
                f"update_id={update_id}/"
                "part-00000.parquet"
            ),
            version_id="silver-parquet-v1",
            sha256="c" * 64,
            size_bytes=123,
            row_count=0,
        ),
        logical_record_set_sha256="d" * 64,
        warnings=(),
    )

    manifest_bytes = b'{"completion_status":"complete"}\n'

    return NvdSilverCompletionArtifactV1(
        manifest=manifest,
        manifest_key=(
            "silver/nvd/cve/"
            "schema_version=1/"
            "source_kind=incremental/"
            f"update_id={update_id}/"
            "manifest.json"
        ),
        manifest_bytes=manifest_bytes,
        manifest_sha256=sha256(manifest_bytes).hexdigest(),
    )


def test_created_complete_returns_exact_persisted_evidence() -> None:
    """Use newly created COMPLETE evidence without invoking replay."""
    artifact = _artifact()
    repository = CreatedCompletionRepository(
        version_id="complete-created-v1",
    )

    stored = NvdSilverCompletionPersistenceServiceV1(
        repository=repository,
        replay_verifier=FailingCompletionReplayVerifier(),
    ).persist(artifact)

    assert repository.calls == 1
    assert stored.key == artifact.manifest_key
    assert stored.version_id == "complete-created-v1"
    assert stored.sha256 == artifact.manifest_sha256
    assert stored.size_bytes == len(artifact.manifest_bytes)


def test_existing_complete_requires_exact_replay() -> None:
    """Accept an existing COMPLETE only after exact replay verification."""
    artifact = _artifact()
    repository = ExistingCompletionRepository()
    replay = RecordingCompletionReplayVerifier(
        version_id="complete-replayed-v1",
    )

    stored = NvdSilverCompletionPersistenceServiceV1(
        repository=repository,
        replay_verifier=replay,
    ).persist(artifact)

    assert repository.calls == 1
    assert replay.calls == 1
    assert stored.version_id == "complete-replayed-v1"
    assert stored.sha256 == artifact.manifest_sha256


def test_rejects_repository_evidence_with_wrong_sha256() -> None:
    """Fail closed when persisted COMPLETE evidence disagrees with artifact."""
    artifact = _artifact()

    with pytest.raises(
        ValueError,
        match="SHA-256",
    ):
        NvdSilverCompletionPersistenceServiceV1(
            repository=WrongHashCompletionRepository(),
            replay_verifier=FailingCompletionReplayVerifier(),
        ).persist(artifact)


def test_created_and_replayed_paths_return_equivalent_evidence() -> None:
    """Keep idempotent completion semantics independent of creation path."""
    artifact = _artifact()

    created = NvdSilverCompletionPersistenceServiceV1(
        repository=CreatedCompletionRepository(
            version_id="complete-stable-v1",
        ),
        replay_verifier=FailingCompletionReplayVerifier(),
    ).persist(artifact)

    replayed = NvdSilverCompletionPersistenceServiceV1(
        repository=ExistingCompletionRepository(),
        replay_verifier=RecordingCompletionReplayVerifier(
            version_id="complete-stable-v1",
        ),
    ).persist(artifact)

    assert created == replayed
