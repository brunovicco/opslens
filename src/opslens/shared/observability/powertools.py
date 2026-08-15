"""AWS Lambda Powertools implementation of OpsLens operational telemetry."""

from collections.abc import Generator, Mapping
from contextlib import AbstractContextManager, contextmanager
from typing import Protocol, cast

from aws_lambda_powertools import Logger, Metrics, Tracer


class _TraceProvider(Protocol):
    """Define the tracing capability consumed from a Powertools provider."""

    def in_subsegment(
        self,
        name: str,
    ) -> AbstractContextManager[object]:
        """Create a tracing subsegment context manager."""
        ...


class PowertoolsTelemetry:
    """Provide structured logs, EMF metrics, and X-Ray tracing."""

    def __init__(
        self,
        logger: Logger,
        metrics: Metrics,
        tracer: Tracer,
    ) -> None:
        """Initialize telemetry using explicitly injected Powertools utilities."""
        self._logger = logger
        self._metrics = metrics
        self._tracer = tracer

    def info(
        self,
        message: str,
        *,
        fields: Mapping[str, object] | None = None,
    ) -> None:
        """Record a structured informational log."""
        self._logger.info(
            message,
            extra=dict(fields or {}),
        )

    def exception(
        self,
        message: str,
        *,
        fields: Mapping[str, object] | None = None,
    ) -> None:
        """Record a structured exception log with stack trace."""
        self._logger.exception(
            message,
            extra=dict(fields or {}),
        )

    def metric(
        self,
        name: str,
        value: float,
        unit: str,
    ) -> None:
        """Add a metric to the current Powertools EMF metric set."""
        self._metrics.add_metric(
            name=name,
            value=value,
            unit=unit,
        )

    @contextmanager
    def span(
        self,
        name: str,
    ) -> Generator[object]:
        """Create an AWS X-Ray subsegment for an infrastructure operation."""
        provider = cast(
            _TraceProvider,
            self._tracer.provider,
        )

        with provider.in_subsegment(
            f"## {name}",
        ) as subsegment:
            yield subsegment
