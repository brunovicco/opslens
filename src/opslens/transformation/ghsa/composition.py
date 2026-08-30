"""Composition root for GHSA Silver transformation runtime."""

from dataclasses import dataclass
from typing import Literal, Protocol, cast

from boto3.session import Session

from opslens.ingestion.ghsa.application.attempt import GhsaAttemptIdFactory
from opslens.ingestion.ghsa.application.key_factory import GhsaBronzeKeyFactory
from opslens.ingestion.ghsa.application.manifest import (
    GhsaCompleteManifestSerializer,
)
from opslens.ingestion.ghsa.domain.api_page import GhsaAdvisoryApiPageParser
from opslens.shared.observability.ports import OperationalTelemetry
from opslens.transformation.ghsa.adapters.outbound.s3_exact_object import (
    S3GetObjectVersionClient,
    S3VersionedGhsaBronzeObjectReader,
)
from opslens.transformation.ghsa.adapters.outbound.s3_silver_completion import (
    S3GhsaSilverCompletionClient,
    S3GhsaSilverCompletionRepository,
)
from opslens.transformation.ghsa.adapters.outbound.s3_silver_content import (
    S3GhsaSilverContentClient,
    S3GhsaSilverContentRepository,
)
from opslens.transformation.ghsa.application.record_composer import (
    GhsaSilverRecordComposerV1,
)
from opslens.transformation.ghsa.completion.key_factory import (
    GhsaSilverKeyFactoryV1,
)
from opslens.transformation.ghsa.completion.manifest import (
    GhsaSilverCompletionManifestFactoryV1,
    GhsaSilverCompletionManifestSerializerV1,
)
from opslens.transformation.ghsa.completion.preparation import (
    GhsaSilverContentPreparerV1,
)
from opslens.transformation.ghsa.completion.service import (
    GhsaSilverPersistenceServiceV1,
)
from opslens.transformation.ghsa.config import GhsaSilverTransformationSettings
from opslens.transformation.ghsa.domain.collections_transformer import (
    GhsaAdvisoryCollectionsTransformer,
)
from opslens.transformation.ghsa.domain.transformer import (
    GhsaAdvisoryCoreTransformer,
)
from opslens.transformation.ghsa.domain.vulnerabilities_transformer import (
    GhsaVulnerabilitiesTransformer,
)
from opslens.transformation.ghsa.runtime.manifest_processor import (
    GhsaBronzeManifestProcessorV1,
)
from opslens.transformation.ghsa.runtime.materializer import GhsaSilverMaterializerV1
from opslens.transformation.ghsa.runtime.page_processor import (
    GhsaBronzePageProcessorV1,
)
from opslens.transformation.ghsa.runtime.processor import GhsaSilverRuntimeProcessorV1
from opslens.transformation.ghsa.runtime.record_processor import (
    GhsaSilverRecordProcessorV1,
)
from opslens.transformation.ghsa.runtime.service import GhsaSilverRuntimeServiceV1
from opslens.transformation.ghsa.serialization.logical_hash import (
    GhsaLogicalRecordSetHasherV1,
)
from opslens.transformation.ghsa.serialization.parquet import (
    GhsaSilverParquetSerializerV1,
)


class _S3ClientFactory(Protocol):
    """Define the minimal AWS client factory required by composition."""

    def client(
        self,
        service_name: Literal["s3"],
    ) -> object:
        """Create one AWS S3 client."""
        ...


@dataclass(frozen=True, slots=True)
class GhsaSilverRuntimeDependencies:
    """Group dependencies required by the GHSA Silver Lambda runtime."""

    processor: GhsaSilverRuntimeProcessorV1


def build_runtime_dependencies(
    telemetry: OperationalTelemetry,
) -> GhsaSilverRuntimeDependencies:
    """Build production GHSA Silver dependencies from environment and AWS SDK."""
    settings = GhsaSilverTransformationSettings.from_environment()
    s3_client = _build_s3_client()

    return compose_runtime_dependencies(
        settings=settings,
        telemetry=telemetry,
        bronze_client=cast(S3GetObjectVersionClient, s3_client),
        content_client=cast(S3GhsaSilverContentClient, s3_client),
        completion_client=cast(S3GhsaSilverCompletionClient, s3_client),
    )


def compose_runtime_dependencies(
    *,
    settings: GhsaSilverTransformationSettings,
    telemetry: OperationalTelemetry,
    bronze_client: S3GetObjectVersionClient,
    content_client: S3GhsaSilverContentClient,
    completion_client: S3GhsaSilverCompletionClient,
) -> GhsaSilverRuntimeDependencies:
    """Compose GHSA Silver from explicit deterministic infrastructure ports."""
    bronze_key_factory = GhsaBronzeKeyFactory()
    silver_key_factory = GhsaSilverKeyFactoryV1()

    bronze_reader = S3VersionedGhsaBronzeObjectReader(
        client=bronze_client,
        bucket_name=settings.data_bucket,
        telemetry=telemetry,
    )
    record_composer = GhsaSilverRecordComposerV1(
        core_transformer=GhsaAdvisoryCoreTransformer(),
        collections_transformer=GhsaAdvisoryCollectionsTransformer(),
        vulnerabilities_transformer=GhsaVulnerabilitiesTransformer(),
    )
    preparation_service = GhsaSilverRuntimeServiceV1(
        object_reader=bronze_reader,
        manifest_processor=GhsaBronzeManifestProcessorV1(
            key_factory=bronze_key_factory,
            serializer=GhsaCompleteManifestSerializer(),
        ),
        source_page_parser=GhsaAdvisoryApiPageParser(),
        attempt_id_factory=GhsaAttemptIdFactory(),
        page_processor=GhsaBronzePageProcessorV1(),
        record_processor=GhsaSilverRecordProcessorV1(
            composer=record_composer,
        ),
        materializer=GhsaSilverMaterializerV1(
            logical_hasher=GhsaLogicalRecordSetHasherV1(),
        ),
    )
    content_preparer = GhsaSilverContentPreparerV1(
        key_factory=silver_key_factory,
        parquet_serializer=GhsaSilverParquetSerializerV1(),
    )
    content_repository = S3GhsaSilverContentRepository(
        client=content_client,
        bucket_name=settings.data_bucket,
        telemetry=telemetry,
    )
    completion_repository = S3GhsaSilverCompletionRepository(
        client=completion_client,
        bucket_name=settings.data_bucket,
        telemetry=telemetry,
    )
    persistence_service = GhsaSilverPersistenceServiceV1(
        content_preparer=content_preparer,
        content_repository=content_repository,
        manifest_factory=GhsaSilverCompletionManifestFactoryV1(
            key_factory=silver_key_factory,
        ),
        manifest_serializer=GhsaSilverCompletionManifestSerializerV1(
            key_factory=silver_key_factory,
        ),
        completion_repository=completion_repository,
    )

    return GhsaSilverRuntimeDependencies(
        processor=GhsaSilverRuntimeProcessorV1(
            preparation_service=preparation_service,
            persistence_service=persistence_service,
        )
    )


def _build_s3_client() -> object:
    """Create the shared AWS S3 client used through minimal typed views."""
    client_factory = cast(_S3ClientFactory, Session())
    return client_factory.client("s3")
