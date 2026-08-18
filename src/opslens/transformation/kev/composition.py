"""Composition root for the CISA KEV Silver transformation runtime."""

from dataclasses import dataclass
from typing import Literal, Protocol, cast

from boto3.session import Session

from opslens.ingestion.kev.domain.parser import KevCatalogParser
from opslens.shared.observability.ports import OperationalTelemetry
from opslens.transformation.kev.adapters.inbound.s3_event import (
    KevS3EventParser,
)
from opslens.transformation.kev.adapters.outbound.bronze_provenance import (
    KevBronzeProvenanceVerifier,
)
from opslens.transformation.kev.adapters.outbound.parquet import (
    PyArrowSilverKevRecordWriter,
)
from opslens.transformation.kev.adapters.outbound.s3_bronze import (
    S3GetObjectVersionClient,
    S3VersionedKevBronzeRepository,
)
from opslens.transformation.kev.adapters.outbound.s3_silver import (
    S3PutSilverObjectClient,
    S3SilverKevArtifactRepository,
)
from opslens.transformation.kev.application.key_factory import (
    KevSilverKeyFactory,
)
from opslens.transformation.kev.application.service import (
    KevSilverTransformationService,
)
from opslens.transformation.kev.config import (
    KevSilverTransformationSettings,
)
from opslens.transformation.kev.domain.transformer import (
    KevSilverTransformer,
)
from opslens.transformation.kev.runtime import (
    KevSilverObjectProcessor,
)


class S3KevSilverRuntimeClient(
    S3GetObjectVersionClient,
    S3PutSilverObjectClient,
    Protocol,
):
    """Combine the minimal S3 capabilities required by KEV Silver."""


class _S3ClientFactory(Protocol):
    """Define the minimal AWS client factory required by composition."""

    def client(
        self,
        service_name: Literal["s3"],
    ) -> S3KevSilverRuntimeClient:
        """Create the S3 client required by KEV Silver."""
        ...


@dataclass(frozen=True, slots=True)
class KevSilverRuntimeDependencies:
    """Group dependencies required by the KEV Silver Lambda runtime."""

    processor: KevSilverObjectProcessor
    event_parser: KevS3EventParser


def build_runtime_dependencies(
    telemetry: OperationalTelemetry,
) -> KevSilverRuntimeDependencies:
    """Build production dependencies from environment and AWS SDK.

    Args:
        telemetry: Operational observability implementation.

    Returns:
        Fully composed KEV Silver runtime dependencies.
    """
    settings = KevSilverTransformationSettings.from_environment()

    return compose_runtime_dependencies(
        settings=settings,
        telemetry=telemetry,
        s3_client=_build_s3_client(),
    )


def compose_runtime_dependencies(
    *,
    settings: KevSilverTransformationSettings,
    telemetry: OperationalTelemetry,
    s3_client: S3KevSilverRuntimeClient,
) -> KevSilverRuntimeDependencies:
    """Compose KEV Silver runtime from explicit dependencies.

    Args:
        settings: Validated KEV Silver runtime configuration.
        telemetry: Operational observability implementation.
        s3_client: Minimal S3 client required by runtime adapters.

    Returns:
        Fully composed object processor and event parser.
    """
    bronze_repository = S3VersionedKevBronzeRepository(
        client=s3_client,
        bucket_name=settings.data_bucket,
        telemetry=telemetry,
    )

    provenance_verifier = KevBronzeProvenanceVerifier(
        parser=KevCatalogParser(),
    )

    silver_repository = S3SilverKevArtifactRepository(
        client=s3_client,
        bucket_name=settings.data_bucket,
        telemetry=telemetry,
    )

    transformation_service = KevSilverTransformationService(
        transformer=KevSilverTransformer(),
        record_writer=PyArrowSilverKevRecordWriter(),
        silver_repository=silver_repository,
        key_factory=KevSilverKeyFactory(
            prefix=settings.silver_prefix,
        ),
    )

    processor = KevSilverObjectProcessor(
        bronze_reader=bronze_repository,
        provenance_verifier=provenance_verifier,
        transformation_service=transformation_service,
    )

    event_parser = KevS3EventParser(
        expected_bucket=settings.data_bucket,
    )

    return KevSilverRuntimeDependencies(
        processor=processor,
        event_parser=event_parser,
    )


def _build_s3_client() -> S3KevSilverRuntimeClient:
    """Create the AWS S3 client required by KEV Silver runtime."""
    client_factory = cast(
        _S3ClientFactory,
        Session(),
    )

    return client_factory.client("s3")
