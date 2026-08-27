"""Composition root for the permanent NVD analytics projection runtime."""

from dataclasses import dataclass
from typing import Literal, Protocol, cast

from boto3.session import Session

from opslens.shared.observability.ports import OperationalTelemetry
from opslens.transformation.nvd.adapters.outbound.analytics_projection_repository import (
    NvdAnalyticsProjectionRepositoryBindingV1,
)
from opslens.transformation.nvd.adapters.outbound.s3_analytics_evidence import (
    S3NvdAnalyticsEvidenceClient,
    S3NvdAnalyticsEvidenceReaderV1,
)
from opslens.transformation.nvd.adapters.outbound.s3_analytics_projection import (
    S3NvdAnalyticsProjectionClient,
    S3NvdAnalyticsProjectionRepositoryV1,
)
from opslens.transformation.nvd.analytics_projection_config import (
    NvdAnalyticsProjectionRuntimeSettingsV1,
)
from opslens.transformation.nvd.application.analytics_projection_evidence_loader import (
    NvdAnalyticsProjectionEvidenceLoaderV1,
)
from opslens.transformation.nvd.application.analytics_projection_service import (
    NvdAnalyticsProjectionServiceV1,
)


class _S3ClientFactory(Protocol):
    """Define the AWS client factory required by analytics composition."""

    def client(
        self,
        service_name: Literal["s3"],
    ) -> object:
        """Create one AWS S3 client."""
        ...


@dataclass(frozen=True, slots=True)
class NvdAnalyticsProjectionRuntimeDependencies:
    """Group dependencies required by the NVD analytics Lambda runtime."""

    service: NvdAnalyticsProjectionServiceV1


def compose_analytics_projection_runtime_dependencies(
    *,
    settings: NvdAnalyticsProjectionRuntimeSettingsV1,
    telemetry: OperationalTelemetry,
    evidence_s3_client: S3NvdAnalyticsEvidenceClient,
    projection_s3_client: S3NvdAnalyticsProjectionClient,
) -> NvdAnalyticsProjectionRuntimeDependencies:
    """Compose the analytics runtime from explicit infrastructure boundaries."""
    exact_reader = S3NvdAnalyticsEvidenceReaderV1(
        client=evidence_s3_client,
        bucket_name=settings.data_bucket,
        telemetry=telemetry,
    )
    evidence_loader = NvdAnalyticsProjectionEvidenceLoaderV1(
        object_reader=exact_reader,
    )
    s3_repository = S3NvdAnalyticsProjectionRepositoryV1(
        client=projection_s3_client,
        bucket_name=settings.data_bucket,
        telemetry=telemetry,
    )
    repository = NvdAnalyticsProjectionRepositoryBindingV1(
        repository=s3_repository,
    )

    return NvdAnalyticsProjectionRuntimeDependencies(
        service=NvdAnalyticsProjectionServiceV1(
            evidence_loader=evidence_loader,
            repository=repository,
        ),
    )


def build_analytics_projection_runtime_dependencies(
    *,
    telemetry: OperationalTelemetry,
) -> NvdAnalyticsProjectionRuntimeDependencies:
    """Build production analytics dependencies from environment and AWS SDK."""
    settings = NvdAnalyticsProjectionRuntimeSettingsV1.from_environment()
    client_factory = cast(
        _S3ClientFactory,
        Session(),
    )
    s3_client = client_factory.client(
        "s3"
    )

    return compose_analytics_projection_runtime_dependencies(
        settings=settings,
        telemetry=telemetry,
        evidence_s3_client=cast(
            S3NvdAnalyticsEvidenceClient,
            s3_client,
        ),
        projection_s3_client=cast(
            S3NvdAnalyticsProjectionClient,
            s3_client,
        ),
    )
