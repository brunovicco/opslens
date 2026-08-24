"""Unit tests for the NVD incremental COMPLETE manifest."""

import json
from datetime import UTC, datetime
from typing import cast

import pytest

from opslens.ingestion.nvd.application.incremental_key_factory import (
    NvdIncrementalKeyFactory,
)
from opslens.ingestion.nvd.application.incremental_manifest import (
    NvdIncrementalManifestFactory,
    NvdIncrementalManifestSerializer,
)
from opslens.ingestion.nvd.application.models import (
    NvdBronzeWriteResult,
    NvdBronzeWriteStatus,
)
from opslens.ingestion.nvd.domain.api_page import (
    NvdCveApiPage,
    NvdCveApiPageParser,
    NvdCveApiPagination,
)
from opslens.ingestion.nvd.domain.incremental import (
    NvdIncrementalWindow,
)


def _window() -> NvdIncrementalWindow:
    """Build one deterministic incremental window."""
    return NvdIncrementalWindow(
        start_at=datetime(
            2026,
            8,
            18,
            18,
            0,
            tzinfo=UTC,
        ),
        end_at=datetime(
            2026,
            8,
            18,
            20,
            0,
            tzinfo=UTC,
        ),
    )


def _page(
    *,
    start_index: int,
    total_results: int,
    cve_ids: tuple[str, ...],
    timestamp: str,
) -> NvdCveApiPage:
    """Build one validated deterministic NVD response page."""
    document: dict[str, object] = {
        "resultsPerPage": len(cve_ids),
        "startIndex": start_index,
        "totalResults": total_results,
        "format": "NVD_CVE",
        "version": "2.0",
        "timestamp": timestamp,
        "vulnerabilities": [
            {
                "cve": {
                    "id": cve_id,
                }
            }
            for cve_id in cve_ids
        ],
    }

    payload = json.dumps(
        document,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()

    return NvdCveApiPageParser().parse(payload)


def _pagination() -> NvdCveApiPagination:
    """Build one complete three-page source sequence."""
    return NvdCveApiPagination(
        pages=(
            _page(
                start_index=0,
                total_results=5,
                cve_ids=(
                    "CVE-2026-1000",
                    "CVE-2026-1001",
                ),
                timestamp=("2026-08-18T20:00:01.000"),
            ),
            _page(
                start_index=2,
                total_results=5,
                cve_ids=(
                    "CVE-2026-1002",
                    "CVE-2026-1003",
                ),
                timestamp=("2026-08-18T20:00:07.000"),
            ),
            _page(
                start_index=4,
                total_results=5,
                cve_ids=("CVE-2026-1004",),
                timestamp=("2026-08-18T20:00:13.000"),
            ),
        )
    )


def _writes() -> tuple[
    NvdBronzeWriteResult,
    ...,
]:
    """Build exact S3 persistence evidence in page order."""
    return (
        NvdBronzeWriteResult(
            status=NvdBronzeWriteStatus.CREATED,
            version_id="page-version-0",
        ),
        NvdBronzeWriteResult(
            status=(NvdBronzeWriteStatus.ALREADY_EXISTS),
            version_id="page-version-2",
        ),
        NvdBronzeWriteResult(
            status=NvdBronzeWriteStatus.CREATED,
            version_id="page-version-4",
        ),
    )


def _page_keys() -> tuple[str, ...]:
    """Build exact attempt-scoped persisted page keys in source order."""
    window = _window()
    factory = NvdIncrementalKeyFactory()
    attempt_id = "a" * 64

    return tuple(
        factory.build_attempt_page_key(
            window=window,
            attempt_id=attempt_id,
            start_index=page.start_index,
        )
        for page in _pagination().pages
    )


def _manifest():
    """Build one valid COMPLETE incremental manifest."""
    return NvdIncrementalManifestFactory().build(
        window=_window(),
        pagination=_pagination(),
        page_keys=_page_keys(),
        page_writes=_writes(),
    )


def test_manifest_binds_exact_page_version_ids() -> None:
    """Bind every source page to an exact immutable S3 version."""
    manifest = _manifest()

    assert tuple(page.version_id for page in manifest.pages) == (
        "page-version-0",
        "page-version-2",
        "page-version-4",
    )


def test_manifest_binds_exact_page_hashes_and_sizes() -> None:
    """Bind each persisted response to exact byte evidence."""
    pagination = _pagination()

    manifest = NvdIncrementalManifestFactory().build(
        window=_window(),
        pagination=pagination,
        page_keys=_page_keys(),
        page_writes=_writes(),
    )

    assert tuple(page.sha256 for page in manifest.pages) == tuple(
        page.sha256 for page in pagination.pages
    )

    assert tuple(page.size_bytes for page in manifest.pages) == tuple(
        len(page.raw_bytes) for page in pagination.pages
    )


def test_manifest_binds_exact_persisted_page_keys() -> None:
    """Bind COMPLETE evidence to the exact physical page keys supplied."""
    window = _window()
    manifest = _manifest()
    factory = NvdIncrementalKeyFactory()

    assert tuple(
        page.key
        for page in manifest.pages
    ) == _page_keys()

    assert all(
        "/attempt_id=" in page.key
        for page in manifest.pages
    )

    assert factory.build_manifest_key(window=window) == (
        f"bronze/nvd/cve/updates/update_id={window.update_id}/manifest.json"
    )


def test_manifest_marks_complete_run() -> None:
    """Serialize explicit COMPLETE run evidence."""
    payload = NvdIncrementalManifestSerializer().serialize(_manifest())

    document = cast(
        dict[str, object],
        json.loads(payload),
    )

    assert document["completion_status"] == "complete"
    assert document["manifest_version"] == "1"
    assert document["source"] == "nvd-cve"
    assert document["source_interface"] == "cve-api-2.0"
    assert document["source_format"] == "NVD_CVE"
    assert document["source_version"] == "2.0"
    assert document["page_count"] == 3
    assert document["total_results"] == 5


def test_manifest_serializer_is_deterministic() -> None:
    """Produce identical bytes for identical evidence."""
    serializer = NvdIncrementalManifestSerializer()
    manifest = _manifest()

    assert serializer.serialize(manifest) == serializer.serialize(manifest)


def test_manifest_rebuild_is_retry_stable() -> None:
    """Exclude persistence outcome and runtime clock from identity."""
    factory = NvdIncrementalManifestFactory()
    serializer = NvdIncrementalManifestSerializer()

    first_writes = _writes()

    replay_writes = tuple(
        NvdBronzeWriteResult(
            status=(NvdBronzeWriteStatus.ALREADY_EXISTS),
            version_id=write.version_id,
        )
        for write in first_writes
    )

    first = factory.build(
        window=_window(),
        pagination=_pagination(),
        page_keys=_page_keys(),
        page_writes=first_writes,
    )

    replay = factory.build(
        window=_window(),
        pagination=_pagination(),
        page_keys=_page_keys(),
        page_writes=replay_writes,
    )

    assert serializer.serialize(first) == serializer.serialize(replay)


def test_manifest_excludes_volatile_runtime_fields() -> None:
    """Keep canonical completion bytes independent of runtime metadata."""
    payload = NvdIncrementalManifestSerializer().serialize(_manifest())

    document = cast(
        dict[str, object],
        json.loads(payload),
    )

    assert "retrieved_at" not in document
    assert "etag" not in document
    assert "write_status" not in document


def test_manifest_rejects_missing_page_persistence_result() -> None:
    """Require exact S3 provenance for every validated page."""
    with pytest.raises(
        ValueError,
        match="do not match",
    ):
        NvdIncrementalManifestFactory().build(
            window=_window(),
            pagination=_pagination(),
            page_keys=_page_keys(),
            page_writes=_writes()[:2],
        )


def test_manifest_supports_explicit_empty_result_page() -> None:
    """Represent a zero-result query as complete source evidence."""
    page = _page(
        start_index=0,
        total_results=0,
        cve_ids=(),
        timestamp="2026-08-18T20:00:01.000",
    )

    pagination = NvdCveApiPagination(pages=(page,))

    window = _window()
    key_factory = NvdIncrementalKeyFactory()

    manifest = NvdIncrementalManifestFactory().build(
        window=window,
        pagination=pagination,
        page_keys=(
            key_factory.build_attempt_page_key(
                window=window,
                attempt_id="a" * 64,
                start_index=0,
            ),
        ),
        page_writes=(
            NvdBronzeWriteResult(
                status=NvdBronzeWriteStatus.CREATED,
                version_id="empty-page-version",
            ),
        ),
    )

    assert manifest.total_results == 0
    assert manifest.page_count == 1
    assert manifest.pages[0].results_per_page == 0
