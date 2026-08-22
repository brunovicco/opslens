"""AWS Lambda entrypoint for NVD Bronze-to-Silver transformation."""

import os
from collections.abc import Mapping
from typing import Protocol, TypedDict

from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

from opslens.shared.observability.ports import OperationalTelemetry
from opslens.shared.observability.powertools import PowertoolsTelemetry
from opslens.transformation.nvd.adapters.inbound.invocation import (
    NvdSilverInvocationParserV1,
)
from opslens.transformation.nvd.adapters.inbound.s3_event import (
    NvdS3TestEvent,
    NvdSilverS3EventParserV1,
)
from opslens.transformation.nvd.application.runtime_models import (
    NvdSilverRuntimeRequestV1,
    NvdSilverRuntimeResultV1,
)
from opslens.transformation.nvd.composition import (
    NvdSilverRuntimeDependencies,
    build_runtime_dependencies,
)

SERVICE_NAME = "opslens-nvd-silver"
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

invocation_parser = NvdSilverInvocationParserV1()

_runtime_dependencies: NvdSilverRuntimeDependencies | None = None
_s3_event_parser: NvdSilverS3EventParserV1 | None = None


class NvdSilverProcessingUseCase(Protocol):
    """Define the NVD Silver processor capability required by Lambda."""

    def process(
        self,
        request: NvdSilverRuntimeRequestV1,
    ) -> NvdSilverRuntimeResultV1:
        """Process one exact NVD Bronze manifest coordinate."""
        ...


class NvdSilverInvocationResponse(TypedDict):
    """Represent one JSON-serializable successful Lambda result."""

    request_id: str
    status: str
    source_kind: str
    source_batch_id: str

    bronze_manifest_key: str
    bronze_manifest_version_id: str
    bronze_manifest_sha256: str

    silver_parquet_key: str
    silver_parquet_version_id: str
    silver_parquet_sha256: str

    silver_complete_key: str
    silver_complete_version_id: str
    silver_complete_sha256: str

    row_count: int


class NvdSilverS3TestResponse(TypedDict):
    """Represent successful handling of an Amazon S3 test notification."""

    status: str
    processed_records: int
    bucket: str
    s3_request_id: str


type NvdSilverLambdaResponse = NvdSilverInvocationResponse | NvdSilverS3TestResponse


@logger.inject_lambda_context(
    clear_state=True,
    log_event=False,
)
@tracer.capture_lambda_handler
@metrics.log_metrics
def lambda_handler(
    event: Mapping[str, object],
    context: LambdaContext,
) -> NvdSilverLambdaResponse:
    """Handle an explicit or S3-triggered NVD Silver invocation."""
    request_id = context.aws_request_id

    s3_event_parser: NvdSilverS3EventParserV1 | None = None

    if _looks_like_s3_event(
        event,
    ):
        try:
            s3_event_parser = _get_s3_event_parser()
        except Exception:
            telemetry.metric(
                name="NvdSilverRuntimeInitializationFailure",
                value=1.0,
                unit="Count",
            )
            telemetry.exception(
                "NVD Silver S3 boundary initialization failed",
                fields={
                    "request_id": request_id,
                },
            )
            raise

    try:
        parsed = parse_lambda_event(
            event=event,
            s3_event_parser=s3_event_parser,
        )
    except Exception:
        telemetry.metric(
            name="NvdSilverInvalidInvocation",
            value=1.0,
            unit="Count",
        )
        telemetry.exception(
            "NVD Silver invocation rejected",
            fields={
                "request_id": request_id,
            },
        )
        raise

    if isinstance(
        parsed,
        NvdS3TestEvent,
    ):
        telemetry.metric(
            name="NvdSilverS3TestEvent",
            value=1.0,
            unit="Count",
        )

        telemetry.info(
            "Accepted NVD Silver S3 test event",
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

    request = parsed

    try:
        runtime = _get_runtime_dependencies()
    except Exception:
        telemetry.metric(
            name="NvdSilverRuntimeInitializationFailure",
            value=1.0,
            unit="Count",
        )
        telemetry.exception(
            "NVD Silver runtime dependency initialization failed",
            fields={
                "request_id": request_id,
                "source_kind": request.source_kind.value,
                "bronze_manifest_key": request.manifest_key,
                "bronze_manifest_version_id": (request.manifest_version_id),
            },
        )
        raise

    return execute_transformation_request(
        request=request,
        processor=runtime.processor,
        telemetry=telemetry,
        request_id=request_id,
    )


def parse_lambda_event(
    *,
    event: Mapping[str, object],
    s3_event_parser: NvdSilverS3EventParserV1 | None,
) -> NvdSilverRuntimeRequestV1 | NvdS3TestEvent:
    """Resolve explicit and S3 event shapes into one runtime boundary."""
    if not _looks_like_s3_event(
        event,
    ):
        return invocation_parser.parse(
            event,
        )

    if s3_event_parser is None:
        raise RuntimeError("NVD Silver S3 event parser is required for S3 events.")

    test_event = s3_event_parser.parse_test_event(
        event,
    )

    if test_event is not None:
        return test_event

    return s3_event_parser.parse(
        event,
    )


def execute_transformation_request(
    *,
    request: NvdSilverRuntimeRequestV1,
    processor: NvdSilverProcessingUseCase,
    telemetry: OperationalTelemetry,
    request_id: str,
) -> NvdSilverInvocationResponse:
    """Execute one fully validated runtime request through NVD Silver."""
    telemetry.metric(
        name="NvdSilverTransformationInvocation",
        value=1.0,
        unit="Count",
    )

    telemetry.info(
        "Starting NVD Silver transformation invocation",
        fields={
            "request_id": request_id,
            "source_kind": request.source_kind.value,
            "bronze_manifest_key": request.manifest_key,
            "bronze_manifest_version_id": (request.manifest_version_id),
        },
    )

    try:
        result = processor.process(
            request,
        )
    except Exception:
        telemetry.metric(
            name="NvdSilverTransformationFailure",
            value=1.0,
            unit="Count",
        )
        telemetry.exception(
            "NVD Silver transformation invocation failed",
            fields={
                "request_id": request_id,
                "source_kind": request.source_kind.value,
                "bronze_manifest_key": request.manifest_key,
                "bronze_manifest_version_id": (request.manifest_version_id),
            },
        )
        raise

    telemetry.metric(
        name="NvdSilverTransformationSuccess",
        value=1.0,
        unit="Count",
    )

    telemetry.metric(
        name="NvdSilverTransformationRows",
        value=float(result.row_count),
        unit="Count",
    )

    telemetry.info(
        "NVD Silver transformation invocation completed",
        fields={
            "request_id": request_id,
            "source_kind": result.source_kind.value,
            "source_batch_id": result.source_batch_id,
            "bronze_manifest_key": result.bronze_manifest_key,
            "bronze_manifest_version_id": (result.bronze_manifest_version_id),
            "silver_parquet_key": result.silver_parquet_key,
            "silver_parquet_version_id": (result.silver_parquet_version_id),
            "silver_complete_key": result.silver_complete_key,
            "silver_complete_version_id": (result.silver_complete_version_id),
            "row_count": result.row_count,
        },
    )

    return _serialize_result(
        result=result,
        request_id=request_id,
    )


def _looks_like_s3_event(
    event: Mapping[str, object],
) -> bool:
    """Identify an Amazon S3 notification envelope shape."""
    return "Records" in event or event.get("Event") == NvdSilverS3EventParserV1.EXPECTED_TEST_EVENT


def _get_s3_event_parser() -> NvdSilverS3EventParserV1:
    """Build the configured S3 event parser once per Lambda environment."""
    global _s3_event_parser

    if _s3_event_parser is None:
        bucket = os.getenv(
            "NVD_DATA_BUCKET",
            "",
        ).strip()

        if not bucket:
            raise RuntimeError("NVD_DATA_BUCKET is required for S3-triggered NVD Silver.")

        _s3_event_parser = NvdSilverS3EventParserV1(
            expected_bucket=bucket,
        )

    return _s3_event_parser


def _get_runtime_dependencies() -> NvdSilverRuntimeDependencies:
    """Build the runtime graph once per reusable Lambda environment."""
    global _runtime_dependencies

    if _runtime_dependencies is None:
        _runtime_dependencies = build_runtime_dependencies(
            telemetry=telemetry,
        )

    return _runtime_dependencies


def _serialize_result(
    *,
    result: NvdSilverRuntimeResultV1,
    request_id: str,
) -> NvdSilverInvocationResponse:
    """Serialize final exact Silver evidence for the Lambda boundary."""
    return {
        "request_id": request_id,
        "status": "complete",
        "source_kind": result.source_kind.value,
        "source_batch_id": result.source_batch_id,
        "bronze_manifest_key": result.bronze_manifest_key,
        "bronze_manifest_version_id": (result.bronze_manifest_version_id),
        "bronze_manifest_sha256": result.bronze_manifest_sha256,
        "silver_parquet_key": result.silver_parquet_key,
        "silver_parquet_version_id": (result.silver_parquet_version_id),
        "silver_parquet_sha256": result.silver_parquet_sha256,
        "silver_complete_key": result.silver_complete_key,
        "silver_complete_version_id": (result.silver_complete_version_id),
        "silver_complete_sha256": result.silver_complete_sha256,
        "row_count": result.row_count,
    }
