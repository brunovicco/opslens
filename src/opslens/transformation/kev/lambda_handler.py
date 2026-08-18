"""AWS Lambda entrypoint for CISA KEV Bronze-to-Silver transformation."""

from collections.abc import Mapping
from typing import Protocol, TypedDict

from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

from opslens.shared.observability.ports import OperationalTelemetry
from opslens.shared.observability.powertools import PowertoolsTelemetry
from opslens.transformation.kev.adapters.inbound.s3_event import (
    KevBronzeObjectReference,
    KevS3EventParser,
)
from opslens.transformation.kev.application.runtime_models import (
    KevSilverRepositoryWriteStatus,
    KevSilverTransformationResult,
)
from opslens.transformation.kev.composition import (
    build_runtime_dependencies,
)

SERVICE_NAME = "opslens-kev-silver"
METRICS_NAMESPACE = "OpsLens"

logger = Logger(
    service=SERVICE_NAME,
)

metrics = Metrics(
    namespace=METRICS_NAMESPACE,
    service=SERVICE_NAME,
)

tracer = Tracer(
    service=SERVICE_NAME,
)

telemetry = PowertoolsTelemetry(
    logger=logger,
    metrics=metrics,
    tracer=tracer,
)


class KevSilverObjectProcessingUseCase(Protocol):
    """Define the per-object capability required by the Lambda boundary."""

    def process(
        self,
        reference: KevBronzeObjectReference,
    ) -> KevSilverTransformationResult:
        """Process one exact versioned KEV Bronze object reference."""
        ...


class KevSilverRecordResponse(TypedDict):
    """Represent one serialized KEV Silver transformation outcome."""

    bronze_key: str
    bronze_version_id: str
    silver_key: str
    snapshot_date: str
    row_count: int
    size_bytes: int
    schema_version: int
    source_sha256: str
    status: str


class KevSilverInvocationResponse(TypedDict):
    """Represent the complete KEV Silver Lambda invocation outcome."""

    processed_records: int
    created_records: int
    already_exists_records: int
    records: list[KevSilverRecordResponse]


@logger.inject_lambda_context(
    clear_state=True,
    log_event=False,
)
@tracer.capture_lambda_handler
@metrics.log_metrics
def lambda_handler(
    event: Mapping[str, object],
    context: LambdaContext,
) -> KevSilverInvocationResponse:
    """Handle an Amazon S3 notification for CISA KEV Bronze.

    Args:
        event: Raw S3 notification delivered to Lambda.
        context: AWS Lambda runtime context.

    Returns:
        Serialized outcomes for all successfully processed S3 records.

    Raises:
        Exception: Propagates event parsing or object processing failures so
            asynchronous Lambda retry and failure-destination semantics remain
            available.
    """
    runtime = build_runtime_dependencies(
        telemetry=telemetry,
    )

    return execute_transformation_event(
        event=event,
        event_parser=runtime.event_parser,
        processor=runtime.processor,
        telemetry=telemetry,
        request_id=context.aws_request_id,
    )


def execute_transformation_event(
    *,
    event: Mapping[str, object],
    event_parser: KevS3EventParser,
    processor: KevSilverObjectProcessingUseCase,
    telemetry: OperationalTelemetry,
    request_id: str,
) -> KevSilverInvocationResponse:
    """Execute one complete S3-triggered KEV Silver invocation.

    Args:
        event: Raw Lambda invocation event.
        event_parser: Strict KEV S3 notification parser.
        processor: Exact-version KEV object processor.
        telemetry: Operational observability implementation.
        request_id: AWS Lambda invocation identifier.

    Returns:
        Serialized results for every successfully processed object, or an
        empty successful response for a validated Amazon S3 test event.

    Raises:
        Exception: Propagates any event or processing failure.
    """
    current_record_index: int | None = None
    current_bronze_key: str | None = None
    current_version_id: str | None = None

    try:
        test_event = event_parser.parse_test_event(
            event,
        )

        if test_event is not None:
            telemetry.metric(
                name="KevSilverS3TestEvent",
                value=1.0,
                unit="Count",
            )

            telemetry.info(
                "Accepted CISA KEV Silver S3 test event",
                fields={
                    "request_id": request_id,
                    "s3_request_id": test_event.request_id,
                    "bucket": test_event.bucket,
                },
            )

            return {
                "processed_records": 0,
                "created_records": 0,
                "already_exists_records": 0,
                "records": [],
            }

        telemetry.metric(
            name="KevSilverTransformationInvocation",
            value=1.0,
            unit="Count",
        )

        telemetry.info(
            "Starting CISA KEV Silver transformation invocation",
            fields={
                "request_id": request_id,
            },
        )

        records = event_parser.parse(
            event,
        )

        telemetry.metric(
            name="KevSilverNotificationRecords",
            value=float(len(records)),
            unit="Count",
        )

        serialized_results: list[KevSilverRecordResponse] = []

        created_records = 0
        already_exists_records = 0

        for record_index, record in enumerate(records):
            current_record_index = record_index
            current_bronze_key = record.key
            current_version_id = record.version_id

            telemetry.info(
                "Starting CISA KEV Silver record transformation",
                fields={
                    "request_id": request_id,
                    "record_index": record_index,
                    "bronze_key": record.key,
                    "bronze_version_id": record.version_id,
                    "etag": record.etag,
                    "size_bytes": record.size_bytes,
                    "sequencer": record.sequencer,
                    "event_name": record.event_name,
                },
            )

            result = processor.process(
                record,
            )

            if result.write_status is KevSilverRepositoryWriteStatus.CREATED:
                created_records += 1
            else:
                already_exists_records += 1

            serialized_results.append(
                _serialize_result(
                    result,
                )
            )

            telemetry.info(
                "CISA KEV Silver record transformation completed",
                fields={
                    "request_id": request_id,
                    "record_index": record_index,
                    "bronze_key": result.bronze_key,
                    "bronze_version_id": result.bronze_version_id,
                    "silver_key": result.silver_key,
                    "snapshot_date": result.snapshot_date,
                    "row_count": result.row_count,
                    "size_bytes": result.size_bytes,
                    "schema_version": result.schema_version,
                    "source_sha256": result.source_sha256,
                    "status": result.write_status.value,
                },
            )

    except Exception:
        telemetry.metric(
            name="KevSilverTransformationFailure",
            value=1.0,
            unit="Count",
        )

        telemetry.exception(
            "CISA KEV Silver transformation invocation failed",
            fields={
                "request_id": request_id,
                "record_index": current_record_index,
                "bronze_key": current_bronze_key,
                "bronze_version_id": current_version_id,
            },
        )

        raise

    telemetry.metric(
        name="KevSilverTransformationSuccess",
        value=1.0,
        unit="Count",
    )

    telemetry.metric(
        name="KevSilverTransformationCreatedRecords",
        value=float(created_records),
        unit="Count",
    )

    telemetry.metric(
        name="KevSilverTransformationAlreadyExistsRecords",
        value=float(already_exists_records),
        unit="Count",
    )

    telemetry.info(
        "CISA KEV Silver transformation invocation completed",
        fields={
            "request_id": request_id,
            "processed_records": len(serialized_results),
            "created_records": created_records,
            "already_exists_records": already_exists_records,
        },
    )

    return {
        "processed_records": len(serialized_results),
        "created_records": created_records,
        "already_exists_records": already_exists_records,
        "records": serialized_results,
    }


def _serialize_result(
    result: KevSilverTransformationResult,
) -> KevSilverRecordResponse:
    """Serialize one deterministic KEV Silver transformation result."""
    return {
        "bronze_key": result.bronze_key,
        "bronze_version_id": result.bronze_version_id,
        "silver_key": result.silver_key,
        "snapshot_date": result.snapshot_date,
        "row_count": result.row_count,
        "size_bytes": result.size_bytes,
        "schema_version": result.schema_version,
        "source_sha256": result.source_sha256,
        "status": result.write_status.value,
    }
