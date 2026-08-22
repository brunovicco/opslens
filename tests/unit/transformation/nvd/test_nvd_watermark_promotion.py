"""Tests for deterministic NVD watermark promotion eligibility."""

import json
from datetime import UTC, datetime
from hashlib import sha256

import pytest

from opslens.ingestion.nvd.application.watermark import (
    NvdWatermarkCandidate,
)
from opslens.transformation.nvd.completion.promotion import (
    InvalidNvdWatermarkPromotionEvidenceError,
    NvdPersistedObjectPayloadV1,
    NvdWatermarkPromotionEligibilitySerializerV1,
    NvdWatermarkPromotionVerifierV1,
)
from opslens.transformation.nvd.serialization.parquet import (
    NVD_PARQUET_WRITER_CONTRACT_VERSION,
)
from opslens.transformation.nvd.serialization.schema import (
    NVD_CVE_VERSIONS_SCHEMA_NAME,
    NVD_CVE_VERSIONS_SCHEMA_VERSION,
)

PARQUET_BYTES = b"PAR1opslens-nvd-silver-testPAR1"
PARQUET_SHA256 = sha256(PARQUET_BYTES).hexdigest()


def _candidate(
    *,
    total_results: int = 1,
    page_count: int = 1,
) -> NvdWatermarkCandidate:
    """Build one Bronze-complete incremental watermark candidate."""
    return NvdWatermarkCandidate(
        update_id="a" * 64,
        window_start_at=datetime(
            2026,
            8,
            20,
            tzinfo=UTC,
        ),
        window_end_at=datetime(
            2026,
            8,
            21,
            tzinfo=UTC,
        ),
        bronze_manifest_key=(f"bronze/nvd/cve/updates/update_id={'a' * 64}/manifest.json"),
        bronze_manifest_version_id="bronze-manifest-version-1",
        bronze_manifest_sha256="b" * 64,
        total_results=total_results,
        page_count=page_count,
    )


def _silver_base(
    candidate: NvdWatermarkCandidate,
) -> str:
    """Return deterministic Silver incremental batch prefix."""
    return (
        "silver/nvd/cve/"
        f"schema_version={NVD_CVE_VERSIONS_SCHEMA_VERSION}/"
        "source_kind=incremental/"
        f"update_id={candidate.update_id}"
    )


def _manifest_document(
    candidate: NvdWatermarkCandidate,
    *,
    warnings: list[str] | None = None,
) -> dict[str, object]:
    """Build one valid persisted Silver COMPLETE document."""
    base = _silver_base(candidate)

    pages: list[dict[str, object]] = []

    for index in range(candidate.page_count):
        pages.append(
            {
                "key": (
                    "bronze/nvd/cve/updates/"
                    f"update_id={candidate.update_id}/"
                    f"page_start={index:06d}/response.json"
                ),
                "page_start": index,
                "role": "page",
                "sha256": f"{index + 1:064x}",
                "size_bytes": 100 + index,
                "source_timestamp": ("2026-08-21T12:00:00.000"),
                "version_id": f"bronze-page-version-{index}",
            }
        )

    return {
        "bronze_manifest": {
            "key": candidate.bronze_manifest_key,
            "sha256": candidate.bronze_manifest_sha256,
            "size_bytes": 500,
            "version_id": candidate.bronze_manifest_version_id,
        },
        "bronze_objects": pages,
        "completion_status": "complete",
        "dataset": NVD_CVE_VERSIONS_SCHEMA_NAME,
        "logical_record_set_sha256": "c" * 64,
        "manifest_version": "1",
        "schema_version": NVD_CVE_VERSIONS_SCHEMA_VERSION,
        "silver_object": {
            "key": f"{base}/part-00000.parquet",
            "row_count": candidate.total_results,
            "sha256": PARQUET_SHA256,
            "size_bytes": len(PARQUET_BYTES),
            "version_id": "silver-parquet-version-1",
        },
        "source_batch_id": candidate.update_id,
        "source_coordinates": {
            "total_results": candidate.total_results,
            "update_id": candidate.update_id,
            "window_end_at": candidate.canonical_window_end_at,
            "window_start_at": candidate.canonical_window_start_at,
        },
        "source_kind": "incremental",
        "warnings": warnings if warnings is not None else [],
        "writer_contract_version": (NVD_PARQUET_WRITER_CONTRACT_VERSION),
    }


def _canonical_bytes(
    document: dict[str, object],
) -> bytes:
    """Serialize one Silver document using the internal canonical form."""
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


def _persisted_evidence(
    candidate: NvdWatermarkCandidate,
    *,
    document: dict[str, object] | None = None,
    parquet_bytes: bytes = PARQUET_BYTES,
    parquet_version_id: str = "silver-parquet-version-1",
) -> tuple[
    NvdPersistedObjectPayloadV1,
    NvdPersistedObjectPayloadV1,
]:
    """Build exact persisted Silver manifest and Parquet evidence."""
    base = _silver_base(candidate)

    manifest_document = document if document is not None else _manifest_document(candidate)

    manifest = NvdPersistedObjectPayloadV1(
        key=f"{base}/manifest.json",
        version_id="silver-manifest-version-1",
        raw_bytes=_canonical_bytes(manifest_document),
    )

    parquet = NvdPersistedObjectPayloadV1(
        key=f"{base}/part-00000.parquet",
        version_id=parquet_version_id,
        raw_bytes=parquet_bytes,
    )

    return manifest, parquet


def test_verified_silver_completion_is_promotion_eligible() -> None:
    """Promote only exact persisted Silver evidence."""
    candidate = _candidate()
    manifest, parquet = _persisted_evidence(candidate)

    eligibility = NvdWatermarkPromotionVerifierV1().verify(
        committed_through_at=candidate.window_start_at,
        candidate=candidate,
        silver_manifest=manifest,
        silver_parquet=parquet,
    )

    assert eligibility.ELIGIBLE is True
    assert eligibility.STATE == "silver_complete"
    assert eligibility.update_id == candidate.update_id
    assert eligibility.row_count == 1
    assert eligibility.total_results == 1
    assert eligibility.next_committed_through_at == (candidate.window_end_at)


def test_zero_result_silver_completion_is_promotion_eligible() -> None:
    """Allow a proven zero-result incremental window to advance."""
    candidate = _candidate(
        total_results=0,
    )
    manifest, parquet = _persisted_evidence(candidate)

    eligibility = NvdWatermarkPromotionVerifierV1().verify(
        committed_through_at=candidate.window_start_at,
        candidate=candidate,
        silver_manifest=manifest,
        silver_parquet=parquet,
    )

    assert eligibility.ELIGIBLE is True
    assert eligibility.row_count == 0
    assert eligibility.total_results == 0


def test_gap_or_overlap_candidate_is_not_eligible() -> None:
    """Bind eligibility to the exact currently committed boundary."""
    candidate = _candidate()
    manifest, parquet = _persisted_evidence(candidate)

    with pytest.raises(
        InvalidNvdWatermarkPromotionEvidenceError,
        match="current committed boundary",
    ):
        NvdWatermarkPromotionVerifierV1().verify(
            committed_through_at=datetime(
                2026,
                8,
                19,
                tzinfo=UTC,
            ),
            candidate=candidate,
            silver_manifest=manifest,
            silver_parquet=parquet,
        )


def test_noncanonical_silver_manifest_is_not_eligible() -> None:
    """Require persisted COMPLETE bytes to match canonical contract."""
    candidate = _candidate()
    document = _manifest_document(candidate)

    base = _silver_base(candidate)

    noncanonical = json.dumps(
        document,
        indent=2,
    ).encode("utf-8")

    manifest = NvdPersistedObjectPayloadV1(
        key=f"{base}/manifest.json",
        version_id="silver-manifest-version-1",
        raw_bytes=noncanonical,
    )

    parquet = NvdPersistedObjectPayloadV1(
        key=f"{base}/part-00000.parquet",
        version_id="silver-parquet-version-1",
        raw_bytes=PARQUET_BYTES,
    )

    with pytest.raises(
        InvalidNvdWatermarkPromotionEvidenceError,
        match="not canonical",
    ):
        NvdWatermarkPromotionVerifierV1().verify(
            committed_through_at=candidate.window_start_at,
            candidate=candidate,
            silver_manifest=manifest,
            silver_parquet=parquet,
        )


def test_bronze_manifest_version_mismatch_is_not_eligible() -> None:
    """Require Silver to bind the same exact Bronze manifest."""
    candidate = _candidate()
    document = _manifest_document(candidate)

    bronze = document["bronze_manifest"]
    assert isinstance(bronze, dict)
    bronze["version_id"] = "wrong-bronze-version"

    manifest, parquet = _persisted_evidence(
        candidate,
        document=document,
    )

    with pytest.raises(
        InvalidNvdWatermarkPromotionEvidenceError,
        match="Bronze VersionId",
    ):
        NvdWatermarkPromotionVerifierV1().verify(
            committed_through_at=candidate.window_start_at,
            candidate=candidate,
            silver_manifest=manifest,
            silver_parquet=parquet,
        )


def test_source_window_mismatch_is_not_eligible() -> None:
    """Require Silver coordinates to equal candidate coordinates."""
    candidate = _candidate()
    document = _manifest_document(candidate)

    coordinates = document["source_coordinates"]
    assert isinstance(coordinates, dict)
    coordinates["window_end_at"] = "2026-08-22T00:00:00Z"

    manifest, parquet = _persisted_evidence(
        candidate,
        document=document,
    )

    with pytest.raises(
        InvalidNvdWatermarkPromotionEvidenceError,
        match="window end",
    ):
        NvdWatermarkPromotionVerifierV1().verify(
            committed_through_at=candidate.window_start_at,
            candidate=candidate,
            silver_manifest=manifest,
            silver_parquet=parquet,
        )


def test_row_count_mismatch_is_not_eligible() -> None:
    """Do not advance when Silver cardinality differs from Bronze."""
    candidate = _candidate(
        total_results=2,
    )
    document = _manifest_document(candidate)

    silver = document["silver_object"]
    assert isinstance(silver, dict)
    silver["row_count"] = 1

    manifest, parquet = _persisted_evidence(
        candidate,
        document=document,
    )

    with pytest.raises(
        InvalidNvdWatermarkPromotionEvidenceError,
        match="row_count",
    ):
        NvdWatermarkPromotionVerifierV1().verify(
            committed_through_at=candidate.window_start_at,
            candidate=candidate,
            silver_manifest=manifest,
            silver_parquet=parquet,
        )


def test_persisted_parquet_version_mismatch_is_not_eligible() -> None:
    """Require the exact persisted Silver Parquet VersionId."""
    candidate = _candidate()
    manifest, parquet = _persisted_evidence(
        candidate,
        parquet_version_id="wrong-version",
    )

    with pytest.raises(
        InvalidNvdWatermarkPromotionEvidenceError,
        match="Parquet VersionId",
    ):
        NvdWatermarkPromotionVerifierV1().verify(
            committed_through_at=candidate.window_start_at,
            candidate=candidate,
            silver_manifest=manifest,
            silver_parquet=parquet,
        )


def test_persisted_parquet_hash_mismatch_is_not_eligible() -> None:
    """Require exact persisted Silver Parquet bytes."""
    candidate = _candidate()

    document = _manifest_document(candidate)
    manifest, parquet = _persisted_evidence(
        candidate,
        document=document,
        parquet_bytes=b"PAR1different-persisted-bytesPAR1",
    )

    with pytest.raises(
        InvalidNvdWatermarkPromotionEvidenceError,
        match="Parquet SHA-256",
    ):
        NvdWatermarkPromotionVerifierV1().verify(
            committed_through_at=candidate.window_start_at,
            candidate=candidate,
            silver_manifest=manifest,
            silver_parquet=parquet,
        )


def test_page_inventory_count_mismatch_is_not_eligible() -> None:
    """Require candidate page_count to match Silver Bronze inventory."""
    candidate = _candidate(
        page_count=2,
    )
    document = _manifest_document(candidate)

    pages = document["bronze_objects"]
    assert isinstance(pages, list)
    pages.pop()

    manifest, parquet = _persisted_evidence(
        candidate,
        document=document,
    )

    with pytest.raises(
        InvalidNvdWatermarkPromotionEvidenceError,
        match="page inventory count",
    ):
        NvdWatermarkPromotionVerifierV1().verify(
            committed_through_at=candidate.window_start_at,
            candidate=candidate,
            silver_manifest=manifest,
            silver_parquet=parquet,
        )


def test_warnings_do_not_block_promotion() -> None:
    """Preserve non-fatal Silver warnings without denying completion."""
    candidate = _candidate()
    document = _manifest_document(
        candidate,
        warnings=[
            "unsupported_cvss_family:cvssMetricV50",
        ],
    )

    manifest, parquet = _persisted_evidence(
        candidate,
        document=document,
    )

    eligibility = NvdWatermarkPromotionVerifierV1().verify(
        committed_through_at=candidate.window_start_at,
        candidate=candidate,
        silver_manifest=manifest,
        silver_parquet=parquet,
    )

    assert eligibility.ELIGIBLE is True
    assert eligibility.warning_count == 1


def test_unknown_manifest_field_is_not_eligible() -> None:
    """Fail closed on internal Silver manifest contract drift."""
    candidate = _candidate()
    document = _manifest_document(candidate)
    document["unexpected"] = "drift"

    manifest, parquet = _persisted_evidence(
        candidate,
        document=document,
    )

    with pytest.raises(
        InvalidNvdWatermarkPromotionEvidenceError,
        match="fields do not match",
    ):
        NvdWatermarkPromotionVerifierV1().verify(
            committed_through_at=candidate.window_start_at,
            candidate=candidate,
            silver_manifest=manifest,
            silver_parquet=parquet,
        )


def test_promotion_eligibility_serialization_is_deterministic() -> None:
    """Keep eligibility proof byte-stable across replay."""
    candidate = _candidate()
    manifest, parquet = _persisted_evidence(candidate)

    verifier = NvdWatermarkPromotionVerifierV1()

    eligibility = verifier.verify(
        committed_through_at=candidate.window_start_at,
        candidate=candidate,
        silver_manifest=manifest,
        silver_parquet=parquet,
    )

    serializer = NvdWatermarkPromotionEligibilitySerializerV1()

    first = serializer.serialize(eligibility)
    replay = serializer.serialize(eligibility)

    assert first == replay

    document = json.loads(first)

    assert document["eligible"] is True
    assert document["state"] == "silver_complete"
    assert document["update_id"] == candidate.update_id
    assert "generated_at" not in document
    assert "created_at" not in document
