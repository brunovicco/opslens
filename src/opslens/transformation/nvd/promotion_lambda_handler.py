"""AWS Lambda entrypoint for authoritative NVD watermark promotion."""

import os
from collections.abc import Mapping
from typing import Protocol, TypedDict

from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

from opslens.shared.observability.ports import OperationalTelemetry
from opslens.shared.observability.powertools import PowertoolsTelemetry
from opslens.transformation.nvd.adapters.inbound.promotion_s3_event import (
    NvdPromotionS3EventParserV1,
    NvdPromotionS3ObjectCreatedV1,
    NvdPromotionS3TestEventV1,
)
from opslens.transformation.nvd.application.watermark_promotion_evidence_loader import (
    NvdSilverCompleteRefV1,
)
from opslens.transformation.nvd.application.watermark_promotion_service import (
    NvdAuthoritativeWatermarkPromotionResultV1,
)
from opslens.transformation.nvd.promotion_composition import (
    NvdPromotionRuntimeDependencies,
    build_promotion_runtime_dependencies,
)

SERVICE_NAME = "opslens-nvd-promotion"
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

_runtime_dependencies: NvdPromotionRuntimeDependencies | None = None
_s3_event_parser: NvdPromotionS3EventParserV1 | None = None


class NvdPromotionProcessingUseCase(Protocol):
    """Define the application capability required by the Lambda boundary."""

    def process(
        self,
        *,
        silver_complete: NvdSilverCompleteRefV1,
    ) -> NvdAuthoritativeWatermarkPromotionResultV1:
        """Process one exact Silver COMPLETE coordinate."""
        ...


class NvdPromotionInvocationResponse(TypedDict):
    """Represent one JSON-serializable promotion result."""

    request_id: str
    status: str
    update_id: str

    silver_complete_key: str
    silver_complete_version_id: str

    committed_through_at: str
    watermark_version_id: str
    watermark_etag: str
    watermark_sha256: str


class NvdPromotionS3TestResponse(TypedDict):
    """Represent successful handling of an Amazon S3 test notification."""

    status: str
    processed_records: int
    bucket: str
    s3_request_id: str


type NvdPromotionLambdaResponse = (
    NvdPromotionInvocationResponse | NvdPromotionS3TestResponse
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
) -> NvdPromotionLambdaResponse:
    """Handle one strict S3-triggered authoritative NVD promotion."""
    request_id = context.aws_request_id

    try:
        s3_event_parser = _get_s3_event_parser()
        parsed = parse_lambda_event(
            event=event,
            s3_event_parser=s3_event_parser,
        )
    except Exception:
        telemetry.metric(
            name="NvdPromotionInvalidInvocation",
            value=1.0,
            unit="Count",
        )
        telemetry.exception(
            "NVD promotion invocation rejected",
            fields={
                "request_id": request_id,
            },
        )
        raise

    if isinstance(
        parsed,
        NvdPromotionS3TestEventV1,
    ):
        telemetry.metric(
            name="NvdPromotionS3TestEvent",
            value=1.0,
            unit="Count",
        )
        telemetry.info(
            "Accepted NVD promotion S3 test event",
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
            name="NvdPromotionRuntimeInitializationFailure",
            value=1.0,
            unit="Count",
        )
        telemetry.exception(
            "NVD promotion runtime dependency initialization failed",
            fields={
                "request_id": request_id,
                "silver_complete_key": parsed.silver_complete.key,
                "silver_complete_version_id": (
                    parsed.silver_complete.version_id
                ),
            },
        )
        raise

    return execute_promotion_request(
        trigger=parsed,
        processor=runtime.runtime,
        telemetry=telemetry,
        request_id=request_id,
    )


def parse_lambda_event(
    *,
    event: Mapping[str, object],
    s3_event_parser: NvdPromotionS3EventParserV1,
) -> NvdPromotionS3ObjectCreatedV1 | NvdPromotionS3TestEventV1:
    """Resolve S3 test and ObjectCreated event shapes at the Lambda boundary."""
    test_event = s3_event_parser.parse_test_event(
        event,
    )

    if test_event is not None:
        return test_event

    return s3_event_parser.parse(
        event,
    )


def execute_promotion_request(
    *,
    trigger: NvdPromotionS3ObjectCreatedV1,
    processor: NvdPromotionProcessingUseCase,
    telemetry: OperationalTelemetry,
    request_id: str,
) -> NvdPromotionInvocationResponse:
    """Execute one fully validated S3-triggered promotion request."""
    telemetry.metric(
        name="NvdPromotionInvocation",
        value=1.0,
        unit="Count",
    )
    telemetry.info(
        "Starting authoritative NVD watermark promotion",
        fields={
            "request_id": request_id,
            "bucket": trigger.bucket,
            "silver_complete_key": trigger.silver_complete.key,
            "silver_complete_version_id": (
                trigger.silver_complete.version_id
            ),
            "event_object_size_bytes": trigger.object_size_bytes,
        },
    )

    try:
        result = processor.process(
            silver_complete=trigger.silver_complete,
        )
    except Exception:
        telemetry.metric(
            name="NvdPromotionFailure",
            value=1.0,
            unit="Count",
        )
        telemetry.exception(
            "Authoritative NVD watermark promotion failed",
            fields={
                "request_id": request_id,
                "silver_complete_key": trigger.silver_complete.key,
                "silver_complete_version_id": (
                    trigger.silver_complete.version_id
                ),
            },
        )
        raise

    telemetry.metric(
        name="NvdPromotionSuccess",
        value=1.0,
        unit="Count",
    )

    status_metric = (
        "NvdPromotionCommitted"
        if result.status == "committed"
        else "NvdPromotionAlreadyCommitted"
    )
    telemetry.metric(
        name=status_metric,
        value=1.0,
        unit="Count",
    )

    telemetry.info(
        "Authoritative NVD watermark promotion completed",
        fields={
            "request_id": request_id,
            "status": result.status,
            "update_id": result.update_id,
            "silver_complete_key": trigger.silver_complete.key,
            "silver_complete_version_id": (
                trigger.silver_complete.version_id
            ),
            "watermark_version_id": result.persisted.version_id,
            "watermark_etag": result.persisted.etag,
            "committed_through_at": (
                result.persisted.watermark.canonical_committed_through_at
            ),
        },
    )

    return {
        "request_id": request_id,
        "status": result.status,
        "update_id": result.update_id,
        "silver_complete_key": trigger.silver_complete.key,
        "silver_complete_version_id": (
            trigger.silver_complete.version_id
        ),
        "committed_through_at": (
            result.persisted.watermark.canonical_committed_through_at
        ),
        "watermark_version_id": result.persisted.version_id,
        "watermark_etag": result.persisted.etag,
        "watermark_sha256": result.persisted.sha256,
    }


def _get_s3_event_parser() -> NvdPromotionS3EventParserV1:
    """Build the configured S3 event parser once per Lambda environment."""
    global _s3_event_parser

    if _s3_event_parser is None:
        bucket = os.getenv(
            "NVD_DATA_BUCKET",
            "",
        ).strip()

        if not bucket:
            raise RuntimeError(
                "NVD_DATA_BUCKET is required for S3-triggered NVD promotion."
            )

        _s3_event_parser = NvdPromotionS3EventParserV1(
            expected_bucket=bucket,
        )

    return _s3_event_parser


def _get_runtime_dependencies() -> NvdPromotionRuntimeDependencies:
    """Build the runtime graph once per reusable Lambda environment."""
    global _runtime_dependencies

    if _runtime_dependencies is None:
        _runtime_dependencies = build_promotion_runtime_dependencies(
            telemetry=telemetry,
        )

    return _runtime_dependencies
