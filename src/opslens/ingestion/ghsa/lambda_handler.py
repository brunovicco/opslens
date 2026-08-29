"""AWS Lambda entrypoint for bounded GHSA Bronze ingestion."""

from collections.abc import Mapping
from typing import Literal, Protocol, TypedDict

from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

from opslens.ingestion.ghsa.adapters.inbound.invocation import (
    GhsaBronzeInvocationParserV1,
)
from opslens.ingestion.ghsa.application.runtime import (
    GhsaBronzeAttemptCompletion,
    GhsaBronzeRuntimeService,
)
from opslens.ingestion.ghsa.domain.sync import GhsaSyncWindow
from opslens.ingestion.ghsa.runtime_composition import (
    build_ghsa_bronze_runtime_from_environment,
)
from opslens.shared.observability.ports import OperationalTelemetry
from opslens.shared.observability.powertools import PowertoolsTelemetry

SERVICE_NAME = "opslens-ghsa-bronze"
METRICS_NAMESPACE = "OpsLens"

logger = Logger(service=SERVICE_NAME)
metrics = Metrics(namespace=METRICS_NAMESPACE, service=SERVICE_NAME)
tracer = Tracer(service=SERVICE_NAME)

telemetry = PowertoolsTelemetry(
    logger=logger,
    metrics=metrics,
    tracer=tracer,
)

invocation_parser = GhsaBronzeInvocationParserV1()

_runtime: GhsaBronzeRuntimeService | None = None


class GhsaBronzeRuntimeUseCase(Protocol):
    """Define the bounded Bronze runtime capability required by Lambda."""

    def run(
        self,
        window: GhsaSyncWindow,
    ) -> tuple[GhsaBronzeAttemptCompletion, ...]:
        """Complete one root synchronization window."""
        ...


class GhsaLeafCompletionResponse(TypedDict):
    """Represent one persisted leaf-window COMPLETE result."""

    sync_id: str
    attempt_id: str
    page_count: int
    total_items: int
    total_bytes: int
    manifest_key: str
    manifest_version_id: str


class GhsaBronzeLambdaResponse(TypedDict):
    """Represent one JSON-serializable manual GHSA Bronze result."""

    request_id: str
    status: Literal["complete"]
    schema_version: int
    mode: str
    root_sync_id: str
    window_start_at: str
    window_end_at: str
    leaf_count: int
    total_items: int
    total_bytes: int
    leaves: list[GhsaLeafCompletionResponse]


@logger.inject_lambda_context(
    clear_state=True,
    log_event=False,
)
@tracer.capture_lambda_handler
@metrics.log_metrics
def lambda_handler(
    event: Mapping[str, object],
    context: LambdaContext,
) -> GhsaBronzeLambdaResponse:
    """Handle one explicit v1 GHSA Bronze synchronization invocation."""
    request_id = context.aws_request_id

    try:
        window = invocation_parser.parse(event)
    except Exception:
        telemetry.metric(
            name="GhsaBronzeInvalidInvocation",
            value=1.0,
            unit="Count",
        )
        telemetry.exception(
            "GHSA Bronze invocation rejected",
            fields={"request_id": request_id},
        )
        raise

    try:
        runtime = _get_runtime()
    except Exception:
        telemetry.metric(
            name="GhsaBronzeRuntimeInitializationFailure",
            value=1.0,
            unit="Count",
        )
        telemetry.exception(
            "GHSA Bronze runtime dependency initialization failed",
            fields={
                "request_id": request_id,
                "root_sync_id": window.sync_id,
            },
        )
        raise

    return execute_bronze_request(
        window=window,
        runtime=runtime,
        telemetry=telemetry,
        request_id=request_id,
    )


def execute_bronze_request(
    *,
    window: GhsaSyncWindow,
    runtime: GhsaBronzeRuntimeUseCase,
    telemetry: OperationalTelemetry,
    request_id: str,
) -> GhsaBronzeLambdaResponse:
    """Execute one parsed GHSA Bronze request and serialize COMPLETE evidence."""
    telemetry.metric(
        name="GhsaBronzeInvocation",
        value=1.0,
        unit="Count",
    )
    telemetry.info(
        "Starting GHSA Bronze runtime invocation",
        fields={
            "request_id": request_id,
            "mode": window.mode.value,
            "root_sync_id": window.sync_id,
            "window_start_at": window.canonical_start_at,
            "window_end_at": window.canonical_end_at,
        },
    )

    try:
        completions = runtime.run(window)
    except Exception:
        telemetry.metric(
            name="GhsaBronzeFailure",
            value=1.0,
            unit="Count",
        )
        telemetry.exception(
            "GHSA Bronze runtime invocation failed",
            fields={
                "request_id": request_id,
                "root_sync_id": window.sync_id,
            },
        )
        raise

    leaves = [
        _serialize_completion(completion)
        for completion in completions
    ]
    response: GhsaBronzeLambdaResponse = {
        "request_id": request_id,
        "status": "complete",
        "schema_version": GhsaBronzeInvocationParserV1.SCHEMA_VERSION,
        "mode": window.mode.value,
        "root_sync_id": window.sync_id,
        "window_start_at": window.canonical_start_at,
        "window_end_at": window.canonical_end_at,
        "leaf_count": len(leaves),
        "total_items": sum(leaf["total_items"] for leaf in leaves),
        "total_bytes": sum(leaf["total_bytes"] for leaf in leaves),
        "leaves": leaves,
    }

    telemetry.metric(
        name="GhsaBronzeSuccess",
        value=1.0,
        unit="Count",
    )
    telemetry.info(
        "GHSA Bronze runtime invocation completed",
        fields={
            "request_id": request_id,
            "root_sync_id": response["root_sync_id"],
            "leaf_count": response["leaf_count"],
            "total_items": response["total_items"],
            "total_bytes": response["total_bytes"],
        },
    )

    return response


def _serialize_completion(
    completion: GhsaBronzeAttemptCompletion,
) -> GhsaLeafCompletionResponse:
    """Serialize one leaf COMPLETE result without secret or transport metadata."""
    return {
        "sync_id": completion.sync_id,
        "attempt_id": completion.attempt_id,
        "page_count": completion.page_count,
        "total_items": completion.total_items,
        "total_bytes": completion.total_bytes,
        "manifest_key": completion.manifest_key,
        "manifest_version_id": completion.manifest_version_id,
    }


def _get_runtime() -> GhsaBronzeRuntimeService:
    """Return one lazily initialized GHSA Bronze runtime instance."""
    global _runtime

    if _runtime is None:
        _runtime = build_ghsa_bronze_runtime_from_environment(
            telemetry=telemetry,
        )

    return _runtime
