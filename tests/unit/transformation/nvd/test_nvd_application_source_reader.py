"""Tests for deterministic NVD Silver source-batch reading."""

import gzip
import json
from datetime import UTC, datetime
from hashlib import sha256

import pytest

from opslens.transformation.nvd.application.source_reader import (
    NvdSilverSourceBatchReaderV1,
    NvdSilverSourceReadError,
)
from opslens.transformation.nvd.provenance.models import (
    NvdBronzeObjectPayloadV1,
    NvdBronzeObjectReferenceV1,
    NvdBronzeObjectRole,
    VerifiedNvdBronzeEvidenceV1,
)
from opslens.transformation.nvd.serialization.models import (
    NvdSilverSourceKind,
)


def _json_bytes(
    vulnerabilities: list[dict[str, object]],
) -> bytes:
    return json.dumps(
        {"vulnerabilities": vulnerabilities},
        separators=(",", ":"),
    ).encode("utf-8")


def _wrapped_cve(cve_id: str) -> dict[str, object]:
    return {
        "cve": {
            "id": cve_id,
        }
    }


def _reference(
    *,
    role: NvdBronzeObjectRole,
    key: str,
    version_id: str,
    raw_bytes: bytes,
    page_start: int | None = None,
    source_timestamp: str | None = None,
) -> NvdBronzeObjectReferenceV1:
    return NvdBronzeObjectReferenceV1(
        role=role,
        key=key,
        version_id=version_id,
        size_bytes=len(raw_bytes),
        sha256=sha256(raw_bytes).hexdigest(),
        page_start=page_start,
        source_timestamp=source_timestamp,
    )


def test_reads_bootstrap_feed_and_preserves_local_record_indexes() -> None:
    """Read yearly-feed CVEs from the verified gzip object."""
    source_bytes = _json_bytes(
        [
            _wrapped_cve("CVE-2026-1000"),
            _wrapped_cve("CVE-2026-1001"),
        ]
    )
    feed_bytes = gzip.compress(
        source_bytes,
        mtime=0,
    )
    meta_bytes = b"lastModifiedDate:2026-08-18T07:00:12Z\n"

    feed_key = "bronze/nvd/bootstrap/feed.json.gz"
    meta_key = "bronze/nvd/bootstrap/feed.meta"

    feed_reference = _reference(
        role=NvdBronzeObjectRole.FEED,
        key=feed_key,
        version_id="feed-version-1",
        raw_bytes=feed_bytes,
    )
    meta_reference = _reference(
        role=NvdBronzeObjectRole.META,
        key=meta_key,
        version_id="meta-version-1",
        raw_bytes=meta_bytes,
    )

    evidence = VerifiedNvdBronzeEvidenceV1(
        source_kind=NvdSilverSourceKind.BOOTSTRAP,
        source_batch_id="feed_year=2026/feed_revision=revision-1",
        manifest_key=(
            "bronze/nvd/cve/bootstrap/feed_year=2026/feed_revision=revision-1/manifest.json"
        ),
        manifest_version_id="manifest-version-1",
        manifest_sha256="a" * 64,
        manifest_size_bytes=100,
        objects=(
            feed_reference,
            meta_reference,
        ),
        bootstrap_feed_year=2026,
        bootstrap_feed_revision="revision-1",
        bootstrap_source_observed_at=datetime(
            2026,
            8,
            18,
            7,
            tzinfo=UTC,
        ),
        incremental_update_id=None,
        incremental_total_results=None,
        incremental_window_start_at=None,
        incremental_window_end_at=None,
    )

    records = NvdSilverSourceBatchReaderV1().read(
        evidence=evidence,
        object_payloads=(
            NvdBronzeObjectPayloadV1(
                key=feed_key,
                version_id="feed-version-1",
                raw_bytes=feed_bytes,
            ),
            NvdBronzeObjectPayloadV1(
                key=meta_key,
                version_id="meta-version-1",
                raw_bytes=meta_bytes,
            ),
        ),
    )

    assert [record.record_index for record in records] == [0, 1]
    assert all(record.bronze_object_key == feed_key for record in records)
    assert [record.source_cve["id"] for record in records] == [
        "CVE-2026-1000",
        "CVE-2026-1001",
    ]


def test_reads_incremental_pages_with_object_local_indexes() -> None:
    """Restart record indexes for each exact Bronze page object."""
    update_id = "b" * 64

    first_bytes = _json_bytes(
        [
            _wrapped_cve("CVE-2026-2000"),
            _wrapped_cve("CVE-2026-2001"),
        ]
    )
    second_bytes = _json_bytes(
        [
            _wrapped_cve("CVE-2026-2002"),
        ]
    )

    first_key = "bronze/nvd/page-000000.json"
    second_key = "bronze/nvd/page-000002.json"

    first_reference = _reference(
        role=NvdBronzeObjectRole.PAGE,
        key=first_key,
        version_id="page-version-1",
        raw_bytes=first_bytes,
        page_start=0,
        source_timestamp="2026-08-21T12:00:00.000",
    )
    second_reference = _reference(
        role=NvdBronzeObjectRole.PAGE,
        key=second_key,
        version_id="page-version-2",
        raw_bytes=second_bytes,
        page_start=2,
        source_timestamp="2026-08-21T12:00:01.000",
    )

    evidence = VerifiedNvdBronzeEvidenceV1(
        source_kind=NvdSilverSourceKind.INCREMENTAL,
        source_batch_id=update_id,
        manifest_key=f"bronze/nvd/cve/updates/update_id={update_id}/manifest.json",
        manifest_version_id="manifest-version-1",
        manifest_sha256="c" * 64,
        manifest_size_bytes=100,
        objects=(
            first_reference,
            second_reference,
        ),
        bootstrap_feed_year=None,
        bootstrap_feed_revision=None,
        bootstrap_source_observed_at=None,
        incremental_update_id=update_id,
        incremental_total_results=3,
        incremental_window_start_at=datetime(
            2026,
            8,
            20,
            tzinfo=UTC,
        ),
        incremental_window_end_at=datetime(
            2026,
            8,
            21,
            tzinfo=UTC,
        ),
    )

    records = NvdSilverSourceBatchReaderV1().read(
        evidence=evidence,
        object_payloads=(
            NvdBronzeObjectPayloadV1(
                key=first_key,
                version_id="page-version-1",
                raw_bytes=first_bytes,
            ),
            NvdBronzeObjectPayloadV1(
                key=second_key,
                version_id="page-version-2",
                raw_bytes=second_bytes,
            ),
        ),
    )

    assert [(record.bronze_object_key, record.record_index) for record in records] == [
        (first_key, 0),
        (first_key, 1),
        (second_key, 0),
    ]


def test_reads_zero_result_incremental_page() -> None:
    """Preserve the frozen zero-result incremental contract."""
    update_id = "d" * 64
    page_bytes = _json_bytes([])
    page_key = "bronze/nvd/empty-page.json"

    reference = _reference(
        role=NvdBronzeObjectRole.PAGE,
        key=page_key,
        version_id="page-version-1",
        raw_bytes=page_bytes,
        page_start=0,
        source_timestamp="2026-08-21T12:00:00.000",
    )

    evidence = VerifiedNvdBronzeEvidenceV1(
        source_kind=NvdSilverSourceKind.INCREMENTAL,
        source_batch_id=update_id,
        manifest_key=f"bronze/nvd/cve/updates/update_id={update_id}/manifest.json",
        manifest_version_id="manifest-version-1",
        manifest_sha256="e" * 64,
        manifest_size_bytes=100,
        objects=(reference,),
        bootstrap_feed_year=None,
        bootstrap_feed_revision=None,
        bootstrap_source_observed_at=None,
        incremental_update_id=update_id,
        incremental_total_results=0,
        incremental_window_start_at=datetime(
            2026,
            8,
            20,
            tzinfo=UTC,
        ),
        incremental_window_end_at=datetime(
            2026,
            8,
            21,
            tzinfo=UTC,
        ),
    )

    records = NvdSilverSourceBatchReaderV1().read(
        evidence=evidence,
        object_payloads=(
            NvdBronzeObjectPayloadV1(
                key=page_key,
                version_id="page-version-1",
                raw_bytes=page_bytes,
            ),
        ),
    )

    assert records == ()


def test_rejects_invalid_bootstrap_gzip() -> None:
    """Fail closed when verified source coordinates cannot be decoded."""
    feed_bytes = b"not-gzip"
    meta_bytes = b"meta"

    feed_reference = _reference(
        role=NvdBronzeObjectRole.FEED,
        key="feed",
        version_id="feed-v1",
        raw_bytes=feed_bytes,
    )
    meta_reference = _reference(
        role=NvdBronzeObjectRole.META,
        key="meta",
        version_id="meta-v1",
        raw_bytes=meta_bytes,
    )

    evidence = VerifiedNvdBronzeEvidenceV1(
        source_kind=NvdSilverSourceKind.BOOTSTRAP,
        source_batch_id="feed_year=2026/feed_revision=r1",
        manifest_key="bootstrap/feed_year=2026/feed_revision=r1/manifest.json",
        manifest_version_id="manifest-v1",
        manifest_sha256="f" * 64,
        manifest_size_bytes=1,
        objects=(
            feed_reference,
            meta_reference,
        ),
        bootstrap_feed_year=2026,
        bootstrap_feed_revision="r1",
        bootstrap_source_observed_at=datetime(
            2026,
            8,
            18,
            tzinfo=UTC,
        ),
        incremental_update_id=None,
        incremental_total_results=None,
        incremental_window_start_at=None,
        incremental_window_end_at=None,
    )

    with pytest.raises(
        NvdSilverSourceReadError,
        match="gzip",
    ):
        NvdSilverSourceBatchReaderV1().read(
            evidence=evidence,
            object_payloads=(
                NvdBronzeObjectPayloadV1(
                    key="feed",
                    version_id="feed-v1",
                    raw_bytes=feed_bytes,
                ),
                NvdBronzeObjectPayloadV1(
                    key="meta",
                    version_id="meta-v1",
                    raw_bytes=meta_bytes,
                ),
            ),
        )


def test_rejects_incremental_page_cardinality_mismatch() -> None:
    """Do not silently accept page content inconsistent with Bronze evidence."""
    update_id = "1" * 64
    page_bytes = _json_bytes(
        [
            _wrapped_cve("CVE-2026-3000"),
        ]
    )
    page_key = "bronze/nvd/page.json"

    reference = _reference(
        role=NvdBronzeObjectRole.PAGE,
        key=page_key,
        version_id="page-v1",
        raw_bytes=page_bytes,
        page_start=0,
        source_timestamp="2026-08-21T12:00:00.000",
    )

    evidence = VerifiedNvdBronzeEvidenceV1(
        source_kind=NvdSilverSourceKind.INCREMENTAL,
        source_batch_id=update_id,
        manifest_key=f"bronze/nvd/cve/updates/update_id={update_id}/manifest.json",
        manifest_version_id="manifest-v1",
        manifest_sha256="2" * 64,
        manifest_size_bytes=1,
        objects=(reference,),
        bootstrap_feed_year=None,
        bootstrap_feed_revision=None,
        bootstrap_source_observed_at=None,
        incremental_update_id=update_id,
        incremental_total_results=2,
        incremental_window_start_at=datetime(
            2026,
            8,
            20,
            tzinfo=UTC,
        ),
        incremental_window_end_at=datetime(
            2026,
            8,
            21,
            tzinfo=UTC,
        ),
    )

    with pytest.raises(
        NvdSilverSourceReadError,
        match="CVE count",
    ):
        NvdSilverSourceBatchReaderV1().read(
            evidence=evidence,
            object_payloads=(
                NvdBronzeObjectPayloadV1(
                    key=page_key,
                    version_id="page-v1",
                    raw_bytes=page_bytes,
                ),
            ),
        )
