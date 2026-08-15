"""Composition root for the EPSS Silver transformation application."""

from typing import Literal, Protocol, cast

from boto3.session import Session

from opslens.ingestion.epss.domain.parser import EpssSnapshotParser
from opslens.shared.observability.ports import OperationalTelemetry
from opslens.transformation.epss.adapters.outbound.parquet import (
    PyArrowSilverEpssRecordWriter,
)
from opslens.transformation.epss.adapters.outbound.s3_bronze import (
    S3BronzeEpssSnapshotRepository,
    S3GetObjectClient,
)
from opslens.transformation.epss.adapters.outbound.s3_silver import (
    S3PutSilverObjectClient,
    S3SilverEpssArtifactRepository,
)
from opslens.transformation.epss.application.key_factory import (
    EpssSilverKeyFactory,
)
from opslens.transformation.epss.application.service import (
    EpssSilverTransformationService,
)
from opslens.transformation.epss.config import (
    EpssSilverTransformationSettings,
)
from opslens.transformation.epss.domain.transformer import (
    EpssSilverTransformer,
)


class S3SilverTransformationClient(
    S3GetObjectClient,
    S3PutSilverObjectClient,
    Protocol,
):
    """Combine the minimal S3 capabilities required by Silver transformation."""


class _S3ClientFactory(Protocol):
    """Define the minimal AWS client factory required by this composition root."""

    def client(
        self,
        service_name: Literal["s3"],
    ) -> S3SilverTransformationClient:
        """Create the S3 client required by EPSS Silver transformation."""
        ...


def build_transformation_service(
    *,
    settings: EpssSilverTransformationSettings,
    telemetry: OperationalTelemetry,
    s3_client: S3SilverTransformationClient,
) -> EpssSilverTransformationService:
    """Build the EPSS Silver application service from explicit dependencies.

    Args:
        settings: Validated Silver runtime configuration.
        telemetry: Operational observability implementation.
        s3_client: Minimal S3 client required by Bronze and Silver adapters.

    Returns:
        Fully composed EPSS Silver transformation service.
    """
    bronze_repository = S3BronzeEpssSnapshotRepository(
        client=s3_client,
        bucket_name=settings.data_bucket,
        telemetry=telemetry,
    )

    silver_repository = S3SilverEpssArtifactRepository(
        client=s3_client,
        bucket_name=settings.data_bucket,
        telemetry=telemetry,
    )

    return EpssSilverTransformationService(
        bronze_repository=bronze_repository,
        parser=EpssSnapshotParser(),
        transformer=EpssSilverTransformer(),
        record_writer=PyArrowSilverEpssRecordWriter(),
        silver_repository=silver_repository,
        key_factory=EpssSilverKeyFactory(
            prefix=settings.silver_prefix,
        ),
    )


def build_runtime_transformation_service(
    telemetry: OperationalTelemetry,
) -> EpssSilverTransformationService:
    """Build the production service from environment and AWS SDK configuration.

    AWS credentials and Region are resolved through the standard AWS SDK
    credential and configuration provider chains.

    Args:
        telemetry: Operational observability implementation.

    Returns:
        Fully composed EPSS Silver transformation service.
    """
    settings = EpssSilverTransformationSettings.from_environment()
    s3_client = _build_s3_client()

    return build_transformation_service(
        settings=settings,
        telemetry=telemetry,
        s3_client=s3_client,
    )


def _build_s3_client() -> S3SilverTransformationClient:
    """Create the AWS S3 client required by Silver transformation."""
    client_factory = cast(
        _S3ClientFactory,
        Session(),
    )

    return client_factory.client("s3")
