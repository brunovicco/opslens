"""Application service for the initial authoritative NVD watermark seed."""

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

from opslens.ingestion.nvd.application.authoritative_watermark import (
    NvdAuthoritativeWatermarkV1,
    NvdWatermarkBootstrapRecoverySeedV1,
    NvdWatermarkEvidenceObjectV1,
)
from opslens.ingestion.nvd.application.authoritative_watermark_store import (
    NvdAuthoritativeWatermarkAlreadyExistsError,
    NvdAuthoritativeWatermarkStoreV1,
    NvdPersistedAuthoritativeWatermarkV1,
)


class NvdAuthoritativeWatermarkSeedConflictError(RuntimeError):
    """Raised when an existing watermark differs from the requested seed."""


@dataclass(frozen=True, slots=True)
class NvdBootstrapRecoverySeedEvidenceV1:
    """Represent audited evidence used to recover the initial NVD boundary.

    This contract exists because the originally intended pre-Bootstrap T0 was
    not persisted by the first runtime implementation. The recovery boundary
    is therefore anchored to the exact NVD source revision represented by an
    immutable Bootstrap COMPLETE manifest.
    """

    source_revision_at: datetime
    bootstrap_manifest: NvdWatermarkEvidenceObjectV1

    def __post_init__(self) -> None:
        """Validate recovery evidence before authoritative-state creation."""
        if (
            self.source_revision_at.tzinfo is None
            or self.source_revision_at.utcoffset() is None
        ):
            raise ValueError(
                "NVD Bootstrap recovery source revision must be timezone-aware."
            )

        normalized = self.source_revision_at.astimezone(UTC)

        object.__setattr__(
            self,
            "source_revision_at",
            normalized,
        )

        manifest_key = self.bootstrap_manifest.key

        if not manifest_key.startswith(
            "bronze/nvd/cve/bootstrap/"
        ):
            raise ValueError(
                "NVD recovery seed must reference a Bootstrap Bronze manifest."
            )

        if not manifest_key.endswith("/manifest.json"):
            raise ValueError(
                "NVD recovery seed must reference a COMPLETE manifest key."
            )


class NvdAuthoritativeWatermarkSeedStatus(StrEnum):
    """Describe the logical outcome of one safe seed attempt."""

    CREATED = "created"
    ALREADY_INITIALIZED = "already_initialized"


@dataclass(frozen=True, slots=True)
class NvdAuthoritativeWatermarkSeedResultV1:
    """Return the exact persisted authoritative state after seeding."""

    status: NvdAuthoritativeWatermarkSeedStatus
    persisted: NvdPersistedAuthoritativeWatermarkV1


class SeedNvdAuthoritativeWatermarkV1:
    """Initialize authoritative NVD state without allowing replacement."""

    def __init__(
        self,
        *,
        store: NvdAuthoritativeWatermarkStoreV1,
    ) -> None:
        """Initialize the use case through dependency inversion."""
        self._store = store

    def execute(
        self,
        *,
        evidence: NvdBootstrapRecoverySeedEvidenceV1,
    ) -> NvdAuthoritativeWatermarkSeedResultV1:
        """Seed or safely replay the initial authoritative boundary.

        The first execution may create the object only if no current
        authoritative state exists.

        A duplicate request is idempotent only when the current exact logical
        watermark equals the requested recovery seed. Any different existing
        state is a conflict and is never replaced.
        """
        desired = self._build_watermark(evidence)

        try:
            persisted = self._store.initialize(
                watermark=desired,
            )
        except NvdAuthoritativeWatermarkAlreadyExistsError:
            return self._resolve_existing(
                desired=desired,
            )

        return NvdAuthoritativeWatermarkSeedResultV1(
            status=NvdAuthoritativeWatermarkSeedStatus.CREATED,
            persisted=persisted,
        )

    def _resolve_existing(
        self,
        *,
        desired: NvdAuthoritativeWatermarkV1,
    ) -> NvdAuthoritativeWatermarkSeedResultV1:
        """Classify an initialization precondition failure safely."""
        current = self._store.load()

        if current.watermark != desired:
            raise NvdAuthoritativeWatermarkSeedConflictError(
                "Existing authoritative NVD watermark does not match "
                "the requested Bootstrap recovery seed."
            )

        return NvdAuthoritativeWatermarkSeedResultV1(
            status=(
                NvdAuthoritativeWatermarkSeedStatus.ALREADY_INITIALIZED
            ),
            persisted=current,
        )

    @staticmethod
    def _build_watermark(
        evidence: NvdBootstrapRecoverySeedEvidenceV1,
    ) -> NvdAuthoritativeWatermarkV1:
        """Construct the only valid initial recovery-seed state."""
        commit_basis = NvdWatermarkBootstrapRecoverySeedV1(
            source_revision_at=evidence.source_revision_at,
            bootstrap_manifest=evidence.bootstrap_manifest,
        )

        return NvdAuthoritativeWatermarkV1(
            committed_through_at=evidence.source_revision_at,
            commit_basis=commit_basis,
        )
