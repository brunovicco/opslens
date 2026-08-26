"""Unit tests for the NVD incremental Lambda runtime boundary."""

from collections.abc import Generator, Mapping
from contextlib import contextmanager
from datetime import UTC, datetime

import pytest

from opslens.ingestion.nvd.application.authoritative_watermark import (
    NvdAuthoritativeWatermarkV1,
    NvdWatermarkBootstrapRecoverySeedV1,
    NvdWatermarkEvidenceObjectV1,
)
from opslens.ingestion.nvd.application.authoritative_watermark_store import (
    NvdPersistedAuthoritativeWatermarkV1,
)
from opslens.ingestion.nvd.application.incremental_runtime_plan import (
    NvdIncrementalRuntimePlannerV1,
    NvdIncrementalRuntimeRequestV1,
)
from opslens.ingestion.nvd.application.incremental_runtime_service import (
    NvdIncrementalRuntimeResultV1,
)
from opslens.ingestion.nvd.incremental_lambda_handler import (
    execute_incremental_request,
)


class FakeTelemetry:
    """Record minimal telemetry emitted by the runtime boundary."""

    def __init__(self) -> None:
        """Initialize recorded telemetry."""
        self.metrics: list[str] = []
        self.exceptions: list[str] = []

    def info(
        self,
        message: str,
        *,
        fields: Mapping[str, object] | None = None,
    ) -> None:
        """Accept informational telemetry."""

    def exception(
        self,
        message: str,
        *,
        fields: Mapping[str, object] | None = None,
    ) -> None:
        """Record exception telemetry."""
        self.exceptions.append(message)

    def metric(
        self,
        name: str,
        value: float,
        unit: str,
    ) -> None:
        """Record metric names."""
        self.metrics.append(name)

    @contextmanager
    def span(
        self,
        name: str,
    ) -> Generator[object]:
        """Provide an inert tracing span."""
        yield object()


def _persisted_watermark(
    committed_through_at: datetime,
) -> NvdPersistedAuthoritativeWatermarkV1:
    """Build one persisted authority snapshot."""
    watermark = NvdAuthoritativeWatermarkV1(
        committed_through_at=committed_through_at,
        commit_basis=NvdWatermarkBootstrapRecoverySeedV1(
            source_revision_at=committed_through_at,
            bootstrap_manifest=NvdWatermarkEvidenceObjectV1(
                key="bronze/nvd/cve/bootstrap/test/manifest.json",
                version_id="bootstrap-version",
                sha256="a" * 64,
            ),
        ),
    )

    return NvdPersistedAuthoritativeWatermarkV1(
        watermark=watermark,
        version_id="watermark-version",
        etag='"watermark-etag"',
        sha256="b" * 64,
        size_bytes=621,
    )


class FakeRuntime:
    """Return one predetermined incremental runtime result."""

    def __init__(
        self,
        result: NvdIncrementalRuntimeResultV1,
    ) -> None:
        """Initialize the runtime with one result."""
        self.result = result
        self.requests: list[NvdIncrementalRuntimeRequestV1] = []

    def execute(
        self,
        *,
        request: NvdIncrementalRuntimeRequestV1,
    ) -> NvdIncrementalRuntimeResultV1:
        """Record and return one runtime result."""
        self.requests.append(request)
        return self.result


class FailingRuntime:
    """Fail every incremental execution."""

    def execute(
        self,
        *,
        request: NvdIncrementalRuntimeRequestV1,
    ) -> NvdIncrementalRuntimeResultV1:
        """Raise a deterministic runtime failure."""
        raise RuntimeError("simulated incremental failure")


def test_noop_response_contains_authority_without_bronze_evidence() -> None:
    """Expose the authority read while proving no Bronze work occurred."""
    committed_at = datetime(
        2026,
        8,
        24,
        18,
        0,
        tzinfo=UTC,
    )

    request = NvdIncrementalRuntimeRequestV1(
        target_end_at=committed_at,
    )

    persisted = _persisted_watermark(
        committed_at,
    )

    plan = NvdIncrementalRuntimePlannerV1().plan(
        committed_through_at=committed_at,
        request=request,
    )

    result = NvdIncrementalRuntimeResultV1(
        watermark_snapshot=persisted,
        plan=plan,
        ingestion=None,
    )

    runtime = FakeRuntime(result)
    telemetry = FakeTelemetry()

    response = execute_incremental_request(
        request=request,
        runtime=runtime,
        telemetry=telemetry,
        request_id="request-123",
    )

    assert runtime.requests == [request]

    assert response["status"] == "noop_already_current"
    assert response["committed_through_at"] == "2026-08-24T18:00:00Z"

    assert response["watermark_version_id"] == "watermark-version"
    assert response["watermark_etag"] == '"watermark-etag"'
    assert response["watermark_sha256"] == "b" * 64

    assert response["update_id"] is None
    assert response["total_results"] is None
    assert response["page_count"] is None
    assert response["bronze_manifest_key"] is None

    assert "NvdIncrementalSuccess" in telemetry.metrics


def test_runtime_failure_is_recorded_and_propagated() -> None:
    """Fail closed when the incremental application service fails."""
    request = NvdIncrementalRuntimeRequestV1(
        target_end_at=datetime(
            2026,
            8,
            24,
            19,
            0,
            tzinfo=UTC,
        ),
    )

    telemetry = FakeTelemetry()

    with pytest.raises(
        RuntimeError,
        match="simulated incremental failure",
    ):
        execute_incremental_request(
            request=request,
            runtime=FailingRuntime(),
            telemetry=telemetry,
            request_id="request-failure",
        )

    assert "NvdIncrementalFailure" in telemetry.metrics
    assert (
        "NVD incremental runtime invocation failed"
        in telemetry.exceptions
    )
