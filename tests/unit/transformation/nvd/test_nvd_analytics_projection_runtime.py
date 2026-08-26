"""Tests for permanent NVD analytics binding, composition, and Lambda execution."""

from collections.abc import Mapping
from contextlib import AbstractContextManager, nullcontext
from datetime import UTC, datetime
from hashlib import sha256
from typing import cast

import pytest
from botocore.exceptions import ClientError

from opslens.transformation.nvd.adapters.inbound.analytics_projection_invocation import (
    NvdAnalyticsBootstrapSeedInvocationV1,
    NvdAnalyticsIncrementalWatermarkEventV1,
)
from opslens.transformation.nvd.adapters.outbound.analytics_projection_repository import (
    NvdAnalyticsProjectionRepositoryBindingV1,
)
from opslens.transformation.nvd.adapters.outbound.s3_analytics_projection import (
    NvdAnalyticsProjectionAlreadyExistsError,
    S3NvdAnalyticsProjectionClient,
    S3NvdAnalyticsProjectionRepositoryV1,
)
from opslens.transformation.nvd.adapters.outbound.s3_promotion_evidence import (
    S3NvdPromotionEvidenceClient,
)
from opslens.transformation.nvd.analytics_projection_composition import (
    compose_analytics_projection_runtime_dependencies,
)
from opslens.transformation.nvd.analytics_projection_config import (
    NvdAnalyticsProjectionRuntimeSettingsV1,
)
from opslens.transformation.nvd.analytics_projection_lambda_handler import (
    execute_projection_request,
)
from opslens.transformation.nvd.application.analytics_projection_key_factory import (
    NvdAnalyticsProjectionKeyFactoryV1,
    NvdAnalyticsProjectionKeyV1,
    NvdAnalyticsProjectionRequestV1,
)
from opslens.transformation.nvd.application.analytics_projection_models import (
    NvdAnalyticsExactObjectRefV1,
    NvdBootstrapAnalyticsProjectionRequestV1,
    NvdIncrementalAnalyticsProjectionRequestV1,
)
from opslens.transformation.nvd.application.analytics_projection_service import (
    NvdAnalyticsProjectionReplayRequiredError,
    NvdAnalyticsProjectionResultV1,
    NvdAnalyticsProjectionServiceV1,
)

BUCKET = "opslens-test-data"
UPDATE_ID = "a" * 64
LOGICAL_SHA = "b" * 64
MANIFEST_SHA = "c" * 64
FEED_REVISION = f"20260822T070013Z-{'d' * 64}"
PARQUET_BYTES = b"PAR1analytics-runtime-testPAR1"
PARQUET_SHA = sha256(PARQUET_BYTES).hexdigest()


class FakeTelemetry:
    """Capture operational telemetry emitted by the runtime boundary."""

    def __init__(self) -> None:
        """Initialize captured telemetry."""
        self.info_events: list[str] = []
        self.exception_events: list[str] = []
        self.metrics: list[tuple[str, float, str]] = []
        self.spans: list[str] = []

    def info(
        self,
        message: str,
        *,
        fields: Mapping[str, object] | None = None,
    ) -> None:
        """Capture one informational event."""
        del fields
        self.info_events.append(message)

    def exception(
        self,
        message: str,
        *,
        fields: Mapping[str, object] | None = None,
    ) -> None:
        """Capture one exception event."""
        del fields
        self.exception_events.append(message)

    def metric(
        self,
        name: str,
        value: float,
        unit: str,
    ) -> None:
        """Capture one metric."""
        self.metrics.append((name, value, unit))

    def span(
        self,
        name: str,
    ) -> AbstractContextManager[object]:
        """Capture one trace span."""
        self.spans.append(name)
        return nullcontext()


class NeverCalledS3Client:
    """Satisfy both exact-read and projection S3 protocols for composition tests."""

    def get_object(
        self,
        *,
        Bucket: str,
        Key: str,
        VersionId: str,
    ) -> Mapping[str, object]:
        """Fail if composition performs network work eagerly."""
        del Bucket, Key, VersionId
        raise AssertionError("composition must not call S3")

    def copy_object(
        self,
        *,
        Bucket: str,
        Key: str,
        CopySource: Mapping[str, str],
        IfNoneMatch: str,
        MetadataDirective: str,
        ContentType: str,
        Metadata: Mapping[str, str],
    ) -> Mapping[str, object]:
        """Fail if composition performs projection work eagerly."""
        del (
            Bucket,
            Key,
            CopySource,
            IfNoneMatch,
            MetadataDirective,
            ContentType,
            Metadata,
        )
        raise AssertionError("composition must not call S3")

    def head_object(
        self,
        *,
        Bucket: str,
        Key: str,
    ) -> Mapping[str, object]:
        """Fail if composition performs replay work eagerly."""
        del Bucket, Key
        raise AssertionError("composition must not call S3")


class FakeS3RepositoryDelegate:
    """Model the provider-specific collision exposed by the concrete S3 adapter."""

    def copy_if_absent(
        self,
        *,
        request: NvdAnalyticsProjectionRequestV1,
        destination: NvdAnalyticsProjectionKeyV1,
    ) -> NvdAnalyticsExactObjectRefV1:
        """Always require replay verification through the binding."""
        del request, destination
        raise NvdAnalyticsProjectionAlreadyExistsError(
            "provider-specific replay collision"
        )

    def verify_current(
        self,
        *,
        request: NvdAnalyticsProjectionRequestV1,
        destination: NvdAnalyticsProjectionKeyV1,
    ) -> NvdAnalyticsExactObjectRefV1:
        """Return deterministic current evidence if requested."""
        return NvdAnalyticsExactObjectRefV1(
            key=destination.object_key,
            version_id="analytics-version",
            sha256=request.silver_parquet.sha256,
            size_bytes=request.silver_parquet.size_bytes,
        )


class FakeProcessor:
    """Return prebuilt application results and capture runtime dispatch."""

    def __init__(
        self,
        *,
        incremental_result: NvdAnalyticsProjectionResultV1,
        bootstrap_result: NvdAnalyticsProjectionResultV1,
        error: Exception | None = None,
    ) -> None:
        """Initialize deterministic processor behavior."""
        self.incremental_result = incremental_result
        self.bootstrap_result = bootstrap_result
        self.error = error
        self.incremental_calls: list[tuple[str, str]] = []
        self.bootstrap_calls: list[tuple[str, str]] = []

    def project_incremental(
        self,
        *,
        watermark_key: str,
        watermark_version_id: str,
    ) -> NvdAnalyticsProjectionResultV1:
        """Capture incremental dispatch and return configured evidence."""
        self.incremental_calls.append(
            (watermark_key, watermark_version_id)
        )
        if self.error is not None:
            raise self.error
        return self.incremental_result

    def project_bootstrap(
        self,
        *,
        silver_complete_key: str,
        silver_complete_version_id: str,
    ) -> NvdAnalyticsProjectionResultV1:
        """Capture Bootstrap dispatch and return configured evidence."""
        self.bootstrap_calls.append(
            (silver_complete_key, silver_complete_version_id)
        )
        if self.error is not None:
            raise self.error
        return self.bootstrap_result


def _incremental_request() -> NvdIncrementalAnalyticsProjectionRequestV1:
    """Build one exact committed incremental request."""
    base = (
        "silver/nvd/cve/schema_version=1/"
        "source_kind=incremental/"
        f"update_id={UPDATE_ID}"
    )
    return NvdIncrementalAnalyticsProjectionRequestV1(
        update_id=UPDATE_ID,
        committed_through_at=datetime(
            2026,
            8,
            25,
            23,
            25,
            tzinfo=UTC,
        ),
        silver_manifest=NvdAnalyticsExactObjectRefV1(
            key=f"{base}/manifest.json",
            version_id="incremental-manifest-version",
            sha256=MANIFEST_SHA,
            size_bytes=2048,
        ),
        silver_parquet=NvdAnalyticsExactObjectRefV1(
            key=f"{base}/part-00000.parquet",
            version_id="incremental-parquet-version",
            sha256=PARQUET_SHA,
            size_bytes=len(PARQUET_BYTES),
        ),
        row_count=6749,
        logical_record_set_sha256=LOGICAL_SHA,
    )


def _bootstrap_request() -> NvdBootstrapAnalyticsProjectionRequestV1:
    """Build one explicit exact Bootstrap request."""
    base = (
        "silver/nvd/cve/schema_version=1/"
        "source_kind=bootstrap/"
        "feed_year=2026/"
        f"feed_revision={FEED_REVISION}"
    )
    return NvdBootstrapAnalyticsProjectionRequestV1(
        feed_year=2026,
        feed_revision=FEED_REVISION,
        source_observed_at=datetime(
            2026,
            8,
            22,
            7,
            0,
            13,
            tzinfo=UTC,
        ),
        silver_manifest=NvdAnalyticsExactObjectRefV1(
            key=f"{base}/manifest.json",
            version_id="bootstrap-manifest-version",
            sha256=MANIFEST_SHA,
            size_bytes=1947,
        ),
        silver_parquet=NvdAnalyticsExactObjectRefV1(
            key=f"{base}/part-00000.parquet",
            version_id="bootstrap-parquet-version",
            sha256=PARQUET_SHA,
            size_bytes=len(PARQUET_BYTES),
        ),
        row_count=48293,
        logical_record_set_sha256=LOGICAL_SHA,
    )


def _result(
    request: NvdAnalyticsProjectionRequestV1,
    *,
    status: str = "projected",
) -> NvdAnalyticsProjectionResultV1:
    """Build one verified projection result for Lambda dispatch tests."""
    destination = NvdAnalyticsProjectionKeyFactoryV1().build(
        request
    )
    return NvdAnalyticsProjectionResultV1(
        status=cast(
            "Literal['projected', 'already_projected']",
            status,
        ),
        request=request,
        destination=destination,
        projected_object=NvdAnalyticsExactObjectRefV1(
            key=destination.object_key,
            version_id="analytics-version",
            sha256=request.silver_parquet.sha256,
            size_bytes=request.silver_parquet.size_bytes,
        ),
    )


def test_runtime_settings_require_one_exact_data_bucket() -> None:
    """Keep runtime configuration minimal and fail closed when absent."""
    settings = NvdAnalyticsProjectionRuntimeSettingsV1.from_environment(
        {
            "NVD_DATA_BUCKET": BUCKET,
        }
    )
    assert settings.data_bucket == BUCKET

    with pytest.raises(
        RuntimeError,
        match="NVD_DATA_BUCKET",
    ):
        NvdAnalyticsProjectionRuntimeSettingsV1.from_environment({})


def test_composition_builds_service_without_eager_s3_calls() -> None:
    """Compose the complete application graph without performing provider work."""
    client = NeverCalledS3Client()
    dependencies = compose_analytics_projection_runtime_dependencies(
        settings=NvdAnalyticsProjectionRuntimeSettingsV1(
            data_bucket=BUCKET,
        ),
        telemetry=FakeTelemetry(),
        evidence_s3_client=cast(
            S3NvdPromotionEvidenceClient,
            client,
        ),
        projection_s3_client=cast(
            S3NvdAnalyticsProjectionClient,
            client,
        ),
    )

    assert isinstance(
        dependencies.service,
        NvdAnalyticsProjectionServiceV1,
    )


def test_s3_binding_translates_only_existing_destination_to_replay_contract() -> None:
    """Keep the application service independent from the S3-specific exception."""
    request = _incremental_request()
    destination = NvdAnalyticsProjectionKeyFactoryV1().build(
        request
    )
    binding = NvdAnalyticsProjectionRepositoryBindingV1(
        repository=cast(
            S3NvdAnalyticsProjectionRepositoryV1,
            FakeS3RepositoryDelegate(),
        )
    )

    with pytest.raises(
        NvdAnalyticsProjectionReplayRequiredError,
        match="exact replay verification",
    ):
        binding.copy_if_absent(
            request=request,
            destination=destination,
        )


def test_execute_incremental_projection_returns_verified_lineage() -> None:
    """Dispatch an exact watermark event and expose only verified result evidence."""
    incremental = _incremental_request()
    bootstrap = _bootstrap_request()
    processor = FakeProcessor(
        incremental_result=_result(incremental),
        bootstrap_result=_result(bootstrap),
    )
    telemetry = FakeTelemetry()
    trigger = NvdAnalyticsIncrementalWatermarkEventV1(
        bucket=BUCKET,
        watermark_key="control/nvd/cve/incremental/watermark.json",
        watermark_version_id="watermark-version",
        object_size_bytes=2048,
    )

    response = execute_projection_request(
        trigger=trigger,
        processor=processor,
        telemetry=telemetry,
        request_id="lambda-request-id",
    )

    assert response["status"] == "projected"
    assert response["source_kind"] == "incremental"
    assert response["source_batch_id"] == UPDATE_ID
    assert response["authority_state"] == "watermark_committed"
    assert response["projection_date"] == "2026-08-25"
    assert response["destination_version_id"] == "analytics-version"
    assert processor.incremental_calls == [
        (
            trigger.watermark_key,
            trigger.watermark_version_id,
        )
    ]
    assert processor.bootstrap_calls == []
    assert (
        "NvdAnalyticsProjectionSuccess",
        1.0,
        "Count",
    ) in telemetry.metrics


def test_execute_bootstrap_replay_reports_already_projected() -> None:
    """Dispatch explicit Bootstrap authority and preserve verified replay status."""
    incremental = _incremental_request()
    bootstrap = _bootstrap_request()
    processor = FakeProcessor(
        incremental_result=_result(incremental),
        bootstrap_result=_result(
            bootstrap,
            status="already_projected",
        ),
    )
    telemetry = FakeTelemetry()
    trigger = NvdAnalyticsBootstrapSeedInvocationV1(
        silver_complete_key=bootstrap.silver_manifest.key,
        silver_complete_version_id=bootstrap.silver_manifest.version_id,
    )

    response = execute_projection_request(
        trigger=trigger,
        processor=processor,
        telemetry=telemetry,
        request_id="lambda-request-id",
    )

    assert response["status"] == "already_projected"
    assert response["source_kind"] == "bootstrap"
    assert response["authority_state"] == "bootstrap_verified_seed"
    assert processor.incremental_calls == []
    assert processor.bootstrap_calls == [
        (
            trigger.silver_complete_key,
            trigger.silver_complete_version_id,
        )
    ]
    assert (
        "NvdAnalyticsAlreadyProjected",
        1.0,
        "Count",
    ) in telemetry.metrics


def test_execute_projection_failure_is_not_reclassified() -> None:
    """Emit failure telemetry and preserve application/provider exceptions."""
    incremental = _incremental_request()
    bootstrap = _bootstrap_request()
    processor = FakeProcessor(
        incremental_result=_result(incremental),
        bootstrap_result=_result(bootstrap),
        error=RuntimeError("projection failed"),
    )
    telemetry = FakeTelemetry()
    trigger = NvdAnalyticsIncrementalWatermarkEventV1(
        bucket=BUCKET,
        watermark_key="control/nvd/cve/incremental/watermark.json",
        watermark_version_id="watermark-version",
        object_size_bytes=2048,
    )

    with pytest.raises(
        RuntimeError,
        match="projection failed",
    ):
        execute_projection_request(
            trigger=trigger,
            processor=processor,
            telemetry=telemetry,
            request_id="lambda-request-id",
        )

    assert (
        "NvdAnalyticsProjectionFailure",
        1.0,
        "Count",
    ) in telemetry.metrics
    assert "Permanent NVD analytics projection failed" in telemetry.exception_events
