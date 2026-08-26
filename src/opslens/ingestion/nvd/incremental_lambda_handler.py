"""AWS Lambda entrypoint for authoritative NVD incremental ingestion."""

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Protocol, TypedDict

from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

from opslens.ingestion.nvd.adapters.inbound.incremental_invocation import (
    NvdIncrementalInvocationParserV1,
)
from opslens.ingestion.nvd.application.incremental_runtime_plan import (
    NvdIncrementalRuntimeRequestV1,
)
from opslens.ingestion.nvd.application.incremental_runtime_service import (
    NvdIncrementalRuntimeResultV1,
    RunNvdIncrementalRuntimeV1,
)
from opslens.ingestion.nvd.incremental_runtime_composition import (
    build_incremental_runtime_from_environment,
)
from opslens.shared.observability.ports import OperationalTelemetry
from opslens.shared.observability.powertools import PowertoolsTelemetry

SERVICE_NAME = "opslens-nvd-incremental"
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

invocation_parser = NvdIncrementalInvocationParserV1()

_runtime: RunNvdIncrementalRuntimeV1 | None = None


class NvdIncrementalRuntimeUseCase(Protocol):
    """Define the incremental runtime capability required by Lambda."""

    def execute(
        self,
        *,
        request: NvdIncrementalRuntimeRequestV1,
    ) -> NvdIncrementalRuntimeResultV1:
        """Execute one authoritative incremental runtime attempt."""
        ...


class NvdIncrementalLambdaResponse(TypedDict):
    """Represent one JSON-serializable incremental Lambda result."""

    request_id: str
    status: str

    committed_through_at: str
    requested_target_end_at: str

    watermark_version_id: str
    watermark_etag: str
    watermark_sha256: str

    update_id: str | None
    window_start_at: str | None
    window_end_at: str | None

    total_results: int | None
    page_count: int | None

    bronze_manifest_key: str | None
    bronze_manifest_version_id: str | None
    bronze_manifest_sha256: str | None
    bronze_manifest_status: str | None


@logger.inject_lambda_context(
    clear_state=True,
    log_event=False,
)
@tracer.capture_lambda_handler
@metrics.log_metrics
def lambda_handler(
    event: Mapping[str, object],
    context: LambdaContext,
) -> NvdIncrementalLambdaResponse:
    """Handle one explicit NVD incremental runtime invocation."""
    request_id = context.aws_request_id

    try:
        request = invocation_parser.parse(event)
    except Exception:
        telemetry.metric(
            name="NvdIncrementalInvalidInvocation",
            value=1.0,
            unit="Count",
        )
        telemetry.exception(
            "NVD incremental invocation rejected",
            fields={
                "request_id": request_id,
            },
        )
        raise

    try:
        runtime = _get_runtime()
    except Exception:
        telemetry.metric(
            name="NvdIncrementalRuntimeInitializationFailure",
            value=1.0,
            unit="Count",
        )
        telemetry.exception(
            "NVD incremental runtime dependency initialization failed",
            fields={
                "request_id": request_id,
                "target_end_at": _canonical_utc(
                    request.target_end_at
                ),
            },
        )
        raise

    return execute_incremental_request(
        request=request,
        runtime=runtime,
        telemetry=telemetry,
        request_id=request_id,
    )


def execute_incremental_request(
    *,
    request: NvdIncrementalRuntimeRequestV1,
    runtime: NvdIncrementalRuntimeUseCase,
    telemetry: OperationalTelemetry,
    request_id: str,
) -> NvdIncrementalLambdaResponse:
    """Execute one parsed NVD incremental Lambda request."""
    telemetry.metric(
        name="NvdIncrementalInvocation",
        value=1.0,
        unit="Count",
    )

    telemetry.info(
        "Starting NVD incremental runtime invocation",
        fields={
            "request_id": request_id,
            "target_end_at": _canonical_utc(
                request.target_end_at
            ),
        },
    )

    try:
        result = runtime.execute(
            request=request,
        )
    except Exception:
        telemetry.metric(
            name="NvdIncrementalFailure",
            value=1.0,
            unit="Count",
        )

        telemetry.exception(
            "NVD incremental runtime invocation failed",
            fields={
                "request_id": request_id,
                "target_end_at": _canonical_utc(
                    request.target_end_at
                ),
            },
        )

        raise

    response = _serialize_result(
        result=result,
        request_id=request_id,
    )

    telemetry.metric(
        name="NvdIncrementalSuccess",
        value=1.0,
        unit="Count",
    )

    telemetry.info(
        "NVD incremental runtime invocation completed",
        fields={
            "request_id": request_id,
            "status": response["status"],
            "committed_through_at": (
                response["committed_through_at"]
            ),
            "requested_target_end_at": (
                response["requested_target_end_at"]
            ),
            "update_id": response["update_id"],
            "total_results": response["total_results"],
            "bronze_manifest_key": (
                response["bronze_manifest_key"]
            ),
        },
    )

    return response


def _serialize_result(
    *,
    result: NvdIncrementalRuntimeResultV1,
    request_id: str,
) -> NvdIncrementalLambdaResponse:
    """Serialize authoritative and Bronze runtime evidence."""
    persisted = result.watermark_snapshot

    response: NvdIncrementalLambdaResponse = {
        "request_id": request_id,
        "status": result.plan.status.value,
        "committed_through_at": _canonical_utc(
            persisted.watermark.committed_through_at
        ),
        "requested_target_end_at": _canonical_utc(
            result.plan.requested_target_end_at
        ),
        "watermark_version_id": persisted.version_id,
        "watermark_etag": persisted.etag,
        "watermark_sha256": persisted.sha256,
        "update_id": None,
        "window_start_at": None,
        "window_end_at": None,
        "total_results": None,
        "page_count": None,
        "bronze_manifest_key": None,
        "bronze_manifest_version_id": None,
        "bronze_manifest_sha256": None,
        "bronze_manifest_status": None,
    }

    ingestion = result.ingestion

    if ingestion is None:
        return response

    candidate = ingestion.candidate

    response["update_id"] = candidate.update_id
    response["window_start_at"] = (
        candidate.canonical_window_start_at
    )
    response["window_end_at"] = (
        candidate.canonical_window_end_at
    )
    response["total_results"] = candidate.total_results
    response["page_count"] = candidate.page_count

    response["bronze_manifest_key"] = (
        candidate.bronze_manifest_key
    )
    response["bronze_manifest_version_id"] = (
        candidate.bronze_manifest_version_id
    )
    response["bronze_manifest_sha256"] = (
        candidate.bronze_manifest_sha256
    )
    response["bronze_manifest_status"] = (
        ingestion.manifest_write.status.value
    )

    return response


def _get_runtime() -> RunNvdIncrementalRuntimeV1:
    """Return one lazily initialized incremental runtime instance."""
    global _runtime

    if _runtime is None:
        _runtime = build_incremental_runtime_from_environment(
            telemetry=telemetry,
        )

    return _runtime


def _canonical_utc(
    value: datetime,
) -> str:
    """Serialize one aware timestamp as canonical UTC."""
    timespec = (
        "microseconds"
        if value.microsecond
        else "seconds"
    )

    return (
        value.astimezone(UTC)
        .isoformat(timespec=timespec)
        .replace("+00:00", "Z")
    )
