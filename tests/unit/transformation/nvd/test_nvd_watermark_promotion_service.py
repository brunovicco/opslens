"""Tests for authoritative NVD Silver watermark promotion."""

from datetime import UTC, datetime

import pytest

from opslens.ingestion.nvd.application.authoritative_watermark import (
    NvdAuthoritativeWatermarkV1,
    NvdWatermarkBootstrapRecoverySeedV1,
    NvdWatermarkEvidenceObjectV1,
    NvdWatermarkSilverPromotionCommitV1,
)
from opslens.ingestion.nvd.application.authoritative_watermark_store import (
    NvdAuthoritativeWatermarkConflictError,
    NvdAuthoritativeWatermarkPreconditionFailedError,
    NvdPersistedAuthoritativeWatermarkV1,
)
from opslens.ingestion.nvd.application.watermark import (
    NvdWatermarkCandidate,
    NvdWatermarkTransitionValidator,
)
from opslens.transformation.nvd.application.watermark_promotion_service import (
    NvdAuthoritativeWatermarkPromotionConflictError,
    NvdAuthoritativeWatermarkPromotionServiceV1,
)
from opslens.transformation.nvd.completion.promotion import (
    InvalidNvdWatermarkPromotionEvidenceError,
    NvdPersistedObjectPayloadV1,
    NvdWatermarkPromotionEligibilityV1,
)

START = datetime(
    2026,
    8,
    18,
    7,
    0,
    12,
    tzinfo=UTC,
)
END = datetime(
    2026,
    8,
    18,
    7,
    20,
    12,
    tzinfo=UTC,
)

UPDATE_ID = "a" * 64
LOGICAL_SHA = "b" * 64


def _candidate() -> NvdWatermarkCandidate:
    """Build one Bronze-complete logical promotion candidate."""
    return NvdWatermarkCandidate(
        update_id=UPDATE_ID,
        window_start_at=START,
        window_end_at=END,
        bronze_manifest_key=(
            "bronze/nvd/cve/updates/"
            f"update_id={UPDATE_ID}/manifest.json"
        ),
        bronze_manifest_version_id="bronze-manifest-version-1",
        bronze_manifest_sha256="c" * 64,
        total_results=34,
        page_count=1,
    )


def _silver_manifest() -> NvdPersistedObjectPayloadV1:
    """Build exact persisted Silver COMPLETE coordinates."""
    return NvdPersistedObjectPayloadV1(
        key=(
            "silver/nvd/cve/schema_version=1/"
            "source_kind=incremental/"
            f"update_id={UPDATE_ID}/manifest.json"
        ),
        version_id="silver-manifest-version-1",
        raw_bytes=b"exact-silver-complete-bytes",
    )


def _silver_parquet() -> NvdPersistedObjectPayloadV1:
    """Build exact persisted Silver Parquet coordinates."""
    return NvdPersistedObjectPayloadV1(
        key=(
            "silver/nvd/cve/schema_version=1/"
            "source_kind=incremental/"
            f"update_id={UPDATE_ID}/part-00000.parquet"
        ),
        version_id="silver-parquet-version-1",
        raw_bytes=b"exact-silver-parquet-bytes",
    )


def _persisted(
    watermark: NvdAuthoritativeWatermarkV1,
    *,
    version_id: str,
    etag: str,
) -> NvdPersistedAuthoritativeWatermarkV1:
    """Bind one logical watermark to fake exact persistence identity."""
    return NvdPersistedAuthoritativeWatermarkV1(
        watermark=watermark,
        version_id=version_id,
        etag=etag,
        sha256="d" * 64,
        size_bytes=512,
    )


def _bootstrap_snapshot() -> NvdPersistedAuthoritativeWatermarkV1:
    """Build the current recovery-seeded authoritative state."""
    watermark = NvdAuthoritativeWatermarkV1(
        committed_through_at=START,
        commit_basis=NvdWatermarkBootstrapRecoverySeedV1(
            source_revision_at=START,
            bootstrap_manifest=NvdWatermarkEvidenceObjectV1(
                key="bronze/nvd/cve/bootstrap/manifest.json",
                version_id="bootstrap-manifest-version-1",
                sha256="e" * 64,
            ),
        ),
    )

    return _persisted(
        watermark,
        version_id="watermark-version-1",
        etag='"watermark-etag-1"',
    )


def _expected_promoted_watermark() -> NvdAuthoritativeWatermarkV1:
    """Build the exact expected Silver-authorized commit."""
    candidate = _candidate()
    silver_manifest = _silver_manifest()
    silver_parquet = _silver_parquet()

    return NvdAuthoritativeWatermarkV1(
        committed_through_at=END,
        commit_basis=NvdWatermarkSilverPromotionCommitV1(
            previous_committed_through_at=START,
            update_id=UPDATE_ID,
            bronze_manifest=NvdWatermarkEvidenceObjectV1(
                key=candidate.bronze_manifest_key,
                version_id=candidate.bronze_manifest_version_id,
                sha256=candidate.bronze_manifest_sha256,
            ),
            silver_manifest=NvdWatermarkEvidenceObjectV1(
                key=silver_manifest.key,
                version_id=silver_manifest.version_id,
                sha256=silver_manifest.sha256,
            ),
            silver_parquet=NvdWatermarkEvidenceObjectV1(
                key=silver_parquet.key,
                version_id=silver_parquet.version_id,
                sha256=silver_parquet.sha256,
            ),
            logical_record_set_sha256=LOGICAL_SHA,
        ),
    )


class _Verifier:
    """Small verifier double preserving the real continuity contract."""

    def __init__(self) -> None:
        self.calls = 0

    def verify(
        self,
        *,
        committed_through_at: datetime,
        candidate: NvdWatermarkCandidate,
        silver_manifest: NvdPersistedObjectPayloadV1,
        silver_parquet: NvdPersistedObjectPayloadV1,
    ) -> NvdWatermarkPromotionEligibilityV1:
        """Return eligibility after the same continuity validation."""
        self.calls += 1

        try:
            NvdWatermarkTransitionValidator().validate(
                committed_through_at=committed_through_at,
                candidate=candidate,
            )
        except ValueError as exc:
            raise InvalidNvdWatermarkPromotionEvidenceError(
                str(exc)
            ) from exc

        return NvdWatermarkPromotionEligibilityV1(
            update_id=candidate.update_id,
            validated_committed_through_at=committed_through_at,
            next_committed_through_at=candidate.window_end_at,
            bronze_manifest_key=candidate.bronze_manifest_key,
            bronze_manifest_version_id=(
                candidate.bronze_manifest_version_id
            ),
            bronze_manifest_sha256=(
                candidate.bronze_manifest_sha256
            ),
            silver_manifest_key=silver_manifest.key,
            silver_manifest_version_id=silver_manifest.version_id,
            silver_manifest_sha256=silver_manifest.sha256,
            silver_parquet_key=silver_parquet.key,
            silver_parquet_version_id=silver_parquet.version_id,
            silver_parquet_sha256=silver_parquet.sha256,
            logical_record_set_sha256=LOGICAL_SHA,
            total_results=candidate.total_results,
            row_count=candidate.total_results,
            page_count=candidate.page_count,
            warning_count=0,
        )


class _NeverVerifier(_Verifier):
    """Fail if verification occurs on an exact committed replay."""

    def verify(
        self,
        *,
        committed_through_at: datetime,
        candidate: NvdWatermarkCandidate,
        silver_manifest: NvdPersistedObjectPayloadV1,
        silver_parquet: NvdPersistedObjectPayloadV1,
    ) -> NvdWatermarkPromotionEligibilityV1:
        """Reject an unexpected verifier call."""
        raise AssertionError(
            "Exact committed replay must not re-enter eligibility."
        )


class _Store:
    """In-memory authoritative store with observable CAS calls."""

    def __init__(
        self,
        current: NvdPersistedAuthoritativeWatermarkV1,
    ) -> None:
        self.current = current
        self.cas_calls = 0
        self.cas_expected_etag: str | None = None

    def load(
        self,
    ) -> NvdPersistedAuthoritativeWatermarkV1:
        """Return current state."""
        return self.current

    def initialize(
        self,
        *,
        watermark: NvdAuthoritativeWatermarkV1,
    ) -> NvdPersistedAuthoritativeWatermarkV1:
        """Reject initialization in promotion tests."""
        raise AssertionError(
            "Promotion service must never initialize watermark."
        )

    def compare_and_swap(
        self,
        *,
        watermark: NvdAuthoritativeWatermarkV1,
        expected_etag: str,
    ) -> NvdPersistedAuthoritativeWatermarkV1:
        """Commit one exact next state."""
        self.cas_calls += 1
        self.cas_expected_etag = expected_etag

        self.current = _persisted(
            watermark,
            version_id="watermark-version-2",
            etag='"watermark-etag-2"',
        )

        return self.current


class _WinningRaceStore(_Store):
    """Simulate another invocation committing the same target first."""

    def compare_and_swap(
        self,
        *,
        watermark: NvdAuthoritativeWatermarkV1,
        expected_etag: str,
    ) -> NvdPersistedAuthoritativeWatermarkV1:
        """Persist the same winner and surface the losing CAS."""
        self.cas_calls += 1
        self.cas_expected_etag = expected_etag
        self.current = _persisted(
            watermark,
            version_id="watermark-version-race",
            etag='"watermark-etag-race"',
        )

        raise NvdAuthoritativeWatermarkPreconditionFailedError(
            "simulated same-candidate race"
        )


class _IncompatibleRaceStore(_Store):
    """Simulate a different authoritative transition winning CAS."""

    def compare_and_swap(
        self,
        *,
        watermark: NvdAuthoritativeWatermarkV1,
        expected_etag: str,
    ) -> NvdPersistedAuthoritativeWatermarkV1:
        """Persist a different winner and surface the conflict."""
        self.cas_calls += 1
        self.cas_expected_etag = expected_etag

        incompatible = NvdAuthoritativeWatermarkV1(
            committed_through_at=END,
            commit_basis=NvdWatermarkSilverPromotionCommitV1(
                previous_committed_through_at=START,
                update_id="f" * 64,
                bronze_manifest=NvdWatermarkEvidenceObjectV1(
                    key="different-bronze",
                    version_id="different-bronze-version",
                    sha256="1" * 64,
                ),
                silver_manifest=NvdWatermarkEvidenceObjectV1(
                    key="different-silver",
                    version_id="different-silver-version",
                    sha256="2" * 64,
                ),
                silver_parquet=NvdWatermarkEvidenceObjectV1(
                    key="different-parquet",
                    version_id="different-parquet-version",
                    sha256="3" * 64,
                ),
                logical_record_set_sha256="4" * 64,
            ),
        )

        self.current = _persisted(
            incompatible,
            version_id="watermark-version-other",
            etag='"watermark-etag-other"',
        )

        raise NvdAuthoritativeWatermarkConflictError(
            "simulated incompatible race"
        )


def test_eligible_candidate_commits_with_snapshot_etag() -> None:
    """Commit verified Silver evidence using the exact prior ETag."""
    store = _Store(_bootstrap_snapshot())
    verifier = _Verifier()

    result = NvdAuthoritativeWatermarkPromotionServiceV1(
        watermark_store=store,
        verifier=verifier,
    ).promote(
        candidate=_candidate(),
        silver_manifest=_silver_manifest(),
        silver_parquet=_silver_parquet(),
    )

    assert result.status == "committed"
    assert result.update_id == UPDATE_ID
    assert verifier.calls == 1
    assert store.cas_calls == 1
    assert store.cas_expected_etag == '"watermark-etag-1"'
    assert result.persisted.watermark == (
        _expected_promoted_watermark()
    )


def test_exact_committed_candidate_is_idempotent() -> None:
    """Treat the same exact already-committed evidence as success."""
    current = _persisted(
        _expected_promoted_watermark(),
        version_id="watermark-version-2",
        etag='"watermark-etag-2"',
    )
    store = _Store(current)

    result = NvdAuthoritativeWatermarkPromotionServiceV1(
        watermark_store=store,
        verifier=_NeverVerifier(),
    ).promote(
        candidate=_candidate(),
        silver_manifest=_silver_manifest(),
        silver_parquet=_silver_parquet(),
    )

    assert result.status == "already_committed"
    assert result.persisted == current
    assert store.cas_calls == 0


def test_stale_candidate_fails_closed() -> None:
    """Reject a candidate whose start is behind current authority."""
    promoted = _persisted(
        _expected_promoted_watermark(),
        version_id="watermark-version-2",
        etag='"watermark-etag-2"',
    )

    changed_parquet = NvdPersistedObjectPayloadV1(
        key=_silver_parquet().key,
        version_id="different-parquet-version",
        raw_bytes=b"different-parquet",
    )

    with pytest.raises(
        InvalidNvdWatermarkPromotionEvidenceError,
        match="current committed boundary",
    ):
        NvdAuthoritativeWatermarkPromotionServiceV1(
            watermark_store=_Store(promoted),
            verifier=_Verifier(),
        ).promote(
            candidate=_candidate(),
            silver_manifest=_silver_manifest(),
            silver_parquet=changed_parquet,
        )


def test_gap_candidate_fails_closed() -> None:
    """Reject a candidate that begins after the committed boundary."""
    earlier = datetime(
        2026,
        8,
        18,
        6,
        50,
        12,
        tzinfo=UTC,
    )

    watermark = NvdAuthoritativeWatermarkV1(
        committed_through_at=earlier,
        commit_basis=NvdWatermarkBootstrapRecoverySeedV1(
            source_revision_at=earlier,
            bootstrap_manifest=NvdWatermarkEvidenceObjectV1(
                key="bootstrap-earlier",
                version_id="bootstrap-earlier-version",
                sha256="5" * 64,
            ),
        ),
    )

    with pytest.raises(
        InvalidNvdWatermarkPromotionEvidenceError,
        match="current committed boundary",
    ):
        NvdAuthoritativeWatermarkPromotionServiceV1(
            watermark_store=_Store(
                _persisted(
                    watermark,
                    version_id="watermark-version-earlier",
                    etag='"watermark-etag-earlier"',
                )
            ),
            verifier=_Verifier(),
        ).promote(
            candidate=_candidate(),
            silver_manifest=_silver_manifest(),
            silver_parquet=_silver_parquet(),
        )


def test_same_candidate_cas_race_is_idempotent() -> None:
    """Accept a lost CAS only when the exact target won the race."""
    store = _WinningRaceStore(_bootstrap_snapshot())

    result = NvdAuthoritativeWatermarkPromotionServiceV1(
        watermark_store=store,
        verifier=_Verifier(),
    ).promote(
        candidate=_candidate(),
        silver_manifest=_silver_manifest(),
        silver_parquet=_silver_parquet(),
    )

    assert result.status == "already_committed"
    assert result.persisted.watermark == (
        _expected_promoted_watermark()
    )
    assert store.cas_calls == 1


def test_incompatible_cas_winner_fails_closed() -> None:
    """Reject a lost CAS when another authoritative state won."""
    store = _IncompatibleRaceStore(_bootstrap_snapshot())

    with pytest.raises(
        NvdAuthoritativeWatermarkPromotionConflictError,
        match="incompatible",
    ):
        NvdAuthoritativeWatermarkPromotionServiceV1(
            watermark_store=store,
            verifier=_Verifier(),
        ).promote(
            candidate=_candidate(),
            silver_manifest=_silver_manifest(),
            silver_parquet=_silver_parquet(),
        )

    assert store.cas_calls == 1
