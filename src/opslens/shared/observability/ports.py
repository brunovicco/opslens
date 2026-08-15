"""Observability ports shared by OpsLens infrastructure boundaries."""

from collections.abc import Mapping
from contextlib import AbstractContextManager
from typing import Protocol


class OperationalTelemetry(Protocol):
    """Define runtime observability capabilities used by infrastructure adapters."""

    def info(
        self,
        message: str,
        *,
        fields: Mapping[str, object] | None = None,
    ) -> None:
        """Record a structured informational event."""
        ...

    def exception(
        self,
        message: str,
        *,
        fields: Mapping[str, object] | None = None,
    ) -> None:
        """Record a structured exception event."""
        ...

    def metric(
        self,
        name: str,
        value: float,
        unit: str,
    ) -> None:
        """Record an operational metric."""
        ...

    def span(
        self,
        name: str,
    ) -> AbstractContextManager[object]:
        """Create a distributed tracing span."""
        ...
