"""AWS Lambda entrypoint for CISA KEV Bronze catalog ingestion."""

from collections.abc import Mapping

from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

from opslens.ingestion.kev.application.models import RepositoryWriteStatus
from opslens.ingestion.kev.application.service import IngestKevCatalog
from opslens.ingestion.kev.composition import build_runtime_use_case
from opslens.shared.observability.ports import OperationalTelemetry
from opslens.shared.observability.powertools import PowertoolsTelemetry

SERVICE_NAME = "opslens-kev-ingestion"
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
    """Handle a CISA KEV ingestion Lambda invocation.

    Args:
        event: Lambda invocation event. Ingestion does not depend on its payload.
        context: AWS Lambda runtime context.

    Returns:
        Serialized KEV ingestion result.

    Raises:
        Exception: Propagates operational failures so asynchronous retry and
            failure-destination mechanisms can act.
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
    use_case: IngestKevCatalog,
    telemetry: OperationalTelemetry,
    request_id: str,
) -> dict[str, str | int | None]:
    """Execute KEV ingestion at the Lambda runtime boundary."""
    telemetry.metric(
        name="KevIngestionInvocation",
        value=1.0,
        unit="Count",
    )

    telemetry.info(
        "Starting CISA KEV ingestion invocation",
        fields={
            "request_id": request_id,
        },
    )

    try:
        result = use_case.execute()
    except Exception:
        telemetry.metric(
            name="KevIngestionFailure",
            value=1.0,
            unit="Count",
        )

        telemetry.exception(
            "CISA KEV ingestion invocation failed",
            fields={
                "request_id": request_id,
            },
        )

        raise

    telemetry.metric(
        name="KevIngestionSuccess",
        value=1.0,
        unit="Count",
    )

    if result.status is RepositoryWriteStatus.CREATED:
        telemetry.metric(
            name="KevIngestionCreated",
            value=1.0,
            unit="Count",
        )
    else:
        telemetry.metric(
            name="KevIngestionAlreadyExists",
            value=1.0,
            unit="Count",
        )

    telemetry.info(
        "CISA KEV ingestion invocation completed",
        fields={
            "request_id": request_id,
            "status": result.status.value,
            "snapshot_date": result.snapshot.snapshot_date,
            "catalog_version": result.snapshot.catalog_version,
            "record_count": result.snapshot.record_count,
            "s3_key": result.s3_key,
        },
    )

    return result.to_dict()
