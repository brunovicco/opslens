"""Unit tests for authoritative NVD recovery-seed orchestration."""

from datetime import UTC, datetime, timedelta, timezone

import pytest

from opslens.ingestion.nvd.application.authoritative_watermark import (
    NvdAuthoritativeWatermarkV1,
    NvdWatermarkBootstrapRecoverySeedV1,
    NvdWatermarkEvidenceObjectV1,
)
from opslens.ingestion.nvd.application.authoritative_watermark_seed import (
    NvdAuthoritativeWatermarkSeedConflictError,
    NvdAuthoritativeWatermarkSeedStatus,
    NvdBootstrapRecoverySeedEvidenceV1,
    SeedNvdAuthoritativeWatermarkV1,
)
from opslens.ingestion.nvd.application.authoritative_watermark_store import (
    NvdAuthoritativeWatermarkAlreadyExistsError,
    NvdPersistedAuthoritativeWatermarkV1,
)


class FakeWatermarkStore:
    """Provide deterministic seed-storage behavior."""

    def __init__(
        self,
        *,
        initialize_error: Exception | None = None,
        current: NvdPersistedAuthoritativeWatermarkV1 | None = None,
    ) -> None:
        """Initialize configured behavior and captured calls."""
        self.initialize_error = initialize_error
        self.current = current
        self.initialize_calls: list[NvdAuthoritativeWatermarkV1] = []
        self.load_calls = 0

    def initialize(
        self,
        *,
        watermark: NvdAuthoritativeWatermarkV1,
    ) -> NvdPersistedAuthoritativeWatermarkV1:
        """Capture initialization and return exact persisted state."""
        self.initialize_calls.append(watermark)

        if self.initialize_error is not None:
            raise self.initialize_error

        return _persisted(watermark)

    def load(
        self,
    ) -> NvdPersistedAuthoritativeWatermarkV1:
        """Return configured current state."""
        self.load_calls += 1

        if self.current is None:
            raise AssertionError(
                "Test did not configure current watermark."
            )

        return self.current

    def compare_and_swap(
        self,
        *,
        watermark: NvdAuthoritativeWatermarkV1,
        expected_etag: str,
    ) -> NvdPersistedAuthoritativeWatermarkV1:
        """Reject unexpected promotion calls in seed-service tests."""
        raise AssertionError(
            "Seed service must never call compare_and_swap."
        )


def _manifest() -> NvdWatermarkEvidenceObjectV1:
    """Build the exact Bootstrap COMPLETE evidence shape."""
    return NvdWatermarkEvidenceObjectV1(
        key=(
            "bronze/nvd/cve/bootstrap/"
            "feed_year=2026/"
            "feed_revision="
            "20260818T070012Z-"
            "10fb32c20bd6187fe43fa047d74772256"
            "f5b37c18029b17c5379a1f4e18f5d4f/"
            "manifest.json"
        ),
        version_id="O9t9lPdkxd0GnvqZBBGU87mqRa5MrIRl",
        sha256=(
            "c05376f10867dbda5b0fd49fbf9c9d"
            "abbb2c43f92d01877fdbfdaccbf188efc8"
        ),
    )


def _evidence() -> NvdBootstrapRecoverySeedEvidenceV1:
    """Build the audited Phase 2.3F recovery evidence."""
    return NvdBootstrapRecoverySeedEvidenceV1(
        source_revision_at=datetime(
            2026,
            8,
            18,
            3,
            0,
            12,
            tzinfo=timezone(timedelta(hours=-4)),
        ),
        bootstrap_manifest=_manifest(),
    )


def _watermark() -> NvdAuthoritativeWatermarkV1:
    """Build the desired initial authoritative state."""
    boundary = datetime(
        2026,
        8,
        18,
        7,
        0,
        12,
        tzinfo=UTC,
    )

    return NvdAuthoritativeWatermarkV1(
        committed_through_at=boundary,
        commit_basis=NvdWatermarkBootstrapRecoverySeedV1(
            source_revision_at=boundary,
            bootstrap_manifest=_manifest(),
        ),
    )


def _persisted(
    watermark: NvdAuthoritativeWatermarkV1,
) -> NvdPersistedAuthoritativeWatermarkV1:
    """Bind test logical state to valid persistence coordinates."""
    return NvdPersistedAuthoritativeWatermarkV1(
        watermark=watermark,
        version_id="watermark-version-1",
        etag='"watermark-etag-1"',
        sha256="a" * 64,
        size_bytes=512,
    )


def test_seed_creates_exact_recovery_boundary() -> None:
    """Initialize T0 from the audited Bootstrap source revision."""
    store = FakeWatermarkStore()

    result = SeedNvdAuthoritativeWatermarkV1(
        store=store,
    ).execute(
        evidence=_evidence(),
    )

    assert result.status == (
        NvdAuthoritativeWatermarkSeedStatus.CREATED
    )
    assert len(store.initialize_calls) == 1
    assert store.load_calls == 0

    created = store.initialize_calls[0]

    assert created.committed_through_at == datetime(
        2026,
        8,
        18,
        7,
        0,
        12,
        tzinfo=UTC,
    )
    assert created == _watermark()


def test_seed_normalizes_nvd_meta_offset_to_utc() -> None:
    """Preserve the exact instant represented by the original NVD META."""
    evidence = _evidence()

    assert evidence.source_revision_at == datetime(
        2026,
        8,
        18,
        7,
        0,
        12,
        tzinfo=UTC,
    )


def test_duplicate_identical_seed_is_idempotent() -> None:
    """Resolve S3 412 as success only when current state is identical."""
    current = _persisted(_watermark())

    store = FakeWatermarkStore(
        initialize_error=(
            NvdAuthoritativeWatermarkAlreadyExistsError(
                "already exists"
            )
        ),
        current=current,
    )

    result = SeedNvdAuthoritativeWatermarkV1(
        store=store,
    ).execute(
        evidence=_evidence(),
    )

    assert result.status == (
        NvdAuthoritativeWatermarkSeedStatus.ALREADY_INITIALIZED
    )
    assert result.persisted is current
    assert store.load_calls == 1


def test_duplicate_different_seed_fails_closed() -> None:
    """Never replace authoritative state after a seed precondition failure."""
    different_boundary = datetime(
        2026,
        8,
        18,
        8,
        0,
        12,
        tzinfo=UTC,
    )

    different = NvdAuthoritativeWatermarkV1(
        committed_through_at=different_boundary,
        commit_basis=NvdWatermarkBootstrapRecoverySeedV1(
            source_revision_at=different_boundary,
            bootstrap_manifest=_manifest(),
        ),
    )

    store = FakeWatermarkStore(
        initialize_error=(
            NvdAuthoritativeWatermarkAlreadyExistsError(
                "already exists"
            )
        ),
        current=_persisted(different),
    )

    with pytest.raises(
        NvdAuthoritativeWatermarkSeedConflictError,
        match="does not match",
    ):
        SeedNvdAuthoritativeWatermarkV1(
            store=store,
        ).execute(
            evidence=_evidence(),
        )

    assert store.load_calls == 1


def test_seed_rejects_non_bootstrap_manifest_evidence() -> None:
    """Prevent arbitrary objects from establishing initial authority."""
    with pytest.raises(
        ValueError,
        match="Bootstrap Bronze manifest",
    ):
        NvdBootstrapRecoverySeedEvidenceV1(
            source_revision_at=datetime(
                2026,
                8,
                18,
                7,
                0,
                12,
                tzinfo=UTC,
            ),
            bootstrap_manifest=NvdWatermarkEvidenceObjectV1(
                key="silver/nvd/cve/manifest.json",
                version_id="wrong-version",
                sha256="b" * 64,
            ),
        )
