"""AWS Lambda entrypoint for GHSA Bronze-to-Silver transformation."""

from collections.abc import Mapping
from typing import Protocol, TypedDict

from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

from opslens.shared.observability.ports import OperationalTelemetry
from opslens.shared.observability.powertools import PowertoolsTelemetry
from opslens.transformation.ghsa.adapters.inbound.invocation import (
    GhsaSilverInvocationParserV1,
)
from opslens.transformation.ghsa.application.runtime_models import (
    GhsaSilverRuntimeRequestV1,
    GhsaSilverRuntimeResultV1,
)
from opslens.transformation.ghsa.composition import (
    GhsaSilverRuntimeDependencies,
    build_runtime_dependencies,
)

SERVICE_NAME = "opslens-ghsa-silver"
METRICS_NAMESPACE = "OpsLens"

logger = Logger(service=SERVICE_NAME)
metrics = Metrics(namespace=METRICS_NAMESPACE, service=SERVICE_NAME)
tracer = Tracer(service=SERVICE_NAME)
telemetry = PowertoolsTelemetry(
    logger=logger,
    metrics=metrics,
    tracer=tracer,
)
invocation_parser = GhsaSilverInvocationParserV1()

_runtime_dependencies: GhsaSilverRuntimeDependencies | None = None


class GhsaSilverProcessingUseCase(Protocol):
    """Define the GHSA Silver processor capability required by Lambda."""

    def process(
        self,
        request: GhsaSilverRuntimeRequestV1,
    ) -> GhsaSilverRuntimeResultV1:
        """Process one exact GHSA Bronze manifest coordinate."""
        ...


class GhsaSilverInvocationResponse(TypedDict):
    """Represent one bounded JSON-serializable successful Lambda result."""

    request_id: str
    status: str
    sync_id: str
    attempt_id: str
    bronze_manifest_key: str
    bronze_manifest_version_id: str
    logical_record_set_sha256: str
    silver_complete_key: str
    silver_complete_version_id: str
    silver_complete_sha256: str
    row_count: int
    content_object_count: int


@logger.inject_lambda_context(clear_state=True, log_event=False)
@tracer.capture_lambda_handler
@metrics.log_metrics
def lambda_handler(
    event: Mapping[str, object],
    context: LambdaContext,
) -> GhsaSilverInvocationResponse:
    """Handle one strict explicit GHSA Silver transformation invocation."""
    request_id = context.aws_request_id

    try:
        request = invocation_parser.parse(event)
    except Exception:
        telemetry.metric(
            name="GhsaSilverInvalidInvocation",
            value=1.0,
            unit="Count",
        )
        telemetry.exception(
            "GHSA Silver invocation rejected",
            fields={"request_id": request_id},
        )
        raise

    try:
        runtime = _get_runtime_dependencies()
    except Exception:
        telemetry.metric(
            name="GhsaSilverRuntimeInitializationFailure",
            value=1.0,
            unit="Count",
        )
        telemetry.exception(
            "GHSA Silver runtime dependency initialization failed",
            fields={
                "request_id": request_id,
                "bronze_manifest_key": request.manifest_key,
                "bronze_manifest_version_id": request.manifest_version_id,
            },
        )
        raise

    return execute_transformation_request(
        request=request,
        processor=runtime.processor,
        telemetry=telemetry,
        request_id=request_id,
    )


def execute_transformation_request(
    *,
    request: GhsaSilverRuntimeRequestV1,
    processor: GhsaSilverProcessingUseCase,
    telemetry: OperationalTelemetry,
    request_id: str,
) -> GhsaSilverInvocationResponse:
    """Execute one fully validated GHSA Silver runtime request."""
    telemetry.metric(
        name="GhsaSilverTransformationInvocation",
        value=1.0,
        unit="Count",
    )
    telemetry.info(
        "Starting GHSA Silver transformation invocation",
        fields={
            "request_id": request_id,
            "bronze_manifest_key": request.manifest_key,
            "bronze_manifest_version_id": request.manifest_version_id,
        },
    )

    try:
        result = processor.process(request)
    except Exception:
        telemetry.metric(
            name="GhsaSilverTransformationFailure",
            value=1.0,
            unit="Count",
        )
        telemetry.exception(
            "GHSA Silver transformation invocation failed",
            fields={
                "request_id": request_id,
                "bronze_manifest_key": request.manifest_key,
                "bronze_manifest_version_id": request.manifest_version_id,
            },
        )
        raise

    telemetry.metric(
        name="GhsaSilverTransformationSuccess",
        value=1.0,
        unit="Count",
    )
    telemetry.metric(
        name="GhsaSilverTransformationRows",
        value=float(result.row_count),
        unit="Count",
    )
    telemetry.info(
        "GHSA Silver transformation invocation completed",
        fields={
            "request_id": request_id,
            "sync_id": result.sync_id,
            "attempt_id": result.attempt_id,
            "bronze_manifest_key": result.bronze_manifest_key,
            "bronze_manifest_version_id": result.bronze_manifest_version_id,
            "silver_complete_key": result.silver_complete_key,
            "silver_complete_version_id": result.silver_complete_version_id,
            "row_count": result.row_count,
        },
    )

    return _serialize_result(result=result, request_id=request_id)


def _get_runtime_dependencies() -> GhsaSilverRuntimeDependencies:
    """Build the runtime graph once per reusable Lambda environment."""
    global _runtime_dependencies

    if _runtime_dependencies is None:
        _runtime_dependencies = build_runtime_dependencies(telemetry=telemetry)

    return _runtime_dependencies


def _serialize_result(
    *,
    result: GhsaSilverRuntimeResultV1,
    request_id: str,
) -> GhsaSilverInvocationResponse:
    """Serialize bounded exact Silver completion evidence."""
    return {
        "request_id": request_id,
        "status": "complete",
        "sync_id": result.sync_id,
        "attempt_id": result.attempt_id,
        "bronze_manifest_key": result.bronze_manifest_key,
        "bronze_manifest_version_id": result.bronze_manifest_version_id,
        "logical_record_set_sha256": result.logical_record_set_sha256,
        "silver_complete_key": result.silver_complete_key,
        "silver_complete_version_id": result.silver_complete_version_id,
        "silver_complete_sha256": result.silver_complete_sha256,
        "row_count": result.row_count,
        "content_object_count": result.content_object_count,
    }
