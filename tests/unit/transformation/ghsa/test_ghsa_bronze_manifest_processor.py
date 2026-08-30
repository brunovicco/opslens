"""Tests for exact GHSA Bronze COMPLETE manifest authorization."""

import hashlib
import json
from datetime import UTC, datetime
from typing import cast

import pytest

from opslens.ingestion.ghsa.application.key_factory import (
    GhsaBronzeKeyFactory,
)
from opslens.ingestion.ghsa.application.manifest import (
    GhsaCompleteManifest,
    GhsaCompleteManifestSerializer,
    GhsaStoredPage,
)
from opslens.ingestion.ghsa.domain.api_page import (
    GhsaRequestUrlPolicy,
)
from opslens.ingestion.ghsa.domain.sync import (
    GhsaSyncMode,
    GhsaSyncWindow,
)
from opslens.transformation.ghsa.runtime.manifest_processor import (
    GhsaBronzeManifestProcessorV1,
)

ATTEMPT_ID = "2" * 64
MANIFEST_VERSION_ID = "manifest-version"


def _window() -> GhsaSyncWindow:
    """Return one deterministic reviewed GHSA source window."""
    return GhsaSyncWindow(
        mode=GhsaSyncMode.PUBLISHED,
        start_at=datetime(
            2026,
            8,
            27,
            tzinfo=UTC,
        ),
        end_at=datetime(
            2026,
            8,
            28,
            tzinfo=UTC,
        ),
    )


def _manifest_fixture() -> tuple[bytes, str]:
    """Build one canonical empty COMPLETE Bronze manifest."""
    window = _window()
    key_factory = GhsaBronzeKeyFactory()

    page_bytes = b"[]"

    page = GhsaStoredPage(
        page_ordinal=1,
        key=key_factory.build_page_key(
            window=window,
            attempt_id=ATTEMPT_ID,
            page_ordinal=1,
        ),
        version_id="page-version",
        size_bytes=len(page_bytes),
        sha256=hashlib.sha256(page_bytes).hexdigest(),
        item_count=0,
        request_url=GhsaRequestUrlPolicy.build_initial(
            window,
        ),
        next_url=None,
        first_ghsa_id=None,
        last_ghsa_id=None,
    )

    manifest = GhsaCompleteManifest(
        mode=window.mode,
        sync_id=window.sync_id,
        attempt_id=ATTEMPT_ID,
        window_start_at=window.start_at,
        window_end_at=window.end_at,
        total_items=0,
        total_bytes=len(page_bytes),
        pages=(page,),
    )

    manifest_bytes = GhsaCompleteManifestSerializer().serialize(
        manifest
    )

    manifest_key = key_factory.build_manifest_key(
        window=window,
        attempt_id=ATTEMPT_ID,
    )

    return manifest_bytes, manifest_key


def _processor() -> GhsaBronzeManifestProcessorV1:
    """Build the deterministic manifest authorization processor."""
    return GhsaBronzeManifestProcessorV1(
        key_factory=GhsaBronzeKeyFactory(),
        serializer=GhsaCompleteManifestSerializer(),
    )


def _canonical_mutation(
    manifest_bytes: bytes,
    *,
    field_name: str,
    value: object,
) -> bytes:
    """Mutate one top-level field while preserving canonical JSON form."""
    document = json.loads(
        manifest_bytes.decode("utf-8")
    )

    assert isinstance(document, dict)

    document[field_name] = value

    return (
        json.dumps(
            document,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def test_authorizes_exact_complete_manifest() -> None:
    """Derive Silver attempt and page evidence from exact Bronze authority."""
    manifest_bytes, manifest_key = _manifest_fixture()

    authorized = _processor().process(
        manifest_key=manifest_key,
        manifest_version_id=MANIFEST_VERSION_ID,
        manifest_bytes=manifest_bytes,
    )

    assert authorized.manifest.attempt_id == ATTEMPT_ID

    context = authorized.attempt_context

    assert context.sync_id == _window().sync_id
    assert context.attempt_id == ATTEMPT_ID
    assert context.manifest_key == manifest_key
    assert context.manifest_version_id == MANIFEST_VERSION_ID

    page_evidences = authorized.page_evidences

    assert len(page_evidences) == 1

    page = page_evidences[0]

    assert page.page_ordinal == 1
    assert page.page_version_id == "page-version"
    assert page.expected_size_bytes == 2
    assert page.expected_sha256 == hashlib.sha256(
        b"[]"
    ).hexdigest()


def test_rejects_manifest_key_outside_deterministic_attempt_layout() -> None:
    """Reject a valid manifest presented under an unauthorized object key."""
    manifest_bytes, _manifest_key = _manifest_fixture()

    with pytest.raises(
        ValueError,
        match="manifest key does not match",
    ):
        _processor().process(
            manifest_key="bronze/ghsa/advisories/manifest.json",
            manifest_version_id=MANIFEST_VERSION_ID,
            manifest_bytes=manifest_bytes,
        )


def test_rejects_sync_id_not_derived_from_window() -> None:
    """Require logical source-query identity to be recomputed from the window."""
    manifest_bytes, manifest_key = _manifest_fixture()

    mutated = _canonical_mutation(
        manifest_bytes,
        field_name="sync_id",
        value="9" * 64,
    )

    with pytest.raises(
        ValueError,
        match="sync_id does not match",
    ):
        _processor().process(
            manifest_key=manifest_key,
            manifest_version_id=MANIFEST_VERSION_ID,
            manifest_bytes=mutated,
        )


def test_rejects_page_key_outside_attempt_layout() -> None:
    """Reject manifest pages that escape their authorized Bronze attempt."""
    manifest_bytes, manifest_key = _manifest_fixture()

    parsed = cast(
        object,
        json.loads(manifest_bytes.decode("utf-8")),
    )


    assert isinstance(parsed, dict)

    document = cast(dict[str, object], parsed)

    raw_pages = document["pages"]
    assert isinstance(raw_pages, list)

    pages = cast(list[object], raw_pages)

    raw_page = pages[0]
    assert isinstance(raw_page, dict)

    page = cast(dict[str, object], raw_page)

    page["key"] = "bronze/ghsa/other/response.json"
    mutated = (
        json.dumps(
            document,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")

    with pytest.raises(
        ValueError,
        match="page key does not match",
    ):
        _processor().process(
            manifest_key=manifest_key,
            manifest_version_id=MANIFEST_VERSION_ID,
            manifest_bytes=mutated,
        )


def test_rejects_duplicate_json_object_fields() -> None:
    """Reject ambiguous JSON objects before schema interpretation."""
    duplicate = b'{"sync_id":"one","sync_id":"two"}'

    with pytest.raises(
        ValueError,
        match="duplicate JSON object field",
    ):
        _processor().process(
            manifest_key="manifest.json",
            manifest_version_id=MANIFEST_VERSION_ID,
            manifest_bytes=duplicate,
        )


def test_rejects_noncanonical_manifest_representation() -> None:
    """Require the exact canonical bytes emitted by the Bronze serializer."""
    manifest_bytes, manifest_key = _manifest_fixture()

    noncanonical = b" " + manifest_bytes

    with pytest.raises(
        ValueError,
        match="canonical COMPLETE manifest representation",
    ):
        _processor().process(
            manifest_key=manifest_key,
            manifest_version_id=MANIFEST_VERSION_ID,
            manifest_bytes=noncanonical,
        )
