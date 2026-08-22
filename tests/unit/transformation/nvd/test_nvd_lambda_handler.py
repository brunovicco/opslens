"""Unit tests for the NVD Silver Lambda execution boundary."""

from collections.abc import Mapping
from contextlib import AbstractContextManager, nullcontext

import pytest

from opslens.transformation.nvd.application.runtime_models import (
    NvdSilverRuntimeRequestV1,
    NvdSilverRuntimeResultV1,
)
from opslens.transformation.nvd.lambda_handler import (
    execute_transformation_request,
)
from opslens.transformation.nvd.serialization.models import (
    NvdSilverSourceKind,
)

UPDATE_ID = "a" * 64

MANIFEST_KEY = f"bronze/nvd/cve/updates/update_id={UPDATE_ID}/manifest.json"


class FakeTelemetry:
    """Capture NVD Silver Lambda operational telemetry."""

    def __init__(self) -> None:
        """Initialize captured events."""
        self.metrics: list[str] = []
        self.exceptions: list[tuple[str, dict[str, object]]] = []

    def info(
        self,
        message: str,
        *,
        fields: Mapping[str, object] | None = None,
    ) -> None:
        """Accept informational telemetry."""
        del message, fields

    def exception(
        self,
        message: str,
        *,
        fields: Mapping[str, object] | None = None,
    ) -> None:
        """Capture exception telemetry."""
        self.exceptions.append(
            (
                message,
                dict(fields or {}),
            )
        )

    def metric(
        self,
        name: str,
        value: float,
        unit: str,
    ) -> None:
        """Capture metric names."""
        del value, unit
        self.metrics.append(name)

    def span(
        self,
        name: str,
    ) -> AbstractContextManager[object]:
        """Return one no-op tracing context."""
        del name
        return nullcontext()


class SuccessfulProcessor:
    """Return one fully completed NVD Silver runtime result."""

    def __init__(self) -> None:
        """Initialize request capture."""
        self.requests: list[NvdSilverRuntimeRequestV1] = []

    def process(
        self,
        request: NvdSilverRuntimeRequestV1,
    ) -> NvdSilverRuntimeResultV1:
        """Capture request and return exact final evidence."""
        self.requests.append(request)

        return NvdSilverRuntimeResultV1(
            source_kind=request.source_kind,
            source_batch_id=UPDATE_ID,
            bronze_manifest_key=request.manifest_key,
            bronze_manifest_version_id=request.manifest_version_id,
            bronze_manifest_sha256="b" * 64,
            silver_parquet_key=(
                "silver/nvd/cve/schema_version=1/"
                "source_kind=incremental/"
                f"update_id={UPDATE_ID}/part-00000.parquet"
            ),
            silver_parquet_version_id="parquet-version-1",
            silver_parquet_sha256="c" * 64,
            silver_complete_key=(
                "silver/nvd/cve/schema_version=1/"
                "source_kind=incremental/"
                f"update_id={UPDATE_ID}/manifest.json"
            ),
            silver_complete_version_id="complete-version-1",
            silver_complete_sha256="d" * 64,
            row_count=227,
        )


class RaisingProcessor:
    """Raise one configured runtime processing failure."""

    def process(
        self,
        request: NvdSilverRuntimeRequestV1,
    ) -> NvdSilverRuntimeResultV1:
        """Propagate a runtime failure to the Lambda boundary."""
        del request
        raise RuntimeError("runtime processing failure")


def _request() -> NvdSilverRuntimeRequestV1:
    """Build one valid exact runtime coordinate."""
    return NvdSilverRuntimeRequestV1(
        source_kind=NvdSilverSourceKind.INCREMENTAL,
        manifest_key=MANIFEST_KEY,
        manifest_version_id="manifest-version-1",
    )


def test_serializes_successful_complete_evidence() -> None:
    """Return JSON-compatible exact evidence only after persisted COMPLETE."""
    telemetry = FakeTelemetry()
    processor = SuccessfulProcessor()

    response = execute_transformation_request(
        request=_request(),
        processor=processor,
        telemetry=telemetry,
        request_id="lambda-request-1",
    )

    assert len(processor.requests) == 1

    assert response == {
        "request_id": "lambda-request-1",
        "status": "complete",
        "source_kind": "incremental",
        "source_batch_id": UPDATE_ID,
        "bronze_manifest_key": MANIFEST_KEY,
        "bronze_manifest_version_id": "manifest-version-1",
        "bronze_manifest_sha256": "b" * 64,
        "silver_parquet_key": (
            "silver/nvd/cve/schema_version=1/"
            "source_kind=incremental/"
            f"update_id={UPDATE_ID}/part-00000.parquet"
        ),
        "silver_parquet_version_id": "parquet-version-1",
        "silver_parquet_sha256": "c" * 64,
        "silver_complete_key": (
            "silver/nvd/cve/schema_version=1/"
            "source_kind=incremental/"
            f"update_id={UPDATE_ID}/manifest.json"
        ),
        "silver_complete_version_id": "complete-version-1",
        "silver_complete_sha256": "d" * 64,
        "row_count": 227,
    }

    assert "NvdSilverTransformationInvocation" in telemetry.metrics
    assert "NvdSilverTransformationSuccess" in telemetry.metrics
    assert "NvdSilverTransformationFailure" not in telemetry.metrics


def test_propagates_processing_failure() -> None:
    """Preserve Lambda retry semantics by propagating runtime failures."""
    telemetry = FakeTelemetry()

    with pytest.raises(
        RuntimeError,
        match="runtime processing failure",
    ):
        execute_transformation_request(
            request=_request(),
            processor=RaisingProcessor(),
            telemetry=telemetry,
            request_id="lambda-request-2",
        )

    assert "NvdSilverTransformationFailure" in telemetry.metrics
    assert "NvdSilverTransformationSuccess" not in telemetry.metrics

    assert len(telemetry.exceptions) == 1

    _, fields = telemetry.exceptions[0]

    assert fields["request_id"] == "lambda-request-2"
    assert fields["bronze_manifest_key"] == MANIFEST_KEY
