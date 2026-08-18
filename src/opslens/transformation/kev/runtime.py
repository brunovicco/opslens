"""Runtime orchestration for CISA KEV Bronze-to-Silver processing."""

from typing import Protocol

from opslens.ingestion.kev.domain.models import KevCatalogSnapshot
from opslens.transformation.kev.adapters.inbound.s3_event import (
    KevBronzeObjectReference,
)
from opslens.transformation.kev.adapters.outbound.s3_bronze import (
    KevBronzeObject,
)
from opslens.transformation.kev.application.runtime_models import (
    KevSilverSourceEvidence,
    KevSilverTransformationResult,
)


class KevBronzeObjectReader(Protocol):
    """Read one exact transport-verified KEV Bronze object."""

    def get(
        self,
        reference: KevBronzeObjectReference,
    ) -> KevBronzeObject:
        """Read the exact Bronze version referenced by the event."""
        ...


class KevBronzeSnapshotVerifier(Protocol):
    """Verify semantic provenance for one KEV Bronze object."""

    def verify(
        self,
        bronze: KevBronzeObject,
    ) -> KevCatalogSnapshot:
        """Reconstruct a semantically verified KEV catalog snapshot."""
        ...


class KevSilverTransformationUseCase(Protocol):
    """Transform verified KEV source evidence into Silver."""

    def transform(
        self,
        evidence: KevSilverSourceEvidence,
    ) -> KevSilverTransformationResult:
        """Produce one immutable KEV Silver artifact."""
        ...


class KevSilverObjectProcessor:
    """Coordinate one complete event-reference-to-Silver processing flow."""

    def __init__(
        self,
        *,
        bronze_reader: KevBronzeObjectReader,
        provenance_verifier: KevBronzeSnapshotVerifier,
        transformation_service: KevSilverTransformationUseCase,
    ) -> None:
        """Initialize runtime processing dependencies.

        Args:
            bronze_reader: Exact-version Bronze evidence reader.
            provenance_verifier: Semantic provenance verifier.
            transformation_service: Deterministic Silver use case.
        """
        self._bronze_reader = bronze_reader
        self._provenance_verifier = provenance_verifier
        self._transformation_service = transformation_service

    def process(
        self,
        reference: KevBronzeObjectReference,
    ) -> KevSilverTransformationResult:
        """Process one validated S3 Bronze object reference.

        Args:
            reference: Strict, versioned object reference from the S3 event.

        Returns:
            Deterministic KEV Silver transformation result.

        Raises:
            Exception: Propagates any read, provenance, transformation, or
                persistence failure so the outer Lambda runtime can fail the
                invocation and preserve asynchronous retry semantics.
        """
        bronze = self._bronze_reader.get(reference)

        snapshot = self._provenance_verifier.verify(bronze)

        evidence = KevSilverSourceEvidence(
            snapshot=snapshot,
            bronze_key=bronze.reference.key,
            bronze_version_id=bronze.version_id,
            bronze_etag=bronze.etag,
        )

        return self._transformation_service.transform(evidence)
