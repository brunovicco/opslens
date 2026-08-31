"""AWS Lambda entrypoint for explicit one-snapshot historical EPSS transformation."""

from collections.abc import Mapping
from typing import Protocol, TypedDict

from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

from opslens.shared.observability.ports import OperationalTelemetry
from opslens.shared.observability.powertools import PowertoolsTelemetry
from opslens.transformation.epss.history.composition import build_runtime_executor
from opslens.transformation.epss.history.invocation import HistoricalEpssInvocationResultV1

SERVICE_NAME = "opslens-epss-history-transformer"
METRICS_NAMESPACE = "OpsLens"

logger = Logger(service=SERVICE_NAME)
metrics = Metrics(namespace=METRICS_NAMESPACE, service=SERVICE_NAME)
tracer = Tracer(service=SERVICE_NAME)
telemetry = PowertoolsTelemetry(logger=logger, metrics=metrics, tracer=tracer)


class HistoricalEpssInvocationUseCase(Protocol):
    """Define the strict explicit invocation capability required by Lambda."""

    def execute(self, event: Mapping[str, object]) -> HistoricalEpssInvocationResultV1:
        """Execute one exact historical snapshot transformation."""
        ...


class HistoricalEpssTransformerResponse(TypedDict):
    """Represent exact persisted evidence returned to the coordinator."""

    request_id: str
    snapshot_date: str
    silver_key: str
    silver_version_id: str
    silver_sha256: str
    silver_replay_status: str
    completion_key: str
    completion_version_id: str
    completion_sha256: str
    completion_replay_status: str


@logger.inject_lambda_context(clear_state=True, log_event=False)
@tracer.capture_lambda_handler
@metrics.log_metrics
def lambda_handler(
    event: Mapping[str, object],
    context: LambdaContext,
) -> HistoricalEpssTransformerResponse:
    """Transform one explicitly authorized historical EPSS Bronze manifest."""
    executor = build_runtime_executor(telemetry=telemetry)
    return execute_historical_event(
        event=event,
        use_case=executor,
        telemetry=telemetry,
        request_id=context.aws_request_id,
    )


def execute_historical_event(
    *,
    event: Mapping[str, object],
    use_case: HistoricalEpssInvocationUseCase,
    telemetry: OperationalTelemetry,
    request_id: str,
) -> HistoricalEpssTransformerResponse:
    """Execute and serialize one strict historical transformation invocation."""
    telemetry.metric(name="EpssHistoryTransformerInvocation", value=1.0, unit="Count")
    telemetry.info(
        "Starting historical EPSS transformer invocation",
        fields={"request_id": request_id},
    )

    try:
        result = use_case.execute(event)
    except Exception:
        telemetry.metric(name="EpssHistoryTransformerFailure", value=1.0, unit="Count")
        telemetry.exception(
            "Historical EPSS transformer invocation failed",
            fields={"request_id": request_id},
        )
        raise

    silver = result.silver.stored_object
    completion = result.completion.stored_object
    response: HistoricalEpssTransformerResponse = {
        "request_id": request_id,
        "snapshot_date": result.snapshot_date.isoformat(),
        "silver_key": silver.key,
        "silver_version_id": silver.version_id,
        "silver_sha256": silver.parquet_sha256,
        "silver_replay_status": result.silver.replay_status.value,
        "completion_key": completion.key,
        "completion_version_id": completion.version_id,
        "completion_sha256": completion.sha256,
        "completion_replay_status": result.completion.replay_status.value,
    }

    telemetry.metric(name="EpssHistoryTransformerSuccess", value=1.0, unit="Count")
    telemetry.info(
        "Historical EPSS transformer invocation completed",
        fields={
            "request_id": request_id,
            "snapshot_date": response["snapshot_date"],
            "silver_key": response["silver_key"],
            "silver_version_id": response["silver_version_id"],
            "silver_replay_status": response["silver_replay_status"],
            "completion_key": response["completion_key"],
            "completion_version_id": response["completion_version_id"],
            "completion_replay_status": response["completion_replay_status"],
        },
    )
    return response
