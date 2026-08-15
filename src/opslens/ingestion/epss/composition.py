"""Composition root for the EPSS ingestion application."""

from typing import Literal, Protocol, cast

from boto3.session import Session

from opslens.ingestion.epss.adapters.outbound.first_http import (
    FirstHttpEpssSnapshotSource,
)
from opslens.ingestion.epss.adapters.outbound.s3_bronze import (
    S3BronzeSnapshotRepository,
    S3PutObjectClient,
)
from opslens.ingestion.epss.application.key_factory import EpssBronzeKeyFactory
from opslens.ingestion.epss.application.service import IngestEpssSnapshot
from opslens.ingestion.epss.config import EpssIngestionSettings
from opslens.ingestion.epss.domain.parser import EpssSnapshotParser
from opslens.shared.observability.ports import OperationalTelemetry


class _S3ClientFactory(Protocol):
    """Define the minimal AWS client factory required by this composition root."""

    def client(
        self,
        service_name: Literal["s3"],
    ) -> S3PutObjectClient:
        """Create the S3 client required by EPSS ingestion."""
        ...


def build_ingestion_use_case(
    settings: EpssIngestionSettings,
    telemetry: OperationalTelemetry,
    s3_client: S3PutObjectClient,
) -> IngestEpssSnapshot:
    """Build the EPSS ingestion use case from explicit dependencies.

    Args:
        settings: Validated EPSS runtime configuration.
        telemetry: Operational observability implementation.
        s3_client: Minimal S3 client required by the Bronze repository.

    Returns:
        Fully composed EPSS ingestion application service.
    """
    source = FirstHttpEpssSnapshotSource(
        source_url=settings.source_url,
        timeout_seconds=settings.http_timeout_seconds,
        telemetry=telemetry,
    )

    repository = S3BronzeSnapshotRepository(
        client=s3_client,
        bucket_name=settings.bronze_bucket,
        telemetry=telemetry,
    )

    parser = EpssSnapshotParser()

    key_factory = EpssBronzeKeyFactory(
        prefix=settings.bronze_prefix,
    )

    return IngestEpssSnapshot(
        source=source,
        repository=repository,
        parser=parser,
        key_factory=key_factory,
    )


def build_runtime_use_case(
    telemetry: OperationalTelemetry,
) -> IngestEpssSnapshot:
    """Build the production EPSS ingestion use case from runtime configuration.

    Configuration is loaded from environment variables. AWS credentials and
    Region are resolved through the standard AWS SDK credential and
    configuration provider chains.

    Args:
        telemetry: Operational observability implementation.

    Returns:
        Fully composed EPSS ingestion application service.
    """
    settings = EpssIngestionSettings.from_environment()
    s3_client = _build_s3_client()

    return build_ingestion_use_case(
        settings=settings,
        telemetry=telemetry,
        s3_client=s3_client,
    )


def _build_s3_client() -> S3PutObjectClient:
    """Create the AWS S3 client required by the Bronze repository."""
    client_factory = cast(
        _S3ClientFactory,
        Session(),
    )

    return client_factory.client("s3")
