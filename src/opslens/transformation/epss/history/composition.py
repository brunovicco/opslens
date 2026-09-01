"""Composition root for the dedicated historical EPSS transformer Lambda."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, Protocol, cast

import boto3

if TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client

from opslens.ingestion.epss.domain.history import HistoricalEpssSnapshotParser
from opslens.shared.observability.ports import OperationalTelemetry
from opslens.transformation.epss.adapters.outbound.parquet import PyArrowSilverEpssRecordWriter
from opslens.transformation.epss.adapters.outbound.s3_history_completion import (
    S3HistoricalEpssCompletionPutClient,
    S3HistoricalEpssCompletionRepository,
)
from opslens.transformation.epss.adapters.outbound.s3_history_completion_replay import (
    S3HistoricalEpssCompletionReplayClient,
    S3HistoricalEpssCompletionReplayVerifier,
)
from opslens.transformation.epss.adapters.outbound.s3_history_exact_object import (
    S3VersionedGetClient,
    S3VersionedHistoricalEpssBronzeObjectReader,
)
from opslens.transformation.epss.adapters.outbound.s3_history_silver import (
    S3HistoricalEpssSilverPutClient,
    S3HistoricalEpssSilverRepository,
)
from opslens.transformation.epss.adapters.outbound.s3_history_silver_replay import (
    S3HistoricalEpssSilverReplayClient,
    S3HistoricalEpssSilverReplayVerifier,
)
from opslens.transformation.epss.application.key_factory import EpssSilverKeyFactory
from opslens.transformation.epss.history.completion import (
    HistoricalEpssCompletionManifestFactoryV1,
    PersistHistoricalEpssCompletion,
)
from opslens.transformation.epss.history.invocation import (
    ExecuteHistoricalEpssInvocationV1,
    HistoricalEpssInvocationParserV1,
)
from opslens.transformation.epss.history.persistence import PersistHistoricalEpssSilver
from opslens.transformation.epss.history.preparation import (
    HistoricalEpssSilverRecordTransformer,
    PrepareHistoricalEpssSilver,
)
from opslens.transformation.epss.history.reader import ReadHistoricalEpssBronzeEvidence
from opslens.transformation.epss.history.runtime import (
    HistoricalEpssForwardListClient,
    HistoricalEpssRuntimeSettings,
    S3HistoricalEpssForwardBoundaryReader,
)


class _Boto3S3ClientFactory(Protocol):
    """Narrow the runtime SDK factory to the only service required here."""

    def client(self, service_name: Literal["s3"]) -> S3Client:
        """Create a typed S3 client."""
        ...


def build_runtime_executor(
    telemetry: OperationalTelemetry,
) -> ExecuteHistoricalEpssInvocationV1:
    """Compose exact-version history transformation from environment and AWS SDK."""
    settings = HistoricalEpssRuntimeSettings.from_environment()
    sdk = cast(_Boto3S3ClientFactory, boto3)
    raw_s3_client = sdk.client("s3")

    boundary_reader = S3HistoricalEpssForwardBoundaryReader(
        client=cast(HistoricalEpssForwardListClient, raw_s3_client),
        bucket_name=settings.data_bucket,
    )
    first_forward_snapshot_date = boundary_reader.discover()

    exact_object_reader = S3VersionedHistoricalEpssBronzeObjectReader(
        client=cast(S3VersionedGetClient, raw_s3_client),
        bucket_name=settings.data_bucket,
    )
    bronze_reader = ReadHistoricalEpssBronzeEvidence(
        object_reader=exact_object_reader,
    )

    silver_key_factory = EpssSilverKeyFactory(prefix="silver/epss")
    silver_preparer = PrepareHistoricalEpssSilver(
        parser=HistoricalEpssSnapshotParser(),
        transformer=HistoricalEpssSilverRecordTransformer(),
        record_writer=PyArrowSilverEpssRecordWriter(),
        key_factory=silver_key_factory,
    )
    silver_persistence = PersistHistoricalEpssSilver(
        repository=S3HistoricalEpssSilverRepository(
            client=cast(S3HistoricalEpssSilverPutClient, raw_s3_client),
            bucket_name=settings.data_bucket,
            telemetry=telemetry,
        ),
        replay_verifier=S3HistoricalEpssSilverReplayVerifier(
            client=cast(S3HistoricalEpssSilverReplayClient, raw_s3_client),
            bucket_name=settings.data_bucket,
            telemetry=telemetry,
        ),
    )

    completion_factory = HistoricalEpssCompletionManifestFactoryV1(
        silver_key_factory=silver_key_factory,
    )
    completion_persistence = PersistHistoricalEpssCompletion(
        repository=S3HistoricalEpssCompletionRepository(
            client=cast(S3HistoricalEpssCompletionPutClient, raw_s3_client),
            bucket_name=settings.data_bucket,
            telemetry=telemetry,
        ),
        replay_verifier=S3HistoricalEpssCompletionReplayVerifier(
            client=cast(S3HistoricalEpssCompletionReplayClient, raw_s3_client),
            bucket_name=settings.data_bucket,
            telemetry=telemetry,
        ),
    )

    return ExecuteHistoricalEpssInvocationV1(
        parser=HistoricalEpssInvocationParserV1(
            approved_archive_commit=settings.approved_archive_commit,
        ),
        bronze_reader=bronze_reader,
        silver_preparer=silver_preparer,
        silver_persistence=silver_persistence,
        completion_factory=completion_factory,
        completion_persistence=completion_persistence,
        first_forward_snapshot_date=first_forward_snapshot_date,
    )
