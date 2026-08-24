"""Tests for exact NVD Silver promotion-evidence loading."""

import hashlib
import json
from datetime import UTC, datetime

import pytest

from opslens.transformation.nvd.application.watermark_promotion_evidence_loader import (
    NvdPromotionExactObjectReaderV1,
    NvdSilverCompleteRefV1,
    NvdWatermarkPromotionEvidenceLoadError,
    NvdWatermarkPromotionEvidenceLoaderV1,
)
from opslens.transformation.nvd.completion.promotion import (
    NvdPersistedObjectPayloadV1,
)

UPDATE_ID = "a" * 64
BRONZE_SHA = "b" * 64
LOGICAL_SHA = "c" * 64
MANIFEST_KEY = (
    "silver/nvd/cve/schema_version=1/source_kind=incremental/"
    f"update_id={UPDATE_ID}/manifest.json"
)
PARQUET_KEY = (
    "silver/nvd/cve/schema_version=1/source_kind=incremental/"
    f"update_id={UPDATE_ID}/part-00000.parquet"
)
MANIFEST_VERSION = "silver-manifest-version-1"
PARQUET_VERSION = "silver-parquet-version-1"
PARQUET_BYTES = b"PAR1-exact-nvd-silver-parquet-evidence"
PARQUET_SHA = hashlib.sha256(PARQUET_BYTES).hexdigest()
START = "2026-08-18T07:00:12Z"
END = "2026-08-18T07:20:12Z"


def _manifest_document() -> dict[str, object]:
    """Build one contract-shaped incremental Silver COMPLETE document."""
    return {
        "bronze_manifest": {
            "key": (
                "bronze/nvd/cve/updates/"
                f"update_id={UPDATE_ID}/manifest.json"
            ),
            "sha256": BRONZE_SHA,
            "size_bytes": 822,
            "version_id": "bronze-manifest-version-1",
        },
        "bronze_objects": [
            {
                "key": (
                    "bronze/nvd/cve/updates/"
                    f"update_id={UPDATE_ID}/"
                    f"attempt_id={'d' * 64}/"
                    "page_start=000000/response.json"
                ),
                "page_start": 0,
                "role": "page",
                "sha256": "e" * 64,
                "size_bytes": 114449,
                "source_timestamp": "2026-08-24T22:24:23.740",
                "version_id": "bronze-page-version-1",
            }
        ],
        "completion_status": "complete",
        "dataset": "nvd_cve_versions",
        "logical_record_set_sha256": LOGICAL_SHA,
        "manifest_version": "1",
        "schema_version": 1,
        "silver_object": {
            "key": PARQUET_KEY,
            "row_count": 34,
            "sha256": PARQUET_SHA,
            "size_bytes": len(PARQUET_BYTES),
            "version_id": PARQUET_VERSION,
        },
        "source_batch_id": UPDATE_ID,
        "source_coordinates": {
            "total_results": 34,
            "update_id": UPDATE_ID,
            "window_end_at": END,
            "window_start_at": START,
        },
        "source_kind": "incremental",
        "warnings": [],
        "writer_contract_version": 1,
    }


def _manifest_bytes(
    document: dict[str, object] | None = None,
) -> bytes:
    """Serialize fixture bytes deterministically."""
    value = document if document is not None else _manifest_document()
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    ).encode()


class _Reader(NvdPromotionExactObjectReaderV1):
    """In-memory exact-version reader with observable requests."""

    def __init__(
        self,
        *,
        manifest_bytes: bytes | None = None,
        parquet_bytes: bytes = PARQUET_BYTES,
    ) -> None:
        self._manifest_bytes = (
            manifest_bytes if manifest_bytes is not None else _manifest_bytes()
        )
        self._parquet_bytes = parquet_bytes
        self.requests: list[tuple[str, str, int]] = []

    def read_exact(
        self,
        *,
        key: str,
        version_id: str,
        max_bytes: int,
    ) -> NvdPersistedObjectPayloadV1:
        """Return the requested fixture object."""
        self.requests.append((key, version_id, max_bytes))

        if key == MANIFEST_KEY and version_id == MANIFEST_VERSION:
            return NvdPersistedObjectPayloadV1(
                key=key,
                version_id=version_id,
                raw_bytes=self._manifest_bytes,
            )

        if key == PARQUET_KEY and version_id == PARQUET_VERSION:
            return NvdPersistedObjectPayloadV1(
                key=key,
                version_id=version_id,
                raw_bytes=self._parquet_bytes,
            )

        raise AssertionError(
            f"Unexpected exact read: key={key!r} version={version_id!r}"
        )


class _WrongManifestVersionReader(_Reader):
    """Return a different manifest VersionId than the one requested."""

    def read_exact(
        self,
        *,
        key: str,
        version_id: str,
        max_bytes: int,
    ) -> NvdPersistedObjectPayloadV1:
        """Violate exact-version identity for the COMPLETE read."""
        if key == MANIFEST_KEY:
            self.requests.append((key, version_id, max_bytes))
            return NvdPersistedObjectPayloadV1(
                key=key,
                version_id="different-manifest-version",
                raw_bytes=_manifest_bytes(),
            )

        return super().read_exact(
            key=key,
            version_id=version_id,
            max_bytes=max_bytes,
        )


def _ref() -> NvdSilverCompleteRefV1:
    """Build the exact event-selected Silver COMPLETE reference."""
    return NvdSilverCompleteRefV1(
        key=MANIFEST_KEY,
        version_id=MANIFEST_VERSION,
    )


def test_load_reads_exact_manifest_and_declared_parquet_version() -> None:
    """Reconstruct promotion evidence from exact immutable versions."""
    reader = _Reader()

    evidence = NvdWatermarkPromotionEvidenceLoaderV1(
        object_reader=reader,
    ).load(
        silver_complete=_ref(),
    )

    assert evidence.candidate.update_id == UPDATE_ID
    assert evidence.candidate.window_start_at == datetime(
        2026,
        8,
        18,
        7,
        0,
        12,
        tzinfo=UTC,
    )
    assert evidence.candidate.window_end_at == datetime(
        2026,
        8,
        18,
        7,
        20,
        12,
        tzinfo=UTC,
    )
    assert evidence.candidate.total_results == 34
    assert evidence.candidate.page_count == 1
    assert evidence.candidate.bronze_manifest_version_id == (
        "bronze-manifest-version-1"
    )
    assert evidence.silver_manifest.key == MANIFEST_KEY
    assert evidence.silver_manifest.version_id == MANIFEST_VERSION
    assert evidence.silver_parquet.key == PARQUET_KEY
    assert evidence.silver_parquet.version_id == PARQUET_VERSION
    assert evidence.silver_parquet.raw_bytes == PARQUET_BYTES

    assert reader.requests == [
        (
            MANIFEST_KEY,
            MANIFEST_VERSION,
            NvdWatermarkPromotionEvidenceLoaderV1.MAX_SILVER_MANIFEST_BYTES,
        ),
        (
            PARQUET_KEY,
            PARQUET_VERSION,
            NvdWatermarkPromotionEvidenceLoaderV1.MAX_SILVER_PARQUET_BYTES,
        ),
    ]


def test_trigger_key_must_be_canonical_incremental_complete() -> None:
    """Reject a trigger outside the one promotable Silver boundary."""
    bad_ref = NvdSilverCompleteRefV1(
        key=(
            "silver/nvd/cve/schema_version=1/source_kind=bootstrap/"
            "feed_year=2026/manifest.json"
        ),
        version_id=MANIFEST_VERSION,
    )

    with pytest.raises(
        NvdWatermarkPromotionEvidenceLoadError,
        match="canonical incremental Silver COMPLETE",
    ):
        NvdWatermarkPromotionEvidenceLoaderV1(
            object_reader=_Reader(),
        ).load(
            silver_complete=bad_ref,
        )


def test_source_coordinates_update_id_must_match_trigger_key() -> None:
    """Reject COMPLETE bytes that describe another logical update."""
    document = _manifest_document()
    coordinates = document["source_coordinates"]
    assert isinstance(coordinates, dict)
    coordinates["update_id"] = "f" * 64

    with pytest.raises(
        NvdWatermarkPromotionEvidenceLoadError,
        match="source_coordinates update_id",
    ):
        NvdWatermarkPromotionEvidenceLoaderV1(
            object_reader=_Reader(
                manifest_bytes=_manifest_bytes(document),
            ),
        ).load(
            silver_complete=_ref(),
        )


def test_non_incremental_manifest_fails_closed() -> None:
    """Reject a body whose source kind conflicts with the trigger boundary."""
    document = _manifest_document()
    document["source_kind"] = "bootstrap"

    with pytest.raises(
        NvdWatermarkPromotionEvidenceLoadError,
        match="Only incremental",
    ):
        NvdWatermarkPromotionEvidenceLoaderV1(
            object_reader=_Reader(
                manifest_bytes=_manifest_bytes(document),
            ),
        ).load(
            silver_complete=_ref(),
        )


def test_reader_must_return_exact_requested_manifest_version() -> None:
    """Reject an adapter that does not preserve the requested VersionId."""
    with pytest.raises(
        NvdWatermarkPromotionEvidenceLoadError,
        match="different VersionId",
    ):
        NvdWatermarkPromotionEvidenceLoaderV1(
            object_reader=_WrongManifestVersionReader(),
        ).load(
            silver_complete=_ref(),
        )


def test_declared_parquet_size_must_match_exact_bytes() -> None:
    """Reject Parquet bytes whose size differs from COMPLETE evidence."""
    with pytest.raises(
        NvdWatermarkPromotionEvidenceLoadError,
        match="byte size does not match",
    ):
        NvdWatermarkPromotionEvidenceLoaderV1(
            object_reader=_Reader(
                parquet_bytes=b"short",
            ),
        ).load(
            silver_complete=_ref(),
        )


def test_declared_parquet_hash_must_match_exact_bytes() -> None:
    """Reject Parquet bytes that do not match Silver COMPLETE evidence."""
    with pytest.raises(
        NvdWatermarkPromotionEvidenceLoadError,
        match="SHA-256 does not match",
    ):
        NvdWatermarkPromotionEvidenceLoaderV1(
            object_reader=_Reader(
                parquet_bytes=b"X" * len(PARQUET_BYTES),
            ),
        ).load(
            silver_complete=_ref(),
        )


def test_empty_bronze_objects_cannot_reconstruct_candidate() -> None:
    """Reject Silver COMPLETE without a positive Bronze page count."""
    document = _manifest_document()
    document["bronze_objects"] = []

    with pytest.raises(
        NvdWatermarkPromotionEvidenceLoadError,
        match="at least one Bronze page",
    ):
        NvdWatermarkPromotionEvidenceLoaderV1(
            object_reader=_Reader(
                manifest_bytes=_manifest_bytes(document),
            ),
        ).load(
            silver_complete=_ref(),
        )
