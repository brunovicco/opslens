"""Application orchestration for permanent NVD analytics projection."""

from dataclasses import dataclass
from typing import Literal, Protocol

from opslens.transformation.nvd.application.analytics_projection_key_factory import (
    NvdAnalyticsProjectionKeyFactoryV1,
    NvdAnalyticsProjectionKeyV1,
    NvdAnalyticsProjectionRequestV1,
)
from opslens.transformation.nvd.application.analytics_projection_models import (
    NvdAnalyticsExactObjectRefV1,
    NvdBootstrapAnalyticsProjectionRequestV1,
    NvdIncrementalAnalyticsProjectionRequestV1,
)


class NvdAnalyticsProjectionReplayRequiredError(RuntimeError):
    """Signal that a deterministic destination must be verified as a replay."""


class InvalidNvdAnalyticsProjectionResultError(RuntimeError):
    """Raised when a projection repository returns evidence outside the contract."""


class NvdAnalyticsProjectionEvidenceUseCase(Protocol):
    """Derive projection eligibility from exact persisted authority."""

    def load_incremental(
        self,
        *,
        watermark_key: str,
        watermark_version_id: str,
    ) -> NvdIncrementalAnalyticsProjectionRequestV1:
        """Load one exact watermark-authorized incremental request."""
        ...

    def load_bootstrap(
        self,
        *,
        silver_complete_key: str,
        silver_complete_version_id: str,
    ) -> NvdBootstrapAnalyticsProjectionRequestV1:
        """Load one explicitly authorized exact Bootstrap seed."""
        ...


class NvdAnalyticsProjectionRepository(Protocol):
    """Persist and verify one deterministic analytics projection."""

    def copy_if_absent(
        self,
        *,
        request: NvdAnalyticsProjectionRequestV1,
        destination: NvdAnalyticsProjectionKeyV1,
    ) -> NvdAnalyticsExactObjectRefV1:
        """Create one projection or raise replay-required on an existing key."""
        ...

    def verify_current(
        self,
        *,
        request: NvdAnalyticsProjectionRequestV1,
        destination: NvdAnalyticsProjectionKeyV1,
    ) -> NvdAnalyticsExactObjectRefV1:
        """Verify the current deterministic destination as an exact replay."""
        ...


NvdAnalyticsProjectionStatus = Literal[
    "projected",
    "already_projected",
]


@dataclass(frozen=True, slots=True)
class NvdAnalyticsProjectionResultV1:
    """Return one verified permanent analytics projection outcome."""

    status: NvdAnalyticsProjectionStatus
    request: NvdAnalyticsProjectionRequestV1
    destination: NvdAnalyticsProjectionKeyV1
    projected_object: NvdAnalyticsExactObjectRefV1


class NvdAnalyticsProjectionServiceV1:
    """Coordinate exact authority loading, deterministic keys, and projection."""

    def __init__(
        self,
        *,
        evidence_loader: NvdAnalyticsProjectionEvidenceUseCase,
        repository: NvdAnalyticsProjectionRepository,
        key_factory: NvdAnalyticsProjectionKeyFactoryV1 | None = None,
    ) -> None:
        """Initialize the application service with explicit boundaries."""
        self._evidence_loader = evidence_loader
        self._repository = repository
        self._key_factory = (
            key_factory
            if key_factory is not None
            else NvdAnalyticsProjectionKeyFactoryV1()
        )

    def project_incremental(
        self,
        *,
        watermark_key: str,
        watermark_version_id: str,
    ) -> NvdAnalyticsProjectionResultV1:
        """Project one exact committed incremental watermark downstream."""
        request = self._evidence_loader.load_incremental(
            watermark_key=watermark_key,
            watermark_version_id=watermark_version_id,
        )
        return self._project(request)

    def project_bootstrap(
        self,
        *,
        silver_complete_key: str,
        silver_complete_version_id: str,
    ) -> NvdAnalyticsProjectionResultV1:
        """Project one explicitly authorized exact Bootstrap Silver seed."""
        request = self._evidence_loader.load_bootstrap(
            silver_complete_key=silver_complete_key,
            silver_complete_version_id=silver_complete_version_id,
        )
        return self._project(request)

    def _project(
        self,
        request: NvdAnalyticsProjectionRequestV1,
    ) -> NvdAnalyticsProjectionResultV1:
        """Materialize or exactly verify one deterministic destination."""
        destination = self._key_factory.build(request)

        try:
            projected = self._repository.copy_if_absent(
                request=request,
                destination=destination,
            )
        except NvdAnalyticsProjectionReplayRequiredError:
            projected = self._repository.verify_current(
                request=request,
                destination=destination,
            )
            status: NvdAnalyticsProjectionStatus = "already_projected"
        else:
            status = "projected"

        self._validate_projected_object(
            request=request,
            destination=destination,
            projected=projected,
        )

        return NvdAnalyticsProjectionResultV1(
            status=status,
            request=request,
            destination=destination,
            projected_object=projected,
        )

    @staticmethod
    def _validate_projected_object(
        *,
        request: NvdAnalyticsProjectionRequestV1,
        destination: NvdAnalyticsProjectionKeyV1,
        projected: NvdAnalyticsExactObjectRefV1,
    ) -> None:
        """Keep repository evidence pinned to the exact authorized source."""
        source = request.silver_parquet

        if projected.key != destination.object_key:
            raise InvalidNvdAnalyticsProjectionResultError(
                "NVD analytics projected object key does not match deterministic destination."
            )

        if projected.sha256 != source.sha256:
            raise InvalidNvdAnalyticsProjectionResultError(
                "NVD analytics projected object SHA-256 does not match exact source."
            )

        if projected.size_bytes != source.size_bytes:
            raise InvalidNvdAnalyticsProjectionResultError(
                "NVD analytics projected object size does not match exact source."
            )
