"""Composition root for NVD Bootstrap Bronze ingestion."""

from typing import Literal, Protocol, cast

from boto3.session import Session

from opslens.ingestion.nvd.adapters.outbound.nvd_http import (
    NvdHttpYearlyFeedSource,
)
from opslens.ingestion.nvd.adapters.outbound.s3_bronze import (
    S3NvdBootstrapBronzeRepository,
    S3NvdBronzeClient,
)
from opslens.ingestion.nvd.application.key_factory import (
    NvdBootstrapKeyFactory,
)
from opslens.ingestion.nvd.application.manifest import (
    NvdBootstrapManifestFactory,
    NvdBootstrapManifestSerializer,
)
from opslens.ingestion.nvd.application.service import (
    IngestNvdBootstrapFeed,
)
from opslens.ingestion.nvd.config import NvdIngestionSettings
from opslens.ingestion.nvd.domain.feed_integrity import (
    NvdFeedIntegrityVerifier,
)
from opslens.ingestion.nvd.domain.meta_parser import NvdFeedMetaParser
from opslens.shared.observability.ports import OperationalTelemetry


class _S3ClientFactory(Protocol):
    """Define the minimal AWS client factory required by NVD ingestion."""

    def client(
        self,
        service_name: Literal["s3"],
    ) -> S3NvdBronzeClient:
        """Create the S3 client required by NVD Bootstrap ingestion."""
        ...


def build_ingestion_use_case(
    *,
    settings: NvdIngestionSettings,
    telemetry: OperationalTelemetry,
    s3_client: S3NvdBronzeClient,
) -> IngestNvdBootstrapFeed:
    """Build NVD Bootstrap ingestion from explicit dependencies.

    Args:
        settings: Validated NVD runtime configuration.
        telemetry: Operational observability implementation.
        s3_client: Minimal S3 client required by the Bronze repository.

    Returns:
        Fully composed NVD Bootstrap application service.
    """
    source = NvdHttpYearlyFeedSource(
        base_url=settings.source_base_url,
        timeout_seconds=settings.http_timeout_seconds,
        max_meta_bytes=settings.max_meta_bytes,
        max_feed_bytes=settings.max_feed_bytes,
        telemetry=telemetry,
    )

    repository = S3NvdBootstrapBronzeRepository(
        client=s3_client,
        bucket_name=settings.bronze_bucket,
        telemetry=telemetry,
    )

    return IngestNvdBootstrapFeed(
        source=source,
        repository=repository,
        meta_parser=NvdFeedMetaParser(),
        integrity_verifier=NvdFeedIntegrityVerifier(),
        key_factory=NvdBootstrapKeyFactory(
            prefix=settings.bronze_prefix,
        ),
        manifest_factory=NvdBootstrapManifestFactory(),
        manifest_serializer=NvdBootstrapManifestSerializer(),
    )


def build_runtime_use_case(
    *,
    telemetry: OperationalTelemetry,
) -> IngestNvdBootstrapFeed:
    """Build production-style NVD ingestion from environment configuration."""
    settings = NvdIngestionSettings.from_environment()

    return build_ingestion_use_case(
        settings=settings,
        telemetry=telemetry,
        s3_client=_build_s3_client(),
    )


def _build_s3_client() -> S3NvdBronzeClient:
    """Create the AWS S3 client required by the Bronze repository."""
    client_factory = cast(
        _S3ClientFactory,
        Session(),
    )

    return client_factory.client("s3")
