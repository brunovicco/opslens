"""Tests for safe exact-version NVD Bronze request loading."""

import json

import pytest

from opslens.transformation.nvd.application.request_loader import (
    NvdSilverRequestLoadError,
    NvdSilverTransformRequestLoaderV1,
)
from opslens.transformation.nvd.provenance.models import (
    NvdBronzeObjectPayloadV1,
)
from opslens.transformation.nvd.serialization.models import (
    NvdSilverSourceKind,
)


class RecordingObjectReader:
    """Return configured exact-version objects and record requested coordinates."""

    def __init__(
        self,
        payloads: dict[tuple[str, str], bytes],
    ) -> None:
        """Initialize the fake exact-version object inventory."""
        self._payloads = payloads
        self.calls: list[tuple[str, str]] = []

    def get(
        self,
        *,
        key: str,
        version_id: str,
    ) -> NvdBronzeObjectPayloadV1:
        """Return one configured exact object version."""
        self.calls.append(
            (
                key,
                version_id,
            )
        )

        return NvdBronzeObjectPayloadV1(
            key=key,
            version_id=version_id,
            raw_bytes=self._payloads[(key, version_id)],
        )


def _json_bytes(
    document: dict[str, object],
) -> bytes:
    """Serialize one test manifest."""
    return json.dumps(
        document,
        separators=(",", ":"),
    ).encode("utf-8")


def test_loads_bootstrap_manifest_and_exact_objects() -> None:
    """Load manifest first, then the exact feed and META versions."""
    base = "bronze/nvd/cve/bootstrap/feed_year=2026/feed_revision=revision-1"

    manifest_key = f"{base}/manifest.json"
    feed_key = f"{base}/nvdcve-2.0-2026.json.gz"
    meta_key = f"{base}/nvdcve-2.0-2026.meta"

    manifest_bytes = _json_bytes(
        {
            "feed_object": {
                "key": feed_key,
                "version_id": "feed-v1",
            },
            "meta_object": {
                "key": meta_key,
                "version_id": "meta-v1",
            },
        }
    )

    reader = RecordingObjectReader(
        {
            (manifest_key, "manifest-v1"): manifest_bytes,
            (feed_key, "feed-v1"): b"feed-bytes",
            (meta_key, "meta-v1"): b"meta-bytes",
        }
    )

    request = NvdSilverTransformRequestLoaderV1(
        object_reader=reader,
    ).load(
        source_kind=NvdSilverSourceKind.BOOTSTRAP,
        manifest_key=manifest_key,
        manifest_version_id="manifest-v1",
    )

    assert reader.calls == [
        (manifest_key, "manifest-v1"),
        (feed_key, "feed-v1"),
        (meta_key, "meta-v1"),
    ]

    assert request.manifest_bytes == manifest_bytes
    assert request.manifest_version_id == "manifest-v1"
    assert [payload.key for payload in request.object_payloads] == [
        feed_key,
        meta_key,
    ]


def test_loads_incremental_pages_in_manifest_order() -> None:
    """Preserve page inventory order while using explicit VersionIds."""
    update_id = "a" * 64
    base = f"bronze/nvd/cve/updates/update_id={update_id}"

    manifest_key = f"{base}/manifest.json"
    first_key = f"{base}/page_start=000000/response.json"
    second_key = f"{base}/page_start=002000/response.json"

    manifest_bytes = _json_bytes(
        {
            "pages": [
                {
                    "key": first_key,
                    "version_id": "page-v1",
                },
                {
                    "key": second_key,
                    "version_id": "page-v2",
                },
            ]
        }
    )

    reader = RecordingObjectReader(
        {
            (manifest_key, "manifest-v1"): manifest_bytes,
            (first_key, "page-v1"): b"page-1",
            (second_key, "page-v2"): b"page-2",
        }
    )

    request = NvdSilverTransformRequestLoaderV1(
        object_reader=reader,
    ).load(
        source_kind=NvdSilverSourceKind.INCREMENTAL,
        manifest_key=manifest_key,
        manifest_version_id="manifest-v1",
    )

    assert reader.calls == [
        (manifest_key, "manifest-v1"),
        (first_key, "page-v1"),
        (second_key, "page-v2"),
    ]

    assert [payload.version_id for payload in request.object_payloads] == [
        "page-v1",
        "page-v2",
    ]


def test_rejects_object_outside_manifest_batch_before_reading_it() -> None:
    """Prevent an untrusted manifest from causing arbitrary object reads."""
    base = "bronze/nvd/cve/bootstrap/feed_year=2026/feed_revision=revision-1"

    manifest_key = f"{base}/manifest.json"

    manifest_bytes = _json_bytes(
        {
            "feed_object": {
                "key": "bronze/other/source.json",
                "version_id": "foreign-v1",
            },
            "meta_object": {
                "key": f"{base}/feed.meta",
                "version_id": "meta-v1",
            },
        }
    )

    reader = RecordingObjectReader(
        {
            (manifest_key, "manifest-v1"): manifest_bytes,
        }
    )

    with pytest.raises(
        NvdSilverRequestLoadError,
        match="outside",
    ):
        NvdSilverTransformRequestLoaderV1(
            object_reader=reader,
        ).load(
            source_kind=NvdSilverSourceKind.BOOTSTRAP,
            manifest_key=manifest_key,
            manifest_version_id="manifest-v1",
        )

    assert reader.calls == [
        (manifest_key, "manifest-v1"),
    ]


def test_rejects_duplicate_incremental_object_keys_before_page_reads() -> None:
    """Do not issue duplicate reads from malformed page inventories."""
    update_id = "b" * 64
    base = f"bronze/nvd/cve/updates/update_id={update_id}"

    manifest_key = f"{base}/manifest.json"
    page_key = f"{base}/page_start=000000/response.json"

    manifest_bytes = _json_bytes(
        {
            "pages": [
                {
                    "key": page_key,
                    "version_id": "page-v1",
                },
                {
                    "key": page_key,
                    "version_id": "page-v2",
                },
            ]
        }
    )

    reader = RecordingObjectReader(
        {
            (manifest_key, "manifest-v1"): manifest_bytes,
        }
    )

    with pytest.raises(
        NvdSilverRequestLoadError,
        match="duplicate",
    ):
        NvdSilverTransformRequestLoaderV1(
            object_reader=reader,
        ).load(
            source_kind=NvdSilverSourceKind.INCREMENTAL,
            manifest_key=manifest_key,
            manifest_version_id="manifest-v1",
        )

    assert reader.calls == [
        (manifest_key, "manifest-v1"),
    ]


def test_rejects_duplicate_json_keys() -> None:
    """Reject ambiguous JSON before discovering object coordinates."""
    update_id = "c" * 64
    base = f"bronze/nvd/cve/updates/update_id={update_id}"
    manifest_key = f"{base}/manifest.json"

    manifest_bytes = b'{"pages":[],"pages":[]}'

    reader = RecordingObjectReader(
        {
            (manifest_key, "manifest-v1"): manifest_bytes,
        }
    )

    with pytest.raises(
        NvdSilverRequestLoadError,
        match="invalid JSON",
    ):
        NvdSilverTransformRequestLoaderV1(
            object_reader=reader,
        ).load(
            source_kind=NvdSilverSourceKind.INCREMENTAL,
            manifest_key=manifest_key,
            manifest_version_id="manifest-v1",
        )

    assert reader.calls == [
        (manifest_key, "manifest-v1"),
    ]
