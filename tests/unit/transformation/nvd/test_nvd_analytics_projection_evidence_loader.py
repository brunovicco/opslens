"""Tests for exact NVD analytics projection evidence loading."""

import json
from datetime import UTC, datetime
from hashlib import sha256

import pytest

from opslens.ingestion.nvd.application.authoritative_watermark import (
    NvdAuthoritativeWatermarkSerializerV1,
    NvdAuthoritativeWatermarkV1,
    NvdWatermarkBootstrapRecoverySeedV1,
    NvdWatermarkEvidenceObjectV1,
    NvdWatermarkSilverPromotionCommitV1,
)
from opslens.transformation.nvd.application.analytics_projection_evidence_loader import (
    NVD_ANALYTICS_INCREMENTAL_WATERMARK_KEY,
    NVD_ANALYTICS_MAX_SILVER_COMPLETE_BYTES,
    NVD_ANALYTICS_MAX_WATERMARK_BYTES,
    InvalidNvdAnalyticsProjectionEvidenceError,
    NvdAnalyticsProjectionEvidenceLoaderV1,
    NvdAnalyticsProjectionNotEligibleError,
)
from opslens.transformation.nvd.completion.promotion import (
    NvdPersistedObjectPayloadV1,
)

UPDATE_ID = "a" * 64
LOGICAL_SHA = "b" * 64
PARQUET_SHA = "c" * 64
BRONZE_SHA = "d" * 64
FEED_REVISION = f"20260822T070013Z-{'e' * 64}"
START = datetime(2026, 8, 25, 21, 25, tzinfo=UTC)
END = datetime(2026, 8, 25, 23, 25, tzinfo=UTC)
INCREMENTAL_BASE = (
    "silver/nvd/cve/schema_version=1/"
    "source_kind=incremental/"
    f"update_id={UPDATE_ID}"
)
INCREMENTAL_MANIFEST_KEY = f"{INCREMENTAL_BASE}/manifest.json"
INCREMENTAL_MANIFEST_VERSION = "incremental-manifest-version"
INCREMENTAL_PARQUET_KEY = f"{INCREMENTAL_BASE}/part-00000.parquet"
INCREMENTAL_PARQUET_VERSION = "incremental-parquet-version"
BOOTSTRAP_BASE = (
    "silver/nvd/cve/schema_version=1/"
    "source_kind=bootstrap/feed_year=2026/"
    f"feed_revision={FEED_REVISION}"
)
BOOTSTRAP_MANIFEST_KEY = f"{BOOTSTRAP_BASE}/manifest.json"
BOOTSTRAP_MANIFEST_VERSION = "bootstrap-manifest-version"
BOOTSTRAP_PARQUET_KEY = f"{BOOTSTRAP_BASE}/part-00000.parquet"
BOOTSTRAP_PARQUET_VERSION = "bootstrap-parquet-version"


class FakeExactReader:
    """Return exact persisted payloads from explicit key/version coordinates."""

    def __init__(
        self,
        objects: dict[tuple[str, str], bytes],
    ) -> None:
        """Initialize deterministic exact objects."""
        self.objects = objects
        self.calls: list[tuple[str, str, int]] = []

    def read_exact(
        self,
        *,
        key: str,
        version_id: str,
        max_bytes: int,
    ) -> NvdPersistedObjectPayloadV1:
        """Return one configured exact persisted object."""
        self.calls.append((key, version_id, max_bytes))
        payload = self.objects[(key, version_id)]
        if len(payload) > max_bytes:
            raise AssertionError("fixture exceeds configured read bound")
        return NvdPersistedObjectPayloadV1(
            key=key,
            version_id=version_id,
            raw_bytes=payload,
        )


def _canonical(document: dict[str, object]) -> bytes:
    """Serialize one test document with the production canonical JSON shape."""
    text = json.dumps(
        document,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )
    return f"{text}\n".encode()


def _incremental_manifest(
    *,
    parquet_version: str = INCREMENTAL_PARQUET_VERSION,
    parquet_sha: str = PARQUET_SHA,
) -> bytes:
    """Build one canonical incremental Silver COMPLETE fixture."""
    document: dict[str, object] = {
        "bronze_manifest": {
            "key": "bronze/nvd/cve/updates/manifest.json",
            "sha256": BRONZE_SHA,
            "size_bytes": 1024,
            "version_id": "bronze-manifest-version",
        },
        "bronze_objects": [],
        "completion_status": "complete",
        "dataset": "nvd_cve_versions",
        "logical_record_set_sha256": LOGICAL_SHA,
        "manifest_version": "1",
        "schema_version": 1,
        "silver_object": {
            "key": INCREMENTAL_PARQUET_KEY,
            "row_count": 6749,
            "sha256": parquet_sha,
            "size_bytes": 4_724_916,
            "version_id": parquet_version,
        },
        "source_batch_id": UPDATE_ID,
        "source_coordinates": {
            "total_results": 6749,
            "update_id": UPDATE_ID,
            "window_end_at": "2026-08-25T23:25:00Z",
            "window_start_at": "2026-08-25T21:25:00Z",
        },
        "source_kind": "incremental",
        "warnings": [],
        "writer_contract_version": 1,
    }
    return _canonical(document)


def _watermark(
    *,
    manifest_bytes: bytes,
    parquet_version: str = INCREMENTAL_PARQUET_VERSION,
    parquet_sha: str = PARQUET_SHA,
) -> bytes:
    """Build one canonical authoritative Silver-promotion watermark."""
    watermark = NvdAuthoritativeWatermarkV1(
        committed_through_at=END,
        commit_basis=NvdWatermarkSilverPromotionCommitV1(
            previous_committed_through_at=START,
            update_id=UPDATE_ID,
            bronze_manifest=NvdWatermarkEvidenceObjectV1(
                key="bronze/nvd/cve/updates/manifest.json",
                version_id="bronze-manifest-version",
                sha256=BRONZE_SHA,
            ),
            silver_manifest=NvdWatermarkEvidenceObjectV1(
                key=INCREMENTAL_MANIFEST_KEY,
                version_id=INCREMENTAL_MANIFEST_VERSION,
                sha256=sha256(manifest_bytes).hexdigest(),
            ),
            silver_parquet=NvdWatermarkEvidenceObjectV1(
                key=INCREMENTAL_PARQUET_KEY,
                version_id=parquet_version,
                sha256=parquet_sha,
            ),
            logical_record_set_sha256=LOGICAL_SHA,
        ),
    )
    return NvdAuthoritativeWatermarkSerializerV1().serialize(
        watermark
    )


def _bootstrap_manifest(
    *,
    source_observed_at: str = "2026-08-22T07:00:13Z",
) -> bytes:
    """Build one canonical Bootstrap Silver COMPLETE fixture."""
    document: dict[str, object] = {
        "bronze_manifest": {
            "key": "bronze/nvd/cve/bootstrap/manifest.json",
            "sha256": BRONZE_SHA,
            "size_bytes": 1024,
            "version_id": "bronze-bootstrap-manifest-version",
        },
        "bronze_objects": [],
        "completion_status": "complete",
        "dataset": "nvd_cve_versions",
        "logical_record_set_sha256": LOGICAL_SHA,
        "manifest_version": "1",
        "schema_version": 1,
        "silver_object": {
            "key": BOOTSTRAP_PARQUET_KEY,
            "row_count": 48_293,
            "sha256": PARQUET_SHA,
            "size_bytes": 36_240_684,
            "version_id": BOOTSTRAP_PARQUET_VERSION,
        },
        "source_batch_id": (
            f"feed_year=2026/feed_revision={FEED_REVISION}"
        ),
        "source_coordinates": {
            "feed_revision": FEED_REVISION,
            "feed_year": 2026,
            "source_observed_at": source_observed_at,
        },
        "source_kind": "bootstrap",
        "warnings": [],
        "writer_contract_version": 1,
    }
    return _canonical(document)


def test_load_incremental_binds_exact_watermark_to_silver_complete() -> None:
    """Derive eligibility only from exact watermark and COMPLETE versions."""
    manifest = _incremental_manifest()
    watermark = _watermark(manifest_bytes=manifest)
    reader = FakeExactReader(
        {
            (
                NVD_ANALYTICS_INCREMENTAL_WATERMARK_KEY,
                "watermark-version",
            ): watermark,
            (
                INCREMENTAL_MANIFEST_KEY,
                INCREMENTAL_MANIFEST_VERSION,
            ): manifest,
        }
    )

    result = NvdAnalyticsProjectionEvidenceLoaderV1(
        object_reader=reader
    ).load_incremental(
        watermark_key=NVD_ANALYTICS_INCREMENTAL_WATERMARK_KEY,
        watermark_version_id="watermark-version",
    )

    assert result.update_id == UPDATE_ID
    assert result.committed_through_at == END
    assert result.row_count == 6749
    assert result.logical_record_set_sha256 == LOGICAL_SHA
    assert result.silver_manifest.sha256 == sha256(manifest).hexdigest()
    assert result.silver_parquet.key == INCREMENTAL_PARQUET_KEY
    assert result.silver_parquet.version_id == INCREMENTAL_PARQUET_VERSION
    assert result.silver_parquet.sha256 == PARQUET_SHA
    assert reader.calls == [
        (
            NVD_ANALYTICS_INCREMENTAL_WATERMARK_KEY,
            "watermark-version",
            NVD_ANALYTICS_MAX_WATERMARK_BYTES,
        ),
        (
            INCREMENTAL_MANIFEST_KEY,
            INCREMENTAL_MANIFEST_VERSION,
            NVD_ANALYTICS_MAX_SILVER_COMPLETE_BYTES,
        ),
    ]


def test_load_incremental_rejects_bootstrap_recovery_watermark() -> None:
    """Do not treat a valid recovery seed as incremental analytics authority."""
    watermark = NvdAuthoritativeWatermarkV1(
        committed_through_at=END,
        commit_basis=NvdWatermarkBootstrapRecoverySeedV1(
            source_revision_at=END,
            bootstrap_manifest=NvdWatermarkEvidenceObjectV1(
                key="bronze/nvd/cve/bootstrap/manifest.json",
                version_id="bootstrap-version",
                sha256=BRONZE_SHA,
            ),
        ),
    )
    payload = NvdAuthoritativeWatermarkSerializerV1().serialize(
        watermark
    )
    reader = FakeExactReader(
        {
            (
                NVD_ANALYTICS_INCREMENTAL_WATERMARK_KEY,
                "watermark-version",
            ): payload,
        }
    )

    with pytest.raises(
        NvdAnalyticsProjectionNotEligibleError,
        match="silver_complete_promotion",
    ):
        NvdAnalyticsProjectionEvidenceLoaderV1(
            object_reader=reader
        ).load_incremental(
            watermark_key=NVD_ANALYTICS_INCREMENTAL_WATERMARK_KEY,
            watermark_version_id="watermark-version",
        )


def test_load_incremental_rejects_manifest_hash_mismatch() -> None:
    """Fail closed when exact COMPLETE bytes disagree with watermark SHA-256."""
    authorized_manifest = _incremental_manifest()
    returned_manifest = _incremental_manifest(
        parquet_sha="f" * 64
    )
    reader = FakeExactReader(
        {
            (
                NVD_ANALYTICS_INCREMENTAL_WATERMARK_KEY,
                "watermark-version",
            ): _watermark(
                manifest_bytes=authorized_manifest
            ),
            (
                INCREMENTAL_MANIFEST_KEY,
                INCREMENTAL_MANIFEST_VERSION,
            ): returned_manifest,
        }
    )

    with pytest.raises(
        InvalidNvdAnalyticsProjectionEvidenceError,
        match="SHA-256 does not match watermark",
    ):
        NvdAnalyticsProjectionEvidenceLoaderV1(
            object_reader=reader
        ).load_incremental(
            watermark_key=NVD_ANALYTICS_INCREMENTAL_WATERMARK_KEY,
            watermark_version_id="watermark-version",
        )


def test_load_incremental_rejects_parquet_evidence_mismatch() -> None:
    """Require COMPLETE Parquet coordinates to equal watermark authority."""
    manifest = _incremental_manifest(
        parquet_version="different-parquet-version"
    )
    reader = FakeExactReader(
        {
            (
                NVD_ANALYTICS_INCREMENTAL_WATERMARK_KEY,
                "watermark-version",
            ): _watermark(
                manifest_bytes=manifest,
                parquet_version=INCREMENTAL_PARQUET_VERSION,
            ),
            (
                INCREMENTAL_MANIFEST_KEY,
                INCREMENTAL_MANIFEST_VERSION,
            ): manifest,
        }
    )

    with pytest.raises(
        InvalidNvdAnalyticsProjectionEvidenceError,
        match="Parquet evidence does not match",
    ):
        NvdAnalyticsProjectionEvidenceLoaderV1(
            object_reader=reader
        ).load_incremental(
            watermark_key=NVD_ANALYTICS_INCREMENTAL_WATERMARK_KEY,
            watermark_version_id="watermark-version",
        )


def test_load_bootstrap_derives_exact_seed_from_complete() -> None:
    """Derive Bootstrap eligibility from one explicit exact COMPLETE version."""
    manifest = _bootstrap_manifest()
    reader = FakeExactReader(
        {
            (
                BOOTSTRAP_MANIFEST_KEY,
                BOOTSTRAP_MANIFEST_VERSION,
            ): manifest,
        }
    )

    result = NvdAnalyticsProjectionEvidenceLoaderV1(
        object_reader=reader
    ).load_bootstrap(
        silver_complete_key=BOOTSTRAP_MANIFEST_KEY,
        silver_complete_version_id=BOOTSTRAP_MANIFEST_VERSION,
    )

    assert result.feed_year == 2026
    assert result.feed_revision == FEED_REVISION
    assert result.source_observed_at == datetime(
        2026,
        8,
        22,
        7,
        0,
        13,
        tzinfo=UTC,
    )
    assert result.row_count == 48_293
    assert result.silver_parquet.version_id == BOOTSTRAP_PARQUET_VERSION
    assert result.silver_parquet.sha256 == PARQUET_SHA
    assert result.silver_manifest.sha256 == sha256(manifest).hexdigest()


def test_load_bootstrap_rejects_noncanonical_complete_bytes() -> None:
    """Reject semantically valid JSON that is not exact canonical COMPLETE."""
    manifest = b" " + _bootstrap_manifest()
    reader = FakeExactReader(
        {
            (
                BOOTSTRAP_MANIFEST_KEY,
                BOOTSTRAP_MANIFEST_VERSION,
            ): manifest,
        }
    )

    with pytest.raises(
        InvalidNvdAnalyticsProjectionEvidenceError,
        match="not canonical",
    ):
        NvdAnalyticsProjectionEvidenceLoaderV1(
            object_reader=reader
        ).load_bootstrap(
            silver_complete_key=BOOTSTRAP_MANIFEST_KEY,
            silver_complete_version_id=BOOTSTRAP_MANIFEST_VERSION,
        )


def test_load_bootstrap_rejects_noncanonical_source_timestamp() -> None:
    """Require the canonical Z-form source timestamp emitted by Silver."""
    manifest = _bootstrap_manifest(
        source_observed_at="2026-08-22T07:00:13+00:00"
    )
    reader = FakeExactReader(
        {
            (
                BOOTSTRAP_MANIFEST_KEY,
                BOOTSTRAP_MANIFEST_VERSION,
            ): manifest,
        }
    )

    with pytest.raises(
        InvalidNvdAnalyticsProjectionEvidenceError,
        match="canonical UTC",
    ):
        NvdAnalyticsProjectionEvidenceLoaderV1(
            object_reader=reader
        ).load_bootstrap(
            silver_complete_key=BOOTSTRAP_MANIFEST_KEY,
            silver_complete_version_id=BOOTSTRAP_MANIFEST_VERSION,
        )
