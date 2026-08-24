"""Commit verified NVD Silver completion to the authoritative watermark."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol

from opslens.ingestion.nvd.application.authoritative_watermark import (
    NvdAuthoritativeWatermarkV1,
    NvdWatermarkEvidenceObjectV1,
    NvdWatermarkSilverPromotionCommitV1,
)
from opslens.ingestion.nvd.application.authoritative_watermark_store import (
    NvdAuthoritativeWatermarkConflictError,
    NvdAuthoritativeWatermarkPreconditionFailedError,
    NvdAuthoritativeWatermarkStoreV1,
    NvdPersistedAuthoritativeWatermarkV1,
)
from opslens.ingestion.nvd.application.watermark import (
    NvdWatermarkCandidate,
    NvdWatermarkTransitionValidator,
)
from opslens.transformation.nvd.completion.promotion import (
    NvdPersistedObjectPayloadV1,
    NvdWatermarkPromotionEligibilityV1,
)

NvdAuthoritativeWatermarkPromotionStatus = Literal[
    "committed",
    "already_committed",
]


class NvdWatermarkPromotionEvidenceVerifier(Protocol):
    """Verify exact Silver evidence for authoritative promotion."""

    def verify(
        self,
        *,
        committed_through_at: datetime,
        candidate: NvdWatermarkCandidate,
        silver_manifest: NvdPersistedObjectPayloadV1,
        silver_parquet: NvdPersistedObjectPayloadV1,
    ) -> NvdWatermarkPromotionEligibilityV1:
        """Return promotion eligibility for exact persisted evidence."""
        ...


class NvdAuthoritativeWatermarkPromotionConflictError(RuntimeError):
    """Raised when another incompatible watermark transition wins."""


@dataclass(frozen=True, slots=True)
class NvdAuthoritativeWatermarkPromotionResultV1:
    """Return exact committed watermark evidence after promotion."""

    status: NvdAuthoritativeWatermarkPromotionStatus
    update_id: str
    persisted: NvdPersistedAuthoritativeWatermarkV1


class NvdAuthoritativeWatermarkPromotionServiceV1:
    """Own the final deterministic transition to watermark_committed."""

    def __init__(
        self,
        *,
        watermark_store: NvdAuthoritativeWatermarkStoreV1,
        verifier: NvdWatermarkPromotionEvidenceVerifier,
        transition_validator: NvdWatermarkTransitionValidator | None = None,
    ) -> None:
        """Initialize explicit promotion dependencies."""
        self._watermark_store = watermark_store
        self._verifier = verifier
        self._transition_validator = (
            transition_validator
            if transition_validator is not None
            else NvdWatermarkTransitionValidator()
        )

    def promote(
        self,
        *,
        candidate: NvdWatermarkCandidate,
        silver_manifest: NvdPersistedObjectPayloadV1,
        silver_parquet: NvdPersistedObjectPayloadV1,
    ) -> NvdAuthoritativeWatermarkPromotionResultV1:
        """Promote one exact Silver-complete candidate using watermark CAS."""
        snapshot = self._watermark_store.load()

        if self._is_exact_existing_commit(
            persisted=snapshot,
            candidate=candidate,
            silver_manifest=silver_manifest,
            silver_parquet=silver_parquet,
        ):
            return NvdAuthoritativeWatermarkPromotionResultV1(
                status="already_committed",
                update_id=candidate.update_id,
                persisted=snapshot,
            )

        eligibility = self._verifier.verify(
            committed_through_at=(
                snapshot.watermark.committed_through_at
            ),
            candidate=candidate,
            silver_manifest=silver_manifest,
            silver_parquet=silver_parquet,
        )

        target = self._build_target_watermark(
            eligibility=eligibility,
        )

        # Promotion eligibility is evidence only. The state owner must
        # revalidate continuity immediately before the conditional write.
        self._transition_validator.validate(
            committed_through_at=(
                snapshot.watermark.committed_through_at
            ),
            candidate=candidate,
        )

        try:
            persisted = self._watermark_store.compare_and_swap(
                watermark=target,
                expected_etag=snapshot.etag,
            )
        except (
            NvdAuthoritativeWatermarkPreconditionFailedError,
            NvdAuthoritativeWatermarkConflictError,
        ) as exc:
            winner = self._watermark_store.load()

            if winner.watermark == target:
                return NvdAuthoritativeWatermarkPromotionResultV1(
                    status="already_committed",
                    update_id=candidate.update_id,
                    persisted=winner,
                )

            raise NvdAuthoritativeWatermarkPromotionConflictError(
                "Authoritative NVD watermark promotion lost CAS to "
                "an incompatible committed state."
            ) from exc

        return NvdAuthoritativeWatermarkPromotionResultV1(
            status="committed",
            update_id=candidate.update_id,
            persisted=persisted,
        )

    @staticmethod
    def _build_target_watermark(
        *,
        eligibility: NvdWatermarkPromotionEligibilityV1,
    ) -> NvdAuthoritativeWatermarkV1:
        """Build the exact authoritative commit authorized by eligibility."""
        return NvdAuthoritativeWatermarkV1(
            committed_through_at=(
                eligibility.next_committed_through_at
            ),
            commit_basis=NvdWatermarkSilverPromotionCommitV1(
                previous_committed_through_at=(
                    eligibility.validated_committed_through_at
                ),
                update_id=eligibility.update_id,
                bronze_manifest=NvdWatermarkEvidenceObjectV1(
                    key=eligibility.bronze_manifest_key,
                    version_id=(
                        eligibility.bronze_manifest_version_id
                    ),
                    sha256=eligibility.bronze_manifest_sha256,
                ),
                silver_manifest=NvdWatermarkEvidenceObjectV1(
                    key=eligibility.silver_manifest_key,
                    version_id=(
                        eligibility.silver_manifest_version_id
                    ),
                    sha256=eligibility.silver_manifest_sha256,
                ),
                silver_parquet=NvdWatermarkEvidenceObjectV1(
                    key=eligibility.silver_parquet_key,
                    version_id=(
                        eligibility.silver_parquet_version_id
                    ),
                    sha256=eligibility.silver_parquet_sha256,
                ),
                logical_record_set_sha256=(
                    eligibility.logical_record_set_sha256
                ),
            ),
        )

    @staticmethod
    def _is_exact_existing_commit(
        *,
        persisted: NvdPersistedAuthoritativeWatermarkV1,
        candidate: NvdWatermarkCandidate,
        silver_manifest: NvdPersistedObjectPayloadV1,
        silver_parquet: NvdPersistedObjectPayloadV1,
    ) -> bool:
        """Recognize only the same exact immutable candidate as idempotent."""
        watermark = persisted.watermark
        basis = watermark.commit_basis

        if not isinstance(
            basis,
            NvdWatermarkSilverPromotionCommitV1,
        ):
            return False

        if watermark.committed_through_at != candidate.window_end_at:
            return False

        return (
            basis.previous_committed_through_at
            == candidate.window_start_at
            and basis.update_id == candidate.update_id
            and basis.bronze_manifest
            == NvdWatermarkEvidenceObjectV1(
                key=candidate.bronze_manifest_key,
                version_id=candidate.bronze_manifest_version_id,
                sha256=candidate.bronze_manifest_sha256,
            )
            and basis.silver_manifest
            == NvdWatermarkEvidenceObjectV1(
                key=silver_manifest.key,
                version_id=silver_manifest.version_id,
                sha256=silver_manifest.sha256,
            )
            and basis.silver_parquet
            == NvdWatermarkEvidenceObjectV1(
                key=silver_parquet.key,
                version_id=silver_parquet.version_id,
                sha256=silver_parquet.sha256,
            )
        )
