"""Composition root for the NVD authoritative watermark-promotion runtime."""

from dataclasses import dataclass
from typing import Literal, Protocol, cast

from boto3.session import Session

from opslens.ingestion.nvd.adapters.outbound.s3_authoritative_watermark import (
    S3NvdAuthoritativeWatermarkClient,
    S3NvdAuthoritativeWatermarkStore,
)
from opslens.shared.observability.ports import OperationalTelemetry
from opslens.transformation.nvd.adapters.outbound.s3_promotion_evidence import (
    S3NvdPromotionEvidenceClient,
    S3NvdPromotionEvidenceReaderV1,
)
from opslens.transformation.nvd.application.watermark_promotion_evidence_loader import (
    NvdWatermarkPromotionEvidenceLoaderV1,
)
from opslens.transformation.nvd.application.watermark_promotion_runtime import (
    NvdWatermarkPromotionRuntimeV1,
)
from opslens.transformation.nvd.application.watermark_promotion_service import (
    NvdAuthoritativeWatermarkPromotionServiceV1,
)
from opslens.transformation.nvd.completion.promotion import (
    NvdWatermarkPromotionVerifierV1,
)
from opslens.transformation.nvd.promotion_config import (
    NvdPromotionRuntimeSettingsV1,
)


class _S3ClientFactory(Protocol):
    """Define the AWS client factory required by promotion composition."""

    def client(
        self,
        service_name: Literal["s3"],
    ) -> object:
        """Create one AWS S3 client."""
        ...


@dataclass(frozen=True, slots=True)
class NvdPromotionRuntimeDependencies:
    """Group dependencies required by the NVD promotion Lambda runtime."""

    runtime: NvdWatermarkPromotionRuntimeV1


def compose_promotion_runtime_dependencies(
    *,
    settings: NvdPromotionRuntimeSettingsV1,
    telemetry: OperationalTelemetry,
    evidence_s3_client: S3NvdPromotionEvidenceClient,
    watermark_s3_client: S3NvdAuthoritativeWatermarkClient,
) -> NvdPromotionRuntimeDependencies:
    """Compose the promotion runtime from explicit infrastructure boundaries."""
    evidence_reader = S3NvdPromotionEvidenceReaderV1(
        client=evidence_s3_client,
        bucket_name=settings.data_bucket,
        telemetry=telemetry,
    )

    evidence_loader = NvdWatermarkPromotionEvidenceLoaderV1(
        object_reader=evidence_reader,
    )

    watermark_store = S3NvdAuthoritativeWatermarkStore(
        client=watermark_s3_client,
        bucket_name=settings.data_bucket,
        object_key=settings.watermark_key,
        telemetry=telemetry,
    )

    promotion_service = NvdAuthoritativeWatermarkPromotionServiceV1(
        watermark_store=watermark_store,
        verifier=NvdWatermarkPromotionVerifierV1(),
    )

    return NvdPromotionRuntimeDependencies(
        runtime=NvdWatermarkPromotionRuntimeV1(
            evidence_loader=evidence_loader,
            promotion_service=promotion_service,
        ),
    )


def build_promotion_runtime_dependencies(
    *,
    telemetry: OperationalTelemetry,
) -> NvdPromotionRuntimeDependencies:
    """Build production promotion dependencies from environment and AWS SDK."""
    settings = NvdPromotionRuntimeSettingsV1.from_environment()

    client_factory = cast(
        _S3ClientFactory,
        Session(),
    )
    s3_client = client_factory.client(
        "s3"
    )

    return compose_promotion_runtime_dependencies(
        settings=settings,
        telemetry=telemetry,
        evidence_s3_client=cast(
            S3NvdPromotionEvidenceClient,
            s3_client,
        ),
        watermark_s3_client=cast(
            S3NvdAuthoritativeWatermarkClient,
            s3_client,
        ),
    )
