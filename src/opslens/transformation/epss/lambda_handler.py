"""AWS Lambda entrypoint for EPSS Bronze-to-Silver transformation."""

from collections.abc import Mapping
from typing import Protocol, TypedDict

from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

from opslens.shared.observability.ports import OperationalTelemetry
from opslens.shared.observability.powertools import PowertoolsTelemetry
from opslens.transformation.epss.adapters.inbound.s3_event import (
    S3ObjectCreatedEventParser,
)
from opslens.transformation.epss.application.models import (
    EpssSilverTransformationResult,
    SilverRepositoryWriteStatus,
)
from opslens.transformation.epss.composition import (
    build_runtime_dependencies,
)

SERVICE_NAME = "opslens-epss-silver"
METRICS_NAMESPACE = "OpsLens"

logger = Logger(service=SERVICE_NAME)
metrics = Metrics(
    namespace=METRICS_NAMESPACE,
    service=SERVICE_NAME,
)
tracer = Tracer(service=SERVICE_NAME)

telemetry = PowertoolsTelemetry(
    logger=logger,
    metrics=metrics,
    tracer=tracer,
)


class EpssSilverTransformationUseCase(Protocol):
    """Define the transformation capability required by the Lambda boundary."""

    def transform(
        self,
        bronze_key: str,
    ) -> EpssSilverTransformationResult:
        """Transform one Bronze object into its Silver representation."""
        ...


class TransformationRecordResponse(TypedDict):
    """Represent one serialized Silver transformation outcome."""

    bronze_key: str
    silver_key: str
    snapshot_date: str
    row_count: int
    size_bytes: int
    schema_version: int
    source_sha256: str
    status: str


class TransformationInvocationResponse(TypedDict):
    """Represent the complete Lambda transformation outcome."""

    processed_records: int
    created_records: int
    already_exists_records: int
    records: list[TransformationRecordResponse]


@logger.inject_lambda_context(
    clear_state=True,
    log_event=False,
)
@tracer.capture_lambda_handler
@metrics.log_metrics
def lambda_handler(
    event: Mapping[str, object],
    context: LambdaContext,
) -> TransformationInvocationResponse:
    """Handle an Amazon S3 ObjectCreated notification.

    Args:
        event: Raw S3 notification delivered to Lambda.
        context: AWS Lambda runtime context.

    Returns:
        Serialized results for all successfully processed S3 records.

    Raises:
        Exception: Propagates parsing or transformation failures so the
            invocation is recorded as failed and asynchronous retry behavior
            remains available.
    """
    runtime = build_runtime_dependencies(
        telemetry=telemetry,
    )

    return execute_transformation_event(
        event=event,
        event_parser=runtime.event_parser,
        use_case=runtime.service,
        telemetry=telemetry,
        request_id=context.aws_request_id,
    )


def execute_transformation_event(
    *,
    event: Mapping[str, object],
    event_parser: S3ObjectCreatedEventParser,
    use_case: EpssSilverTransformationUseCase,
    telemetry: OperationalTelemetry,
    request_id: str,
) -> TransformationInvocationResponse:
    """Execute one complete S3-triggered Silver transformation invocation.

    Args:
        event: Raw Lambda invocation event.
        event_parser: Validated S3 ObjectCreated event parser.
        use_case: Bronze-to-Silver application service.
        telemetry: Operational observability implementation.
        request_id: AWS Lambda invocation identifier.

    Returns:
        Serialized results for every successfully transformed record, or an
        empty successful response for a validated Amazon S3 test event.

    Raises:
        Exception: Propagates any event or transformation failure.
    """
    current_record_index: int | None = None
    current_bronze_key: str | None = None

    try:
        test_event = event_parser.parse_test_event(event)

        if test_event is not None:
            telemetry.metric(
                name="EpssSilverS3TestEvent",
                value=1.0,
                unit="Count",
            )

            telemetry.info(
                "Accepted S3 test event",
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
            name="EpssSilverTransformationInvocation",
            value=1.0,
            unit="Count",
        )

        telemetry.info(
            "Starting EPSS Silver transformation invocation",
            fields={
                "request_id": request_id,
            },
        )

        records = event_parser.parse(event)

        telemetry.metric(
            name="EpssSilverNotificationRecords",
            value=float(len(records)),
            unit="Count",
        )

        serialized_results: list[TransformationRecordResponse] = []
        created_records = 0
        already_exists_records = 0

        for record_index, record in enumerate(records):
            current_record_index = record_index
            current_bronze_key = record.key

            telemetry.info(
                "Starting EPSS Silver record transformation",
                fields={
                    "request_id": request_id,
                    "record_index": record_index,
                    "bronze_key": record.key,
                    "sequencer": record.sequencer,
                    "event_name": record.event_name,
                },
            )

            result = use_case.transform(record.key)

            if result.write_status is SilverRepositoryWriteStatus.CREATED:
                created_records += 1
            else:
                already_exists_records += 1

            serialized_results.append(
                _serialize_result(result),
            )

            telemetry.info(
                "EPSS Silver record transformation completed",
                fields={
                    "request_id": request_id,
                    "record_index": record_index,
                    "bronze_key": result.bronze_key,
                    "silver_key": result.silver_key,
                    "snapshot_date": result.snapshot_date.isoformat(),
                    "row_count": result.row_count,
                    "size_bytes": result.size_bytes,
                    "schema_version": result.schema_version,
                    "source_sha256": result.source_sha256,
                    "status": result.write_status.value,
                },
            )

    except Exception:
        telemetry.metric(
            name="EpssSilverTransformationFailure",
            value=1.0,
            unit="Count",
        )

        telemetry.exception(
            "EPSS Silver transformation invocation failed",
            fields={
                "request_id": request_id,
                "record_index": current_record_index,
                "bronze_key": current_bronze_key,
            },
        )

        raise

    telemetry.metric(
        name="EpssSilverTransformationSuccess",
        value=1.0,
        unit="Count",
    )
    telemetry.metric(
        name="EpssSilverTransformationCreatedRecords",
        value=float(created_records),
        unit="Count",
    )
    telemetry.metric(
        name="EpssSilverTransformationAlreadyExistsRecords",
        value=float(already_exists_records),
        unit="Count",
    )

    telemetry.info(
        "EPSS Silver transformation invocation completed",
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
    result: EpssSilverTransformationResult,
) -> TransformationRecordResponse:
    """Serialize one deterministic Silver transformation result."""
    return {
        "bronze_key": result.bronze_key,
        "silver_key": result.silver_key,
        "snapshot_date": result.snapshot_date.isoformat(),
        "row_count": result.row_count,
        "size_bytes": result.size_bytes,
        "schema_version": result.schema_version,
        "source_sha256": result.source_sha256,
        "status": result.write_status.value,
    }
