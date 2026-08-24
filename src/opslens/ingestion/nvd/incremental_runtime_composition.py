"""Composition root for authoritative NVD incremental ingestion runtime."""

from typing import Literal, Protocol, cast

from boto3.session import Session

from opslens.ingestion.nvd.adapters.outbound.nvd_cve_api import (
    NvdHttpCveApiSource,
)
from opslens.ingestion.nvd.adapters.outbound.s3_authoritative_watermark import (
    S3NvdAuthoritativeWatermarkClient,
    S3NvdAuthoritativeWatermarkStore,
)
from opslens.ingestion.nvd.adapters.outbound.s3_incremental_bronze import (
    S3NvdIncrementalBronzeClient,
    S3NvdIncrementalBronzeRepository,
)
from opslens.ingestion.nvd.adapters.outbound.s3_incremental_complete import (
    S3NvdIncrementalCompleteManifestClient,
    S3NvdIncrementalCompleteManifestReader,
)
from opslens.ingestion.nvd.application.incremental_attempt import (
    NvdIncrementalAttemptIdFactory,
)
from opslens.ingestion.nvd.application.incremental_complete import (
    NvdIncrementalManifestParser,
)
from opslens.ingestion.nvd.application.incremental_key_factory import (
    NvdIncrementalKeyFactory,
)
from opslens.ingestion.nvd.application.incremental_manifest import (
    NvdIncrementalManifestFactory,
    NvdIncrementalManifestSerializer,
)
from opslens.ingestion.nvd.application.incremental_runtime_plan import (
    NvdIncrementalRuntimePlannerV1,
)
from opslens.ingestion.nvd.application.incremental_runtime_service import (
    RunNvdIncrementalRuntimeV1,
)
from opslens.ingestion.nvd.application.incremental_service import (
    IngestNvdIncrementalWindow,
)
from opslens.ingestion.nvd.application.watermark import (
    NvdWatermarkCandidateFactory,
)
from opslens.ingestion.nvd.domain.api_page import (
    NvdCveApiPageParser,
)
from opslens.ingestion.nvd.incremental_runtime_config import (
    NvdIncrementalRuntimeSettingsV1,
)
from opslens.shared.observability.ports import OperationalTelemetry


class _S3ClientFactory(Protocol):
    """Define the AWS client factory required by incremental runtime."""

    def client(
        self,
        service_name: Literal["s3"],
    ) -> object:
        """Create one AWS S3 client."""
        ...


def build_incremental_runtime_use_case(
    *,
    settings: NvdIncrementalRuntimeSettingsV1,
    telemetry: OperationalTelemetry,
    watermark_s3_client: S3NvdAuthoritativeWatermarkClient,
    bronze_s3_client: S3NvdIncrementalBronzeClient,
) -> RunNvdIncrementalRuntimeV1:
    """Compose one production-capable NVD incremental application service."""
    watermark_store = S3NvdAuthoritativeWatermarkStore(
        client=watermark_s3_client,
        bucket_name=settings.bucket_name,
        object_key=settings.watermark_key,
        telemetry=telemetry,
    )

    source = NvdHttpCveApiSource(
        base_url=settings.cve_api_base_url,
        timeout_seconds=settings.cve_api_timeout_seconds,
        max_response_bytes=settings.cve_api_max_response_bytes,
        minimum_interval_seconds=(
            settings.cve_api_minimum_interval_seconds
        ),
        max_attempts=settings.cve_api_max_attempts,
        telemetry=telemetry,
    )

    bronze_repository = S3NvdIncrementalBronzeRepository(
        client=bronze_s3_client,
        bucket_name=settings.bucket_name,
        telemetry=telemetry,
    )

    complete_reader = S3NvdIncrementalCompleteManifestReader(
        client=cast(
            S3NvdIncrementalCompleteManifestClient,
            bronze_s3_client,
        ),
        bucket_name=settings.bucket_name,
        parser=NvdIncrementalManifestParser(),
        telemetry=telemetry,
    )

    ingestor = IngestNvdIncrementalWindow(
        source=source,
        repository=bronze_repository,
        complete_reader=complete_reader,
        page_parser=NvdCveApiPageParser(),
        attempt_id_factory=NvdIncrementalAttemptIdFactory(),
        key_factory=NvdIncrementalKeyFactory(
            prefix=settings.bronze_prefix,
        ),
        manifest_factory=NvdIncrementalManifestFactory(),
        manifest_serializer=NvdIncrementalManifestSerializer(),
        candidate_factory=NvdWatermarkCandidateFactory(),
    )

    return RunNvdIncrementalRuntimeV1(
        watermark_reader=watermark_store,
        planner=NvdIncrementalRuntimePlannerV1(),
        ingestor=ingestor,
    )


def build_incremental_runtime_from_environment(
    *,
    telemetry: OperationalTelemetry,
) -> RunNvdIncrementalRuntimeV1:
    """Compose incremental NVD runtime from environment configuration."""
    settings = NvdIncrementalRuntimeSettingsV1.from_environment()

    client_factory = cast(
        _S3ClientFactory,
        Session(),
    )

    s3_client = client_factory.client(
        "s3"
    )

    return build_incremental_runtime_use_case(
        settings=settings,
        telemetry=telemetry,
        watermark_s3_client=cast(
            S3NvdAuthoritativeWatermarkClient,
            s3_client,
        ),
        bronze_s3_client=cast(
            S3NvdIncrementalBronzeClient,
            s3_client,
        ),
    )
