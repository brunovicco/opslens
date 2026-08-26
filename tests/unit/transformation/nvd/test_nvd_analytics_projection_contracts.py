"""Tests for permanent NVD analytics projection contracts and keys."""

from datetime import UTC, datetime, timedelta, timezone

import pytest

from opslens.transformation.nvd.application.analytics_projection_key_factory import (
    NvdAnalyticsProjectionKeyFactoryV1,
)
from opslens.transformation.nvd.application.analytics_projection_models import (
    NvdAnalyticsExactObjectRefV1,
    NvdBootstrapAnalyticsProjectionRequestV1,
    NvdIncrementalAnalyticsProjectionRequestV1,
    parse_nvd_bootstrap_feed_revision,
)
from opslens.transformation.nvd.serialization.models import (
    NvdSilverSourceKind,
)

UPDATE_ID = "a" * 64
LOGICAL_SHA = "b" * 64
PARQUET_SHA = "c" * 64
MANIFEST_SHA = "d" * 64
FEED_REVISION = f"20260822T070013Z-{'e' * 64}"


def _exact_ref(
    *,
    key: str,
    sha256: str,
    size_bytes: int,
    version_id: str,
) -> NvdAnalyticsExactObjectRefV1:
    """Build one exact persisted-object reference."""
    return NvdAnalyticsExactObjectRefV1(
        key=key,
        version_id=version_id,
        sha256=sha256,
        size_bytes=size_bytes,
    )


def _incremental_request(
    *,
    committed_through_at: datetime | None = None,
) -> NvdIncrementalAnalyticsProjectionRequestV1:
    """Build one valid incremental analytics request."""
    base = (
        "silver/nvd/cve/schema_version=1/"
        "source_kind=incremental/"
        f"update_id={UPDATE_ID}"
    )

    return NvdIncrementalAnalyticsProjectionRequestV1(
        update_id=UPDATE_ID,
        committed_through_at=(
            committed_through_at
            if committed_through_at is not None
            else datetime(2026, 8, 25, 23, 25, tzinfo=UTC)
        ),
        silver_manifest=_exact_ref(
            key=f"{base}/manifest.json",
            version_id="incremental-manifest-version",
            sha256=MANIFEST_SHA,
            size_bytes=2048,
        ),
        silver_parquet=_exact_ref(
            key=f"{base}/part-00000.parquet",
            version_id="incremental-parquet-version",
            sha256=PARQUET_SHA,
            size_bytes=4_724_916,
        ),
        row_count=6749,
        logical_record_set_sha256=LOGICAL_SHA,
    )


def _bootstrap_request() -> NvdBootstrapAnalyticsProjectionRequestV1:
    """Build one valid Bootstrap analytics request."""
    base = (
        "silver/nvd/cve/schema_version=1/"
        "source_kind=bootstrap/"
        "feed_year=2026/"
        f"feed_revision={FEED_REVISION}"
    )

    return NvdBootstrapAnalyticsProjectionRequestV1(
        feed_year=2026,
        feed_revision=FEED_REVISION,
        source_observed_at=datetime(2026, 8, 22, 7, 0, 13, tzinfo=UTC),
        silver_manifest=_exact_ref(
            key=f"{base}/manifest.json",
            version_id="bootstrap-manifest-version",
            sha256=MANIFEST_SHA,
            size_bytes=1947,
        ),
        silver_parquet=_exact_ref(
            key=f"{base}/part-00000.parquet",
            version_id="bootstrap-parquet-version",
            sha256=PARQUET_SHA,
            size_bytes=36_240_684,
        ),
        row_count=48_293,
        logical_record_set_sha256=LOGICAL_SHA,
    )


def test_exact_object_reference_requires_lowercase_sha256() -> None:
    """Reject an exact object reference without canonical SHA-256 evidence."""
    with pytest.raises(ValueError, match="SHA-256"):
        _exact_ref(
            key="silver/example.parquet",
            version_id="version-1",
            sha256="NOT-A-SHA",
            size_bytes=1,
        )


def test_incremental_request_normalizes_timestamp_and_derives_utc_date() -> None:
    """Use the committed UTC instant rather than the caller's local date."""
    sao_paulo = timezone(-timedelta(hours=3))
    request = _incremental_request(
        committed_through_at=datetime(
            2026,
            8,
            25,
            22,
            30,
            tzinfo=sao_paulo,
        )
    )

    assert request.committed_through_at == datetime(
        2026,
        8,
        26,
        1,
        30,
        tzinfo=UTC,
    )
    assert request.projection_date.isoformat() == "2026-08-26"
    assert request.source_kind is NvdSilverSourceKind.INCREMENTAL
    assert request.authority_state == "watermark_committed"
    assert request.source_batch_id == UPDATE_ID


def test_incremental_request_rejects_invalid_update_id() -> None:
    """Reject incremental analytics authority without canonical batch identity."""
    valid = _incremental_request()

    with pytest.raises(ValueError, match="update_id"):
        NvdIncrementalAnalyticsProjectionRequestV1(
            update_id="not-a-sha256",
            committed_through_at=valid.committed_through_at,
            silver_manifest=valid.silver_manifest,
            silver_parquet=valid.silver_parquet,
            row_count=valid.row_count,
            logical_record_set_sha256=valid.logical_record_set_sha256,
        )


def test_incremental_request_rejects_naive_committed_boundary() -> None:
    """Require explicit timezone evidence before deriving a projection date."""
    valid = _incremental_request()

    with pytest.raises(ValueError, match="timezone-aware"):
        NvdIncrementalAnalyticsProjectionRequestV1(
            update_id=valid.update_id,
            committed_through_at=datetime(2026, 8, 25, 23, 25),
            silver_manifest=valid.silver_manifest,
            silver_parquet=valid.silver_parquet,
            row_count=valid.row_count,
            logical_record_set_sha256=valid.logical_record_set_sha256,
        )


def test_incremental_request_rejects_non_deterministic_silver_key() -> None:
    """Fail closed when exact Silver coordinates do not belong to update_id."""
    valid = _incremental_request()

    with pytest.raises(ValueError, match="Silver Parquet key is not deterministic"):
        NvdIncrementalAnalyticsProjectionRequestV1(
            update_id=valid.update_id,
            committed_through_at=valid.committed_through_at,
            silver_manifest=valid.silver_manifest,
            silver_parquet=_exact_ref(
                key="silver/nvd/cve/wrong.parquet",
                version_id=valid.silver_parquet.version_id,
                sha256=valid.silver_parquet.sha256,
                size_bytes=valid.silver_parquet.size_bytes,
            ),
            row_count=valid.row_count,
            logical_record_set_sha256=valid.logical_record_set_sha256,
        )


def test_bootstrap_request_derives_partition_date_from_feed_revision() -> None:
    """Keep Bootstrap partition identity tied to its deterministic revision."""
    request = _bootstrap_request()

    assert request.projection_date.isoformat() == "2026-08-22"
    assert request.source_kind is NvdSilverSourceKind.BOOTSTRAP
    assert request.authority_state == "bootstrap_verified_seed"
    assert request.source_batch_id == (
        f"feed_year=2026/feed_revision={FEED_REVISION}"
    )


def test_bootstrap_request_rejects_non_canonical_revision() -> None:
    """Reject Bootstrap revisions that cannot deterministically yield a date."""
    with pytest.raises(ValueError, match="feed_revision"):
        parse_nvd_bootstrap_feed_revision("2026-08-22-not-canonical")


def test_bootstrap_request_rejects_feed_year_mismatch() -> None:
    """Require the declared feed year to agree with the revision timestamp."""
    valid = _bootstrap_request()

    with pytest.raises(ValueError, match="feed_year must match"):
        NvdBootstrapAnalyticsProjectionRequestV1(
            feed_year=2025,
            feed_revision=valid.feed_revision,
            source_observed_at=valid.source_observed_at,
            silver_manifest=valid.silver_manifest,
            silver_parquet=valid.silver_parquet,
            row_count=valid.row_count,
            logical_record_set_sha256=valid.logical_record_set_sha256,
        )


def test_bootstrap_request_requires_positive_rows() -> None:
    """Preserve the existing Bootstrap Silver non-empty completion invariant."""
    valid = _bootstrap_request()

    with pytest.raises(ValueError, match="row_count"):
        NvdBootstrapAnalyticsProjectionRequestV1(
            feed_year=valid.feed_year,
            feed_revision=valid.feed_revision,
            source_observed_at=valid.source_observed_at,
            silver_manifest=valid.silver_manifest,
            silver_parquet=valid.silver_parquet,
            row_count=0,
            logical_record_set_sha256=valid.logical_record_set_sha256,
        )


def test_incremental_key_is_deterministic_and_partition_friendly() -> None:
    """Build the selected permanent incremental analytics layout."""
    key = NvdAnalyticsProjectionKeyFactoryV1().build(
        _incremental_request()
    )

    assert key.object_key == (
        "analytics/nvd/cve/schema_version=1/"
        "source_kind=incremental/"
        "projection_date=2026-08-25/"
        f"update_id={UPDATE_ID}.parquet"
    )
    assert key.source_kind_partition == "incremental"
    assert key.projection_date == "2026-08-25"


def test_bootstrap_key_is_deterministic_and_partition_friendly() -> None:
    """Build the selected permanent Bootstrap analytics layout."""
    key = NvdAnalyticsProjectionKeyFactoryV1().build(
        _bootstrap_request()
    )

    assert key.object_key == (
        "analytics/nvd/cve/schema_version=1/"
        "source_kind=bootstrap/"
        "projection_date=2026-08-22/"
        f"feed_revision={FEED_REVISION}.parquet"
    )
    assert key.source_kind_partition == "bootstrap"
    assert key.projection_date == "2026-08-22"


def test_key_factory_accepts_explicit_non_empty_prefix() -> None:
    """Keep the pure factory reusable without weakening deterministic layout."""
    key = NvdAnalyticsProjectionKeyFactoryV1(
        "/analytics-test/nvd/cve/",
    ).build(_incremental_request())

    assert key.object_key.startswith("analytics-test/nvd/cve/")


def test_key_factory_rejects_empty_prefix() -> None:
    """Reject a destination root that would erase the analytics boundary."""
    with pytest.raises(ValueError, match="prefix"):
        NvdAnalyticsProjectionKeyFactoryV1("///")
