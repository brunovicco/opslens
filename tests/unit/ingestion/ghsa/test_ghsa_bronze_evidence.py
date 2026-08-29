"""Tests for GHSA physical attempt identity, Bronze keys, and COMPLETE manifest."""

import json
from dataclasses import replace
from datetime import UTC, datetime
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import pytest

from opslens.ingestion.ghsa.application.attempt import (
    GhsaAttemptIdFactory,
)
from opslens.ingestion.ghsa.application.key_factory import (
    GhsaBronzeKeyFactory,
)
from opslens.ingestion.ghsa.application.manifest import (
    GhsaCompleteManifestFactory,
    GhsaCompleteManifestSerializer,
)
from opslens.ingestion.ghsa.application.models import (
    GhsaBronzeWriteResult,
)
from opslens.ingestion.ghsa.domain.api_page import (
    GhsaAdvisoryApiPageParser,
    GhsaAdvisoryPagination,
    GhsaRequestUrlPolicy,
)
from opslens.ingestion.ghsa.domain.sync import (
    GhsaSyncMode,
    GhsaSyncWindow,
)


def _window(mode: GhsaSyncMode = GhsaSyncMode.PUBLISHED) -> GhsaSyncWindow:
    """Build one bounded July 2026 window."""
    return GhsaSyncWindow(
        mode=mode,
        start_at=datetime(2026, 7, 1, 0, 0, 0, tzinfo=UTC),
        end_at=datetime(2026, 7, 31, 23, 59, 59, tzinfo=UTC),
    )


def _advisory(
    ghsa_id: str,
    *,
    published_at: str,
    updated_at: str,
    marker: str | None = None,
) -> dict[str, object]:
    """Build a source-like reviewed advisory object."""
    document: dict[str, object] = {
        "ghsa_id": ghsa_id,
        "type": "reviewed",
        "published_at": published_at,
        "updated_at": updated_at,
    }

    if marker is not None:
        document["summary"] = marker

    return document


def _payload(*items: dict[str, object]) -> bytes:
    """Serialize exact compact source-like response bytes."""
    return json.dumps(
        list(items),
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")


def _with_after_cursor(url: str, cursor: str) -> str:
    """Append one opaque cursor while preserving the frozen query."""
    parsed = urlsplit(url)
    pairs = parse_qsl(parsed.query, keep_blank_values=True)
    pairs.append(("after", cursor))
    return urlunsplit(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            urlencode(pairs),
            "",
        )
    )


def _pagination(
    *,
    cursor: str = "opaque-cursor-1",
    marker: str | None = None,
) -> tuple[GhsaSyncWindow, GhsaAdvisoryPagination]:
    """Build one valid two-page physical source observation."""
    window = _window()
    initial_url = GhsaRequestUrlPolicy.build_initial(window)
    next_url = _with_after_cursor(initial_url, cursor)
    parser = GhsaAdvisoryApiPageParser()
    first = parser.parse(
        _payload(
            _advisory(
                "GHSA-2345-6789-cfgh",
                published_at="2026-07-02T10:00:00Z",
                updated_at="2026-07-03T10:00:00Z",
                marker=marker,
            )
        ),
        request_url=initial_url,
        link_header=f'<{next_url}>; rel="next"',
        window=window,
    )
    second = parser.parse(
        _payload(
            _advisory(
                "GHSA-2345-6789-cfgj",
                published_at="2026-07-04T10:00:00Z",
                updated_at="2026-07-05T10:00:00Z",
            )
        ),
        request_url=next_url,
        link_header=None,
        window=window,
    )

    return window, GhsaAdvisoryPagination(
        window=window,
        pages=(first, second),
    )


def _writes(
    *,
    window: GhsaSyncWindow,
    pagination: GhsaAdvisoryPagination,
) -> tuple[GhsaBronzeWriteResult, ...]:
    """Build exact versioned persistence results for a validated attempt."""
    attempt_id = GhsaAttemptIdFactory().build(
        window=window,
        pagination=pagination,
    )
    key_factory = GhsaBronzeKeyFactory()

    return tuple(
        GhsaBronzeWriteResult(
            key=key_factory.build_page_key(
                window=window,
                attempt_id=attempt_id,
                page_ordinal=ordinal,
            ),
            version_id=f"version-{ordinal}",
        )
        for ordinal, _page in enumerate(pagination.pages, start=1)
    )


def _manifest(
    *,
    window: GhsaSyncWindow,
    pagination: GhsaAdvisoryPagination,
):
    """Build one COMPLETE manifest fixture."""
    return GhsaCompleteManifestFactory(
        attempt_factory=GhsaAttemptIdFactory(),
        key_factory=GhsaBronzeKeyFactory(),
    ).build(
        window=window,
        pagination=pagination,
        page_writes=_writes(window=window, pagination=pagination),
    )


def test_attempt_id_is_deterministic_for_same_complete_observation() -> None:
    """Replay identical exact pages and cursor evidence to the same attempt id."""
    window, pagination = _pagination()
    factory = GhsaAttemptIdFactory()

    first = factory.build(window=window, pagination=pagination)
    second = factory.build(window=window, pagination=pagination)

    assert first == second
    assert len(first) == 64


def test_changed_response_bytes_change_attempt_id() -> None:
    """Bind physical identity to exact response content rather than timestamps alone."""
    window, original = _pagination(marker="original")
    changed_window, changed = _pagination(marker="changed")

    assert window.sync_id == changed_window.sync_id
    assert GhsaAttemptIdFactory().build(window=window, pagination=original) != (
        GhsaAttemptIdFactory().build(window=changed_window, pagination=changed)
    )


def test_changed_cursor_chain_changes_attempt_id() -> None:
    """Treat pagination navigation evidence as part of the physical observation."""
    window, first = _pagination(cursor="cursor-a")
    other_window, second = _pagination(cursor="cursor-b")

    assert window.sync_id == other_window.sync_id
    assert GhsaAttemptIdFactory().build(window=window, pagination=first) != (
        GhsaAttemptIdFactory().build(window=other_window, pagination=second)
    )


def test_attempt_id_rejects_different_logical_window() -> None:
    """Prevent physical evidence from being rebound to another sync identity."""
    _window_used, pagination = _pagination()

    with pytest.raises(ValueError, match="does not match the requested sync window"):
        GhsaAttemptIdFactory().build(
            window=_window(GhsaSyncMode.MODIFIED),
            pagination=pagination,
        )


def test_bronze_page_key_is_scoped_by_mode_sync_attempt_and_ordinal() -> None:
    """Freeze a human-navigable but content-bound immutable page layout."""
    window, pagination = _pagination()
    attempt_id = GhsaAttemptIdFactory().build(window=window, pagination=pagination)

    key = GhsaBronzeKeyFactory().build_page_key(
        window=window,
        attempt_id=attempt_id,
        page_ordinal=2,
    )

    assert key == (
        "bronze/ghsa/advisories/"
        f"mode=published/sync_id={window.sync_id}/attempt_id={attempt_id}/"
        "page=000002/response.json"
    )


def test_bronze_manifest_key_is_attempt_scoped() -> None:
    """Keep COMPLETE evidence beside the exact physical page inventory."""
    window, pagination = _pagination()
    attempt_id = GhsaAttemptIdFactory().build(window=window, pagination=pagination)

    key = GhsaBronzeKeyFactory().build_manifest_key(
        window=window,
        attempt_id=attempt_id,
    )

    assert key.endswith(f"sync_id={window.sync_id}/attempt_id={attempt_id}/manifest.json")


def test_key_factory_rejects_invalid_attempt_and_page_ordinal() -> None:
    """Fail closed on ambiguous physical coordinates."""
    window = _window()
    factory = GhsaBronzeKeyFactory()

    with pytest.raises(ValueError, match="attempt_id"):
        factory.build_manifest_key(window=window, attempt_id="not-a-sha")

    with pytest.raises(ValueError, match="positive integer"):
        factory.build_page_key(
            window=window,
            attempt_id="a" * 64,
            page_ordinal=0,
        )


def test_complete_manifest_binds_exact_s3_versions_and_page_evidence() -> None:
    """Carry source hashes, URLs, object keys, and VersionIds into completion proof."""
    window, pagination = _pagination()
    manifest = _manifest(window=window, pagination=pagination)

    assert manifest.sync_id == window.sync_id
    assert manifest.page_count == 2
    assert manifest.total_items == pagination.total_items
    assert manifest.total_bytes == pagination.total_bytes
    assert manifest.pages[0].version_id == "version-1"
    assert manifest.pages[1].version_id == "version-2"
    assert manifest.pages[0].sha256 == pagination.pages[0].sha256
    assert manifest.pages[0].first_ghsa_id == "GHSA-2345-6789-cfgh"
    assert manifest.pages[1].last_ghsa_id == "GHSA-2345-6789-cfgj"


def test_manifest_factory_rejects_wrong_persisted_key() -> None:
    """Do not declare COMPLETE when S3 persistence used a different physical path."""
    window, pagination = _pagination()
    writes = list(_writes(window=window, pagination=pagination))
    writes[0] = GhsaBronzeWriteResult(
        key="bronze/ghsa/wrong/response.json",
        version_id="version-1",
    )

    with pytest.raises(ValueError, match="deterministic Bronze layout"):
        GhsaCompleteManifestFactory(
            attempt_factory=GhsaAttemptIdFactory(),
            key_factory=GhsaBronzeKeyFactory(),
        ).build(
            window=window,
            pagination=pagination,
            page_writes=tuple(writes),
        )


def test_manifest_factory_rejects_missing_persistence_result() -> None:
    """Require one exact VersionId result for every validated response page."""
    window, pagination = _pagination()
    writes = _writes(window=window, pagination=pagination)

    with pytest.raises(ValueError, match="do not match the page inventory"):
        GhsaCompleteManifestFactory(
            attempt_factory=GhsaAttemptIdFactory(),
            key_factory=GhsaBronzeKeyFactory(),
        ).build(
            window=window,
            pagination=pagination,
            page_writes=writes[:1],
        )


def test_manifest_serializer_is_deterministic_and_excludes_auth_material() -> None:
    """Serialize canonical completion evidence without credentials or runtime metadata."""
    window, pagination = _pagination()
    manifest = _manifest(window=window, pagination=pagination)
    serializer = GhsaCompleteManifestSerializer()

    first = serializer.serialize(manifest)
    second = serializer.serialize(manifest)

    assert first == second
    assert first.endswith(b"\n")
    assert b'"completion_status":"complete"' in first
    assert b'"api_version":"2026-03-10"' in first
    assert b'"advisory_type":"reviewed"' in first
    assert b"Authorization" not in first
    assert b"Bearer" not in first


def test_manifest_validation_detects_tampered_totals() -> None:
    """Reject completion evidence whose aggregate count does not match page inventory."""
    window, pagination = _pagination()
    manifest = _manifest(window=window, pagination=pagination)

    with pytest.raises(ValueError, match="item counts do not match total_items"):
        replace(manifest, total_items=manifest.total_items + 1)


def test_empty_source_window_produces_one_complete_empty_page() -> None:
    """Represent a valid zero-result window without inventing advisory evidence."""
    window = _window()
    request_url = GhsaRequestUrlPolicy.build_initial(window)
    page = GhsaAdvisoryApiPageParser().parse(
        b"[]",
        request_url=request_url,
        link_header=None,
        window=window,
    )
    pagination = GhsaAdvisoryPagination(window=window, pages=(page,))
    manifest = _manifest(window=window, pagination=pagination)

    assert manifest.total_items == 0
    assert manifest.page_count == 1
    assert manifest.pages[0].first_ghsa_id is None
    assert manifest.pages[0].last_ghsa_id is None


def test_write_result_requires_exact_key_and_version_id() -> None:
    """Require versioned object provenance before building COMPLETE evidence."""
    with pytest.raises(ValueError, match="non-empty key"):
        GhsaBronzeWriteResult(key="", version_id="version-1")

    with pytest.raises(ValueError, match="VersionId"):
        GhsaBronzeWriteResult(key="bronze/ghsa/page.json", version_id="")
