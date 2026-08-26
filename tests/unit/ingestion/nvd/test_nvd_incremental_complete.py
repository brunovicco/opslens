"""Unit tests for strict NVD incremental COMPLETE parsing."""

from datetime import UTC, datetime

import pytest

from opslens.ingestion.nvd.application.incremental_complete import (
    NvdIncrementalManifestParseError,
    NvdIncrementalManifestParser,
)
from opslens.ingestion.nvd.application.incremental_manifest import (
    NvdIncrementalManifest,
    NvdIncrementalManifestSerializer,
    NvdIncrementalStoredPage,
)


def _manifest() -> NvdIncrementalManifest:
    """Build one zero-result COMPLETE manifest."""
    return NvdIncrementalManifest(
        update_id="a" * 64,
        window_start_at=datetime(
            2026,
            8,
            18,
            7,
            0,
            12,
            tzinfo=UTC,
        ),
        window_end_at=datetime(
            2026,
            8,
            18,
            7,
            10,
            12,
            tzinfo=UTC,
        ),
        total_results=0,
        pages=(
            NvdIncrementalStoredPage(
                key=(
                    "bronze/nvd/cve/updates/"
                    f"update_id={'a' * 64}/"
                    "page_start=000000/response.json"
                ),
                version_id="page-version",
                size_bytes=146,
                sha256="b" * 64,
                start_index=0,
                results_per_page=0,
                total_results=0,
                source_timestamp="2026-08-24T19:51:57.077",
            ),
        ),
    )


def test_parses_canonical_complete_manifest() -> None:
    """Round-trip canonical COMPLETE evidence."""
    manifest = _manifest()
    payload = NvdIncrementalManifestSerializer().serialize(
        manifest
    )

    parsed = NvdIncrementalManifestParser().parse(
        payload
    )

    assert parsed == manifest


@pytest.mark.parametrize(
    "replacement",
    [
        b'"manifest_version":"2"',
        b'"completion_status":"partial"',
        b'"source":"other"',
    ],
)
def test_rejects_unsupported_constants(
    replacement: bytes,
) -> None:
    """Fail closed on unsupported COMPLETE schema constants."""
    payload = NvdIncrementalManifestSerializer().serialize(
        _manifest()
    )

    if b"manifest_version" in replacement:
        changed = payload.replace(
            b'"manifest_version":"1"',
            replacement,
        )
    elif b"completion_status" in replacement:
        changed = payload.replace(
            b'"completion_status":"complete"',
            replacement,
        )
    else:
        changed = payload.replace(
            b'"source":"nvd-cve"',
            replacement,
        )

    with pytest.raises(
        NvdIncrementalManifestParseError,
    ):
        NvdIncrementalManifestParser().parse(
            changed
        )


def test_rejects_non_canonical_json() -> None:
    """Reject semantically valid bytes that are not canonical evidence."""
    canonical = NvdIncrementalManifestSerializer().serialize(
        _manifest()
    )

    non_canonical = canonical.rstrip(
        b"\n"
    )

    with pytest.raises(
        NvdIncrementalManifestParseError,
        match="not canonical",
    ):
        NvdIncrementalManifestParser().parse(
            non_canonical
        )
