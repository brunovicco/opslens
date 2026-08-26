"""Tests for permanent NVD analytics projection application orchestration."""

from datetime import UTC, datetime
from hashlib import sha256

import pytest

from opslens.transformation.nvd.application.analytics_projection_key_factory import (
    NvdAnalyticsProjectionKeyV1,
    NvdAnalyticsProjectionRequestV1,
)
from opslens.transformation.nvd.application.analytics_projection_models import (
    NvdAnalyticsExactObjectRefV1,
    NvdBootstrapAnalyticsProjectionRequestV1,
    NvdIncrementalAnalyticsProjectionRequestV1,
)
from opslens.transformation.nvd.application.analytics_projection_service import (
    InvalidNvdAnalyticsProjectionResultError,
    NvdAnalyticsProjectionReplayRequiredError,
    NvdAnalyticsProjectionResultV1,
    NvdAnalyticsProjectionServiceV1,
)

UPDATE_ID = "a" * 64
LOGICAL_SHA = "b" * 64
MANIFEST_SHA = "c" * 64
PARQUET_BYTES = b"PAR1analytics-service-testPAR1"
PARQUET_SHA = sha256(PARQUET_BYTES).hexdigest()
FEED_REVISION = f"20260822T070013Z-{'d' * 64}"


class FakeEvidenceLoader:
    """Return pre-authorized projection requests and capture coordinates."""

    def __init__(
        self,
        *,
        incremental: NvdIncrementalAnalyticsProjectionRequestV1,
        bootstrap: NvdBootstrapAnalyticsProjectionRequestV1,
    ) -> None:
        """Initialize deterministic application evidence."""
        self.incremental = incremental
        self.bootstrap = bootstrap
        self.incremental_calls: list[tuple[str, str]] = []
        self.bootstrap_calls: list[tuple[str, str]] = []

    def load_incremental(
        self,
        *,
        watermark_key: str,
        watermark_version_id: str,
    ) -> NvdIncrementalAnalyticsProjectionRequestV1:
        """Capture one exact incremental authority request."""
        self.incremental_calls.append(
            (watermark_key, watermark_version_id)
        )
        return self.incremental

    def load_bootstrap(
        self,
        *,
        silver_complete_key: str,
        silver_complete_version_id: str,
    ) -> NvdBootstrapAnalyticsProjectionRequestV1:
        """Capture one explicit Bootstrap seed request."""
        self.bootstrap_calls.append(
            (silver_complete_key, silver_complete_version_id)
        )
        return self.bootstrap


class FakeProjectionRepository:
    """Model projection, replay, and provider failures at the application port."""

    def __init__(
        self,
        *,
        copy_result: NvdAnalyticsExactObjectRefV1 | None = None,
        verify_result: NvdAnalyticsExactObjectRefV1 | None = None,
        copy_error: Exception | None = None,
    ) -> None:
        """Initialize deterministic repository behavior."""
        self.copy_result = copy_result
        self.verify_result = verify_result
        self.copy_error = copy_error
        self.copy_calls: list[
            tuple[NvdAnalyticsProjectionRequestV1, NvdAnalyticsProjectionKeyV1]
        ] = []
        self.verify_calls: list[
            tuple[NvdAnalyticsProjectionRequestV1, NvdAnalyticsProjectionKeyV1]
        ] = []

    def copy_if_absent(
        self,
        *,
        request: NvdAnalyticsProjectionRequestV1,
        destination: NvdAnalyticsProjectionKeyV1,
    ) -> NvdAnalyticsExactObjectRefV1:
        """Return a new projection or raise the configured port error."""
        self.copy_calls.append((request, destination))
        if self.copy_error is not None:
            raise self.copy_error
        if self.copy_result is None:
            raise AssertionError("copy_result must be configured")
        return self.copy_result

    def verify_current(
        self,
        *,
        request: NvdAnalyticsProjectionRequestV1,
        destination: NvdAnalyticsProjectionKeyV1,
    ) -> NvdAnalyticsExactObjectRefV1:
        """Return exact replay evidence for the deterministic destination."""
        self.verify_calls.append((request, destination))
        if self.verify_result is None:
            raise AssertionError("verify_result must be configured")
        return self.verify_result


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
    """Build one explicit exact Bootstrap seed request."""
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


def _projected(
    *,
    key: str,
    source: NvdAnalyticsExactObjectRefV1,
) -> NvdAnalyticsExactObjectRefV1:
    """Build exact destination evidence matching one source object."""
    return NvdAnalyticsExactObjectRefV1(
        key=key,
        version_id="analytics-version",
        sha256=source.sha256,
        size_bytes=source.size_bytes,
    )


def _loader() -> FakeEvidenceLoader:
    """Build a loader containing both supported projection kinds."""
    return FakeEvidenceLoader(
        incremental=_incremental_request(),
        bootstrap=_bootstrap_request(),
    )


def test_project_incremental_materializes_deterministic_destination() -> None:
    """Project new incremental authority without invoking replay verification."""
    loader = _loader()
    request = loader.incremental
    expected_key = (
        "analytics/nvd/cve/schema_version=1/"
        "source_kind=incremental/"
        "projection_date=2026-08-25/"
        f"update_id={UPDATE_ID}.parquet"
    )
    repository = FakeProjectionRepository(
        copy_result=_projected(
            key=expected_key,
            source=request.silver_parquet,
        )
    )
    service = NvdAnalyticsProjectionServiceV1(
        evidence_loader=loader,
        repository=repository,
    )

    result = service.project_incremental(
        watermark_key="control/nvd/cve/incremental/watermark.json",
        watermark_version_id="watermark-version",
    )

    assert isinstance(result, NvdAnalyticsProjectionResultV1)
    assert result.status == "projected"
    assert result.destination.object_key == expected_key
    assert result.destination.source_kind_partition == "incremental"
    assert result.destination.projection_date == "2026-08-25"
    assert result.projected_object.key == expected_key
    assert loader.incremental_calls == [
        (
            "control/nvd/cve/incremental/watermark.json",
            "watermark-version",
        )
    ]
    assert len(repository.copy_calls) == 1
    assert repository.verify_calls == []


def test_replay_requires_exact_current_destination_verification() -> None:
    """Accept an existing key only after the repository verifies current evidence."""
    loader = _loader()
    request = loader.incremental
    expected_key = (
        "analytics/nvd/cve/schema_version=1/"
        "source_kind=incremental/"
        "projection_date=2026-08-25/"
        f"update_id={UPDATE_ID}.parquet"
    )
    repository = FakeProjectionRepository(
        copy_error=NvdAnalyticsProjectionReplayRequiredError(
            "replay verification required"
        ),
        verify_result=_projected(
            key=expected_key,
            source=request.silver_parquet,
        ),
    )

    result = NvdAnalyticsProjectionServiceV1(
        evidence_loader=loader,
        repository=repository,
    ).project_incremental(
        watermark_key="control/nvd/cve/incremental/watermark.json",
        watermark_version_id="watermark-version",
    )

    assert result.status == "already_projected"
    assert len(repository.copy_calls) == 1
    assert len(repository.verify_calls) == 1
    assert repository.verify_calls[0] == repository.copy_calls[0]


def test_non_replay_repository_failure_is_not_reclassified() -> None:
    """Propagate provider failures instead of guessing that they are replays."""
    loader = _loader()
    repository = FakeProjectionRepository(
        copy_error=RuntimeError("provider failed")
    )
    service = NvdAnalyticsProjectionServiceV1(
        evidence_loader=loader,
        repository=repository,
    )

    with pytest.raises(
        RuntimeError,
        match="provider failed",
    ):
        service.project_incremental(
            watermark_key="control/nvd/cve/incremental/watermark.json",
            watermark_version_id="watermark-version",
        )

    assert repository.verify_calls == []


def test_project_bootstrap_uses_explicit_complete_coordinates() -> None:
    """Keep Bootstrap eligibility bound to the explicit exact COMPLETE invocation."""
    loader = _loader()
    request = loader.bootstrap
    expected_key = (
        "analytics/nvd/cve/schema_version=1/"
        "source_kind=bootstrap/"
        "projection_date=2026-08-22/"
        f"feed_revision={FEED_REVISION}.parquet"
    )
    repository = FakeProjectionRepository(
        copy_result=_projected(
            key=expected_key,
            source=request.silver_parquet,
        )
    )

    result = NvdAnalyticsProjectionServiceV1(
        evidence_loader=loader,
        repository=repository,
    ).project_bootstrap(
        silver_complete_key=request.silver_manifest.key,
        silver_complete_version_id=request.silver_manifest.version_id,
    )

    assert result.status == "projected"
    assert result.destination.object_key == expected_key
    assert loader.bootstrap_calls == [
        (
            request.silver_manifest.key,
            request.silver_manifest.version_id,
        )
    ]
    assert loader.incremental_calls == []


def test_repository_result_must_match_exact_authorized_source() -> None:
    """Reject repository evidence that escapes the deterministic destination contract."""
    loader = _loader()
    request = loader.incremental
    repository = FakeProjectionRepository(
        copy_result=NvdAnalyticsExactObjectRefV1(
            key="analytics/nvd/cve/wrong.parquet",
            version_id="analytics-version",
            sha256=request.silver_parquet.sha256,
            size_bytes=request.silver_parquet.size_bytes,
        )
    )

    with pytest.raises(
        InvalidNvdAnalyticsProjectionResultError,
        match="deterministic destination",
    ):
        NvdAnalyticsProjectionServiceV1(
            evidence_loader=loader,
            repository=repository,
        ).project_incremental(
            watermark_key="control/nvd/cve/incremental/watermark.json",
            watermark_version_id="watermark-version",
        )
