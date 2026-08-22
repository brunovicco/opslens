"""Composition root for the NVD Silver transformation runtime."""

from dataclasses import dataclass
from typing import Literal, Protocol, cast

from boto3.session import Session

from opslens.shared.observability.ports import OperationalTelemetry
from opslens.transformation.nvd.adapters.outbound.s3_exact_object import (
    S3GetObjectVersionClient,
    S3VersionedNvdBronzeObjectReader,
)
from opslens.transformation.nvd.adapters.outbound.s3_silver_completion import (
    S3NvdSilverCompletionClient,
    S3NvdSilverCompletionReplayVerifier,
    S3NvdSilverCompletionRepository,
)
from opslens.transformation.nvd.adapters.outbound.s3_silver_parquet import (
    S3NvdSilverParquetRepository,
    S3PutNvdSilverObjectClient,
)
from opslens.transformation.nvd.adapters.outbound.s3_silver_replay import (
    S3NvdSilverParquetReplayVerifier,
    S3NvdSilverReplayClient,
)
from opslens.transformation.nvd.application.completion_persistence_service import (
    NvdSilverCompletionPersistenceServiceV1,
)
from opslens.transformation.nvd.application.persistence_service import (
    NvdSilverPersistenceServiceV1,
)
from opslens.transformation.nvd.application.record_composer import (
    NvdSilverRecordComposerV1,
)
from opslens.transformation.nvd.application.request_loader import (
    NvdSilverTransformRequestLoaderV1,
)
from opslens.transformation.nvd.application.service import (
    NvdSilverPrepareServiceV1,
)
from opslens.transformation.nvd.application.source_reader import (
    NvdSilverSourceBatchReaderV1,
)
from opslens.transformation.nvd.completion.key_factory import (
    NvdSilverKeyFactoryV1,
)
from opslens.transformation.nvd.completion.manifest import (
    NvdSilverCompletionManifestFactoryV1,
    NvdSilverCompletionManifestSerializerV1,
)
from opslens.transformation.nvd.config import (
    NvdSilverTransformationSettings,
)
from opslens.transformation.nvd.domain.collections_transformer import (
    NvdCveCollectionsTransformer,
)
from opslens.transformation.nvd.domain.configurations_transformer import (
    NvdCpeConfigurationsTransformer,
)
from opslens.transformation.nvd.domain.cvss_transformer import (
    NvdCvssMetricsTransformer,
)
from opslens.transformation.nvd.domain.transformer import (
    NvdCveCoreTransformer,
)
from opslens.transformation.nvd.provenance.verifier import (
    NvdBronzeEvidenceVerifierV1,
    NvdSilverProvenanceFactoryV1,
)
from opslens.transformation.nvd.runtime import (
    NvdSilverRuntimeProcessor,
)
from opslens.transformation.nvd.serialization.parquet import (
    NvdSilverParquetSerializerV1,
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
class NvdSilverRuntimeDependencies:
    """Group dependencies required by the NVD Silver runtime."""

    processor: NvdSilverRuntimeProcessor


def build_runtime_dependencies(
    telemetry: OperationalTelemetry,
) -> NvdSilverRuntimeDependencies:
    """Build production NVD Silver dependencies from environment and AWS SDK."""
    settings = NvdSilverTransformationSettings.from_environment()
    s3_client = _build_s3_client()

    return compose_runtime_dependencies(
        settings=settings,
        telemetry=telemetry,
        bronze_client=cast(
            S3GetObjectVersionClient,
            s3_client,
        ),
        parquet_write_client=cast(
            S3PutNvdSilverObjectClient,
            s3_client,
        ),
        parquet_replay_client=cast(
            S3NvdSilverReplayClient,
            s3_client,
        ),
        completion_client=cast(
            S3NvdSilverCompletionClient,
            s3_client,
        ),
    )


def compose_runtime_dependencies(
    *,
    settings: NvdSilverTransformationSettings,
    telemetry: OperationalTelemetry,
    bronze_client: S3GetObjectVersionClient,
    parquet_write_client: S3PutNvdSilverObjectClient,
    parquet_replay_client: S3NvdSilverReplayClient,
    completion_client: S3NvdSilverCompletionClient,
) -> NvdSilverRuntimeDependencies:
    """Compose NVD Silver runtime from explicit infrastructure boundaries."""
    key_factory = NvdSilverKeyFactoryV1()

    bronze_reader = S3VersionedNvdBronzeObjectReader(
        client=bronze_client,
        bucket_name=settings.data_bucket,
        telemetry=telemetry,
    )

    request_loader = NvdSilverTransformRequestLoaderV1(
        object_reader=bronze_reader,
    )

    record_composer = NvdSilverRecordComposerV1(
        core_transformer=NvdCveCoreTransformer(),
        collections_transformer=NvdCveCollectionsTransformer(),
        cvss_transformer=NvdCvssMetricsTransformer(),
        configurations_transformer=NvdCpeConfigurationsTransformer(),
        provenance_factory=NvdSilverProvenanceFactoryV1(),
    )

    prepare_service = NvdSilverPrepareServiceV1(
        evidence_verifier=NvdBronzeEvidenceVerifierV1(),
        source_reader=NvdSilverSourceBatchReaderV1(),
        record_composer=record_composer,
        parquet_serializer=NvdSilverParquetSerializerV1(),
        key_factory=key_factory,
    )

    parquet_repository = S3NvdSilverParquetRepository(
        client=parquet_write_client,
        bucket_name=settings.data_bucket,
        telemetry=telemetry,
    )

    parquet_replay_verifier = S3NvdSilverParquetReplayVerifier(
        client=parquet_replay_client,
        bucket_name=settings.data_bucket,
        telemetry=telemetry,
    )

    parquet_persistence_service = NvdSilverPersistenceServiceV1(
        parquet_repository=parquet_repository,
        replay_verifier=parquet_replay_verifier,
        completion_factory=NvdSilverCompletionManifestFactoryV1(
            key_factory=key_factory,
        ),
        completion_serializer=NvdSilverCompletionManifestSerializerV1(),
    )

    completion_repository = S3NvdSilverCompletionRepository(
        client=completion_client,
        bucket_name=settings.data_bucket,
        telemetry=telemetry,
    )

    completion_replay_verifier = S3NvdSilverCompletionReplayVerifier(
        client=completion_client,
        bucket_name=settings.data_bucket,
        telemetry=telemetry,
    )

    completion_persistence_service = NvdSilverCompletionPersistenceServiceV1(
        repository=completion_repository,
        replay_verifier=completion_replay_verifier,
    )

    processor = NvdSilverRuntimeProcessor(
        request_loader=request_loader,
        prepare_service=prepare_service,
        parquet_persistence_service=parquet_persistence_service,
        completion_persistence_service=completion_persistence_service,
    )

    return NvdSilverRuntimeDependencies(
        processor=processor,
    )


def _build_s3_client() -> object:
    """Create the shared AWS S3 client used through minimal typed views."""
    client_factory = cast(
        _S3ClientFactory,
        Session(),
    )

    return client_factory.client("s3")
