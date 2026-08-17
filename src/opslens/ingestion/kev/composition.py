"""Composition root for the CISA KEV ingestion application."""

from typing import Literal, Protocol, cast

from boto3.session import Session

from opslens.ingestion.kev.adapters.outbound.cisa_http import (
    CisaHttpKevCatalogSource,
)
from opslens.ingestion.kev.adapters.outbound.s3_bronze import (
    S3BronzeCatalogRepository,
    S3PutObjectClient,
)
from opslens.ingestion.kev.adapters.outbound.system_clock import SystemClock
from opslens.ingestion.kev.application.key_factory import KevBronzeKeyFactory
from opslens.ingestion.kev.application.ports import Clock
from opslens.ingestion.kev.application.service import IngestKevCatalog
from opslens.ingestion.kev.config import KevIngestionSettings
from opslens.ingestion.kev.domain.parser import KevCatalogParser
from opslens.shared.observability.ports import OperationalTelemetry


class _S3ClientFactory(Protocol):
    """Define the minimal AWS client factory required by the composition root."""

    def client(
        self,
        service_name: Literal["s3"],
    ) -> S3PutObjectClient:
        """Create the S3 client required by KEV ingestion."""
        ...


def build_ingestion_use_case(
    settings: KevIngestionSettings,
    telemetry: OperationalTelemetry,
    s3_client: S3PutObjectClient,
    clock: Clock,
) -> IngestKevCatalog:
    """Build the KEV ingestion use case from explicit dependencies.

    Args:
        settings: Validated KEV runtime configuration.
        telemetry: Operational observability implementation.
        s3_client: Minimal S3 client required by the Bronze repository.
        clock: Application clock used to timestamp source observations.

    Returns:
        Fully composed KEV ingestion application service.
    """
    source = CisaHttpKevCatalogSource(
        source_url=settings.source_url,
        timeout_seconds=settings.http_timeout_seconds,
        max_source_bytes=settings.max_source_bytes,
        telemetry=telemetry,
    )

    repository = S3BronzeCatalogRepository(
        client=s3_client,
        bucket_name=settings.bronze_bucket,
        telemetry=telemetry,
    )

    parser = KevCatalogParser()

    key_factory = KevBronzeKeyFactory(
        prefix=settings.bronze_prefix,
    )

    return IngestKevCatalog(
        source=source,
        repository=repository,
        parser=parser,
        key_factory=key_factory,
        clock=clock,
    )


def build_runtime_use_case(
    telemetry: OperationalTelemetry,
) -> IngestKevCatalog:
    """Build the production KEV ingestion use case from runtime configuration."""
    settings = KevIngestionSettings.from_environment()
    s3_client = _build_s3_client()

    return build_ingestion_use_case(
        settings=settings,
        telemetry=telemetry,
        s3_client=s3_client,
        clock=SystemClock(),
    )


def _build_s3_client() -> S3PutObjectClient:
    """Create the AWS S3 client required by the Bronze repository."""
    client_factory = cast(
        _S3ClientFactory,
        Session(),
    )

    return client_factory.client("s3")
