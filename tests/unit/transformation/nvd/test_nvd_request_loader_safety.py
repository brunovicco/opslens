"""Safety-bound tests for the NVD Silver Bronze request loader."""

import json

import pytest

from opslens.ingestion.nvd.domain.api_page import (
    MAX_RESULTS_PER_PAGE,
)
from opslens.transformation.nvd.application.request_loader import (
    NVD_SILVER_VALIDATED_MAX_INCREMENTAL_PAGES,
    NVD_SILVER_VALIDATED_MAX_INCREMENTAL_RESULTS,
    NvdSilverRequestLoadError,
    NvdSilverTransformRequestLoaderV1,
)
from opslens.transformation.nvd.provenance.models import (
    NvdBronzeObjectPayloadV1,
)
from opslens.transformation.nvd.serialization.models import (
    NvdSilverSourceKind,
)

UPDATE_ID = "a" * 64

MANIFEST_KEY = f"bronze/nvd/cve/updates/update_id={UPDATE_ID}/manifest.json"
MANIFEST_VERSION = "manifest-v1"


class RecordingObjectReader:
    """Return configured exact objects while recording every read."""

    def __init__(
        self,
        objects: dict[tuple[str, str], bytes],
    ) -> None:
        """Initialize the fake reader with exact object payloads."""
        self.objects = objects
        self.calls: list[tuple[str, str]] = []

    def get(
        self,
        *,
        key: str,
        version_id: str,
    ) -> NvdBronzeObjectPayloadV1:
        """Return one configured exact object and record the read."""
        self.calls.append(
            (
                key,
                version_id,
            )
        )

        raw_bytes = self.objects[
            (
                key,
                version_id,
            )
        ]

        return NvdBronzeObjectPayloadV1(
            key=key,
            version_id=version_id,
            raw_bytes=raw_bytes,
        )


def _canonical_json_bytes(
    document: dict[str, object],
) -> bytes:
    text = json.dumps(
        document,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )

    return f"{text}\n".encode()


def _page(
    *,
    start_index: int,
    results_per_page: int,
    total_results: int,
) -> dict[str, object]:
    key = (
        MANIFEST_KEY.removesuffix("/manifest.json") + f"/page_start={start_index:06d}/response.json"
    )

    return {
        "key": key,
        "results_per_page": results_per_page,
        "start_index": start_index,
        "total_results": total_results,
        "version_id": f"page-v{start_index}",
    }


def _manifest(
    *,
    total_results: int,
    pages: list[dict[str, object]],
) -> bytes:
    return _canonical_json_bytes(
        {
            "page_count": len(pages),
            "pages": pages,
            "total_results": total_results,
        }
    )


def test_rejects_page_fanout_before_any_page_get() -> None:
    """An over-bound manifest must cause only the manifest S3 read."""
    page_count = NVD_SILVER_VALIDATED_MAX_INCREMENTAL_PAGES + 1

    pages = [
        _page(
            start_index=index,
            results_per_page=1,
            total_results=page_count,
        )
        for index in range(page_count)
    ]

    reader = RecordingObjectReader(
        {
            (
                MANIFEST_KEY,
                MANIFEST_VERSION,
            ): _manifest(
                total_results=page_count,
                pages=pages,
            ),
        }
    )

    loader = NvdSilverTransformRequestLoaderV1(
        object_reader=reader,
    )

    with pytest.raises(
        NvdSilverRequestLoadError,
        match="page-read bound",
    ):
        loader.load(
            source_kind=NvdSilverSourceKind.INCREMENTAL,
            manifest_key=MANIFEST_KEY,
            manifest_version_id=MANIFEST_VERSION,
        )

    assert reader.calls == [
        (
            MANIFEST_KEY,
            MANIFEST_VERSION,
        )
    ]


def test_rejects_unproven_incremental_cardinality_before_page_get() -> None:
    """Do not allow a manifest to exceed proven Lambda cardinality."""
    total_results = NVD_SILVER_VALIDATED_MAX_INCREMENTAL_RESULTS + 1

    pages = [
        _page(
            start_index=0,
            results_per_page=1,
            total_results=total_results,
        )
    ]

    reader = RecordingObjectReader(
        {
            (
                MANIFEST_KEY,
                MANIFEST_VERSION,
            ): _manifest(
                total_results=total_results,
                pages=pages,
            ),
        }
    )

    loader = NvdSilverTransformRequestLoaderV1(
        object_reader=reader,
    )

    with pytest.raises(
        NvdSilverRequestLoadError,
        match="runtime bound",
    ):
        loader.load(
            source_kind=NvdSilverSourceKind.INCREMENTAL,
            manifest_key=MANIFEST_KEY,
            manifest_version_id=MANIFEST_VERSION,
        )

    assert reader.calls == [
        (
            MANIFEST_KEY,
            MANIFEST_VERSION,
        )
    ]


def test_rejects_page_count_inventory_mismatch_before_page_get() -> None:
    """Declared page_count cannot understate the actual page inventory."""
    page = _page(
        start_index=0,
        results_per_page=1,
        total_results=1,
    )

    manifest = _canonical_json_bytes(
        {
            "page_count": 2,
            "pages": [page],
            "total_results": 1,
        }
    )

    reader = RecordingObjectReader(
        {
            (
                MANIFEST_KEY,
                MANIFEST_VERSION,
            ): manifest,
        }
    )

    loader = NvdSilverTransformRequestLoaderV1(
        object_reader=reader,
    )

    with pytest.raises(
        NvdSilverRequestLoadError,
        match="page_count",
    ):
        loader.load(
            source_kind=NvdSilverSourceKind.INCREMENTAL,
            manifest_key=MANIFEST_KEY,
            manifest_version_id=MANIFEST_VERSION,
        )

    assert reader.calls == [
        (
            MANIFEST_KEY,
            MANIFEST_VERSION,
        )
    ]


def test_validated_runtime_ceiling_can_be_loaded() -> None:
    """The currently proven runtime envelope remains processable."""
    remaining = NVD_SILVER_VALIDATED_MAX_INCREMENTAL_RESULTS
    start_index = 0
    pages: list[dict[str, object]] = []
    objects: dict[tuple[str, str], bytes] = {}

    while remaining > 0:
        results_per_page = min(
            MAX_RESULTS_PER_PAGE,
            remaining,
        )

        page = _page(
            start_index=start_index,
            results_per_page=results_per_page,
            total_results=(NVD_SILVER_VALIDATED_MAX_INCREMENTAL_RESULTS),
        )

        pages.append(page)

        key = page["key"]
        version_id = page["version_id"]

        assert isinstance(key, str)
        assert isinstance(version_id, str)

        objects[
            (
                key,
                version_id,
            )
        ] = b"{}\n"

        start_index += results_per_page
        remaining -= results_per_page

    manifest = _manifest(
        total_results=(NVD_SILVER_VALIDATED_MAX_INCREMENTAL_RESULTS),
        pages=pages,
    )

    objects[
        (
            MANIFEST_KEY,
            MANIFEST_VERSION,
        )
    ] = manifest

    reader = RecordingObjectReader(objects)

    loader = NvdSilverTransformRequestLoaderV1(
        object_reader=reader,
    )

    request = loader.load(
        source_kind=NvdSilverSourceKind.INCREMENTAL,
        manifest_key=MANIFEST_KEY,
        manifest_version_id=MANIFEST_VERSION,
    )

    assert len(request.object_payloads) == (NVD_SILVER_VALIDATED_MAX_INCREMENTAL_PAGES)

    assert reader.calls[0] == (
        MANIFEST_KEY,
        MANIFEST_VERSION,
    )
