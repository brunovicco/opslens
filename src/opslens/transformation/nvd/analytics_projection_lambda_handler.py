"""AWS Lambda entrypoint for permanent NVD analytics projection."""

from collections.abc import Mapping
from typing import Protocol, TypedDict

from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

from opslens.shared.observability.ports import OperationalTelemetry
from opslens.shared.observability.powertools import PowertoolsTelemetry
from opslens.transformation.nvd.adapters.inbound.analytics_projection_invocation import (
    NvdAnalyticsBootstrapSeedInvocationV1,
    NvdAnalyticsIncrementalWatermarkEventV1,
    NvdAnalyticsProjectionInvocationParserV1,
    NvdAnalyticsS3TestEventV1,
)
from opslens.transformation.nvd.analytics_projection_composition import (
    NvdAnalyticsProjectionRuntimeDependencies,
    build_analytics_projection_runtime_dependencies,
)
from opslens.transformation.nvd.analytics_projection_config import (
    NvdAnalyticsProjectionRuntimeSettingsV1,
)
from opslens.transformation.nvd.application.analytics_projection_service import (
    NvdAnalyticsProjectionResultV1,
)

SERVICE_NAME = "opslens-nvd-analytics-projection"
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

_runtime_dependencies: NvdAnalyticsProjectionRuntimeDependencies | None = None
_invocation_parser: NvdAnalyticsProjectionInvocationParserV1 | None = None


class NvdAnalyticsProjectionProcessingUseCase(Protocol):
    """Define the application capabilities required by the Lambda boundary."""

    def project_incremental(
        self,
        *,
        watermark_key: str,
        watermark_version_id: str,
    ) -> NvdAnalyticsProjectionResultV1:
        """Project one exact committed incremental watermark."""
        ...

    def project_bootstrap(
        self,
        *,
        silver_complete_key: str,
        silver_complete_version_id: str,
    ) -> NvdAnalyticsProjectionResultV1:
        """Project one explicit exact Bootstrap seed."""
        ...


class NvdAnalyticsProjectionInvocationResponse(TypedDict):
    """Represent one JSON-serializable verified analytics projection result."""

    request_id: str
    status: str
    source_kind: str
    source_batch_id: str
    authority_state: str
    projection_date: str
    row_count: int
    destination_key: str
    destination_version_id: str
    destination_sha256: str


class NvdAnalyticsProjectionS3TestResponse(TypedDict):
    """Represent successful handling of an Amazon S3 test notification."""

    status: str
    processed_records: int
    bucket: str
    s3_request_id: str


type NvdAnalyticsProjectionLambdaResponse = (
    NvdAnalyticsProjectionInvocationResponse
    | NvdAnalyticsProjectionS3TestResponse
)


@logger.inject_lambda_context(
    clear_state=True,
    log_event=False,
)
@tracer.capture_lambda_handler
@metrics.log_metrics
def lambda_handler(
    event: Mapping[str, object],
    context: LambdaContext,
) -> NvdAnalyticsProjectionLambdaResponse:
    """Handle one strict incremental, Bootstrap, or S3 test invocation."""
    request_id = context.aws_request_id

    try:
        parsed = _get_invocation_parser().parse(event)
    except Exception:
        telemetry.metric(
            name="NvdAnalyticsProjectionInvalidInvocation",
            value=1.0,
            unit="Count",
        )
        telemetry.exception(
            "NVD analytics projection invocation rejected",
            fields={
                "request_id": request_id,
            },
        )
        raise

    if isinstance(
        parsed,
        NvdAnalyticsS3TestEventV1,
    ):
        telemetry.metric(
            name="NvdAnalyticsProjectionS3TestEvent",
            value=1.0,
            unit="Count",
        )
        telemetry.info(
            "Accepted NVD analytics projection S3 test event",
            fields={
                "request_id": request_id,
                "s3_request_id": parsed.request_id,
                "bucket": parsed.bucket,
            },
        )
        return {
            "status": "s3_test_event",
            "processed_records": 0,
            "bucket": parsed.bucket,
            "s3_request_id": parsed.request_id,
        }

    try:
        runtime = _get_runtime_dependencies()
    except Exception:
        telemetry.metric(
            name="NvdAnalyticsProjectionRuntimeInitializationFailure",
            value=1.0,
            unit="Count",
        )
        telemetry.exception(
            "NVD analytics projection runtime dependency initialization failed",
            fields={
                "request_id": request_id,
                **_trigger_fields(parsed),
            },
        )
        raise

    return execute_projection_request(
        trigger=parsed,
        processor=runtime.service,
        telemetry=telemetry,
        request_id=request_id,
    )


def execute_projection_request(
    *,
    trigger: (
        NvdAnalyticsIncrementalWatermarkEventV1
        | NvdAnalyticsBootstrapSeedInvocationV1
    ),
    processor: NvdAnalyticsProjectionProcessingUseCase,
    telemetry: OperationalTelemetry,
    request_id: str,
) -> NvdAnalyticsProjectionInvocationResponse:
    """Execute one fully validated projection request and emit bounded telemetry."""
    trigger_fields = _trigger_fields(trigger)
    telemetry.metric(
        name="NvdAnalyticsProjectionInvocation",
        value=1.0,
        unit="Count",
    )
    telemetry.info(
        "Starting permanent NVD analytics projection",
        fields={
            "request_id": request_id,
            **trigger_fields,
        },
    )

    try:
        if isinstance(
            trigger,
            NvdAnalyticsIncrementalWatermarkEventV1,
        ):
            result = processor.project_incremental(
                watermark_key=trigger.watermark_key,
                watermark_version_id=trigger.watermark_version_id,
            )
        else:
            result = processor.project_bootstrap(
                silver_complete_key=trigger.silver_complete_key,
                silver_complete_version_id=trigger.silver_complete_version_id,
            )
    except Exception:
        telemetry.metric(
            name="NvdAnalyticsProjectionFailure",
            value=1.0,
            unit="Count",
        )
        telemetry.exception(
            "Permanent NVD analytics projection failed",
            fields={
                "request_id": request_id,
                **trigger_fields,
            },
        )
        raise

    telemetry.metric(
        name="NvdAnalyticsProjectionSuccess",
        value=1.0,
        unit="Count",
    )
    telemetry.metric(
        name=(
            "NvdAnalyticsProjected"
            if result.status == "projected"
            else "NvdAnalyticsAlreadyProjected"
        ),
        value=1.0,
        unit="Count",
    )
    telemetry.info(
        "Permanent NVD analytics projection completed",
        fields={
            "request_id": request_id,
            "status": result.status,
            "source_kind": result.request.source_kind.value,
            "source_batch_id": result.request.source_batch_id,
            "authority_state": result.request.authority_state,
            "projection_date": result.destination.projection_date,
            "row_count": result.request.row_count,
            "destination_key": result.destination.object_key,
            "destination_version_id": result.projected_object.version_id,
            "destination_sha256": result.projected_object.sha256,
        },
    )

    return {
        "request_id": request_id,
        "status": result.status,
        "source_kind": result.request.source_kind.value,
        "source_batch_id": result.request.source_batch_id,
        "authority_state": result.request.authority_state,
        "projection_date": result.destination.projection_date,
        "row_count": result.request.row_count,
        "destination_key": result.destination.object_key,
        "destination_version_id": result.projected_object.version_id,
        "destination_sha256": result.projected_object.sha256,
    }


def _trigger_fields(
    trigger: (
        NvdAnalyticsIncrementalWatermarkEventV1
        | NvdAnalyticsBootstrapSeedInvocationV1
    ),
) -> dict[str, object]:
    """Return bounded authority coordinates for logs without reading payloads."""
    if isinstance(
        trigger,
        NvdAnalyticsIncrementalWatermarkEventV1,
    ):
        return {
            "trigger_kind": "incremental_watermark",
            "bucket": trigger.bucket,
            "watermark_key": trigger.watermark_key,
            "watermark_version_id": trigger.watermark_version_id,
            "event_object_size_bytes": trigger.object_size_bytes,
        }

    return {
        "trigger_kind": "bootstrap_seed",
        "silver_complete_key": trigger.silver_complete_key,
        "silver_complete_version_id": trigger.silver_complete_version_id,
    }


def _get_invocation_parser() -> NvdAnalyticsProjectionInvocationParserV1:
    """Build the configured strict invocation parser once per Lambda environment."""
    global _invocation_parser

    if _invocation_parser is None:
        settings = NvdAnalyticsProjectionRuntimeSettingsV1.from_environment()
        _invocation_parser = NvdAnalyticsProjectionInvocationParserV1(
            expected_bucket=settings.data_bucket,
        )

    return _invocation_parser


def _get_runtime_dependencies() -> NvdAnalyticsProjectionRuntimeDependencies:
    """Build the runtime graph once per reusable Lambda environment."""
    global _runtime_dependencies

    if _runtime_dependencies is None:
        _runtime_dependencies = build_analytics_projection_runtime_dependencies(
            telemetry=telemetry,
        )

    return _runtime_dependencies
