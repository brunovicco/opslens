"""AWS Lambda entrypoint for EPSS Bronze snapshot ingestion."""

from collections.abc import Mapping

from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

from opslens.ingestion.epss.application.models import RepositoryWriteStatus
from opslens.ingestion.epss.application.service import IngestEpssSnapshot
from opslens.ingestion.epss.composition import build_runtime_use_case
from opslens.shared.observability.ports import OperationalTelemetry
from opslens.shared.observability.powertools import PowertoolsTelemetry

SERVICE_NAME = "opslens-epss-ingestion"
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


@logger.inject_lambda_context(
    clear_state=True,
    log_event=False,
)
@tracer.capture_lambda_handler
@metrics.log_metrics
def lambda_handler(
    event: Mapping[str, object],
    context: LambdaContext,
) -> dict[str, str | int | None]:
    """Handle an EPSS ingestion Lambda invocation.

    Args:
        event: Lambda invocation event. The current ingestion flow does not
            depend on event payload data.
        context: AWS Lambda runtime context.

    Returns:
        Serialized EPSS ingestion result.

    Raises:
        Exception: Propagates operational failures so Lambda correctly records
            the invocation as failed and upstream retry mechanisms can act.
    """
    del event

    use_case = build_runtime_use_case(
        telemetry=telemetry,
    )

    return execute_ingestion(
        use_case=use_case,
        telemetry=telemetry,
        request_id=context.aws_request_id,
    )


def execute_ingestion(
    use_case: IngestEpssSnapshot,
    telemetry: OperationalTelemetry,
    request_id: str,
) -> dict[str, str | int | None]:
    """Execute EPSS ingestion at the runtime boundary.

    Args:
        use_case: Fully composed EPSS ingestion application service.
        telemetry: Operational telemetry implementation.
        request_id: AWS Lambda invocation request identifier.

    Returns:
        Serialized ingestion result.

    Raises:
        Exception: Propagates any ingestion failure after recording telemetry.
    """
    telemetry.metric(
        name="EpssIngestionInvocation",
        value=1.0,
        unit="Count",
    )

    telemetry.info(
        "Starting EPSS ingestion invocation",
        fields={
            "request_id": request_id,
        },
    )

    try:
        result = use_case.execute()
    except Exception:
        telemetry.metric(
            name="EpssIngestionFailure",
            value=1.0,
            unit="Count",
        )

        telemetry.exception(
            "EPSS ingestion invocation failed",
            fields={
                "request_id": request_id,
            },
        )

        raise

    telemetry.metric(
        name="EpssIngestionSuccess",
        value=1.0,
        unit="Count",
    )

    if result.status is RepositoryWriteStatus.CREATED:
        telemetry.metric(
            name="EpssIngestionCreated",
            value=1.0,
            unit="Count",
        )
    else:
        telemetry.metric(
            name="EpssIngestionAlreadyExists",
            value=1.0,
            unit="Count",
        )

    telemetry.info(
        "EPSS ingestion invocation completed",
        fields={
            "request_id": request_id,
            "status": result.status.value,
            "snapshot_date": result.snapshot.snapshot_date,
            "model_version": result.snapshot.model_version,
            "row_count": result.snapshot.row_count,
            "s3_key": result.s3_key,
        },
    )

    return result.to_dict()
