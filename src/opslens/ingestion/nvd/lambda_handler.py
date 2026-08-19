"""AWS Lambda entrypoint for NVD Bootstrap Bronze ingestion."""

from collections.abc import Mapping

from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.utilities.typing import LambdaContext

from opslens.ingestion.nvd.application.service import IngestNvdBootstrapFeed
from opslens.ingestion.nvd.composition import build_runtime_use_case
from opslens.shared.observability.ports import OperationalTelemetry
from opslens.shared.observability.powertools import PowertoolsTelemetry

SERVICE_NAME = "opslens-nvd-bootstrap-ingestion"
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
    """Handle one manually requested NVD yearly-feed bootstrap.

    Args:
        event: Invocation event containing an explicit integer ``feed_year``.
        context: AWS Lambda runtime context.

    Returns:
        Serialized evidence for the completed Bronze revision.

    Raises:
        ValueError: If the invocation does not contain a valid feed year.
        Exception: Propagates ingestion failures so the invocation fails closed.
    """
    feed_year = parse_feed_year(event)

    use_case = build_runtime_use_case(
        telemetry=telemetry,
    )

    return execute_ingestion(
        use_case=use_case,
        telemetry=telemetry,
        request_id=context.aws_request_id,
        feed_year=feed_year,
    )


def execute_ingestion(
    *,
    use_case: IngestNvdBootstrapFeed,
    telemetry: OperationalTelemetry,
    request_id: str,
    feed_year: int,
) -> dict[str, str | int | None]:
    """Execute NVD Bootstrap ingestion at the Lambda runtime boundary."""
    telemetry.metric(
        name="NvdBootstrapIngestionInvocation",
        value=1.0,
        unit="Count",
    )

    telemetry.info(
        "Starting NVD Bootstrap ingestion invocation",
        fields={
            "request_id": request_id,
            "feed_year": feed_year,
        },
    )

    try:
        result = use_case.execute(
            feed_year=feed_year,
        )
    except Exception:
        telemetry.metric(
            name="NvdBootstrapIngestionFailure",
            value=1.0,
            unit="Count",
        )

        telemetry.exception(
            "NVD Bootstrap ingestion invocation failed",
            fields={
                "request_id": request_id,
                "feed_year": feed_year,
            },
        )

        raise

    telemetry.metric(
        name="NvdBootstrapIngestionSuccess",
        value=1.0,
        unit="Count",
    )

    telemetry.info(
        "NVD Bootstrap ingestion invocation completed",
        fields={
            "request_id": request_id,
            "feed_year": result.feed_year,
            "feed_revision": result.feed_revision,
            "feed_status": result.feed_write.status.value,
            "meta_status": result.meta_write.status.value,
            "manifest_status": result.manifest_write.status.value,
            "manifest_key": result.manifest_key,
        },
    )

    return {
        "feed_year": result.feed_year,
        "feed_revision": result.feed_revision,
        "source_sha256": result.source_sha256,
        "feed_key": result.feed_key,
        "feed_status": result.feed_write.status.value,
        "feed_version_id": result.feed_write.version_id,
        "feed_etag": result.feed_write.etag,
        "meta_key": result.meta_key,
        "meta_status": result.meta_write.status.value,
        "meta_version_id": result.meta_write.version_id,
        "meta_etag": result.meta_write.etag,
        "manifest_key": result.manifest_key,
        "manifest_status": result.manifest_write.status.value,
        "manifest_version_id": result.manifest_write.version_id,
        "manifest_etag": result.manifest_write.etag,
    }


def parse_feed_year(
    event: Mapping[str, object],
) -> int:
    """Extract one explicit four-digit integer feed year."""
    value = event.get("feed_year")

    if type(value) is not int:
        raise ValueError("NVD Lambda event feed_year must be an integer.")

    if value < 1000 or value > 9999:
        raise ValueError("NVD Lambda event feed_year must contain exactly four digits.")

    return value
