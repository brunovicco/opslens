"""Tests for NVD Silver application-boundary models."""

from datetime import UTC, datetime
from hashlib import sha256

import pytest

from opslens.transformation.nvd.application.models import (
    NvdSilverPreparedBatchV1,
    NvdSilverTransformRequestV1,
)
from opslens.transformation.nvd.completion.key_factory import (
    NvdSilverObjectKeysV1,
)
from opslens.transformation.nvd.provenance.models import (
    NvdBronzeObjectPayloadV1,
    NvdBronzeObjectReferenceV1,
    NvdBronzeObjectRole,
    VerifiedNvdBronzeEvidenceV1,
)
from opslens.transformation.nvd.serialization.models import (
    NvdSilverParquetArtifactV1,
    NvdSilverSourceKind,
)


def _incremental_evidence(
    *,
    total_results: int = 0,
) -> VerifiedNvdBronzeEvidenceV1:
    """Build valid verified incremental evidence for boundary tests."""
    update_id = "a" * 64

    page = NvdBronzeObjectReferenceV1(
        role=NvdBronzeObjectRole.PAGE,
        key=(f"bronze/nvd/cve/updates/update_id={update_id}/page_start=000000/response.json"),
        version_id="page-version-1",
        size_bytes=2,
        sha256="b" * 64,
        page_start=0,
        source_timestamp="2026-08-21T12:00:00.000",
    )

    return VerifiedNvdBronzeEvidenceV1(
        source_kind=NvdSilverSourceKind.INCREMENTAL,
        source_batch_id=update_id,
        manifest_key=(f"bronze/nvd/cve/updates/update_id={update_id}/manifest.json"),
        manifest_version_id="manifest-version-1",
        manifest_sha256="c" * 64,
        manifest_size_bytes=123,
        objects=(page,),
        bootstrap_feed_year=None,
        bootstrap_feed_revision=None,
        bootstrap_source_observed_at=None,
        incremental_update_id=update_id,
        incremental_total_results=total_results,
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


def _empty_incremental_artifact(
    *,
    source_batch_id: str,
) -> NvdSilverParquetArtifactV1:
    """Build minimal valid zero-row Parquet framing for model tests."""
    parquet_bytes = b"PAR1PAR1"

    return NvdSilverParquetArtifactV1(
        parquet_bytes=parquet_bytes,
        parquet_sha256=sha256(parquet_bytes).hexdigest(),
        row_count=0,
        size_bytes=len(parquet_bytes),
        schema_version=1,
        source_kind=NvdSilverSourceKind.INCREMENTAL,
        source_batch_id=source_batch_id,
    )


def _keys() -> NvdSilverObjectKeysV1:
    """Return distinct deterministic-looking Silver destinations."""
    return NvdSilverObjectKeysV1(
        parquet_key="silver/nvd/cve/part-00000.parquet",
        manifest_key="silver/nvd/cve/manifest.json",
    )


def test_transform_request_accepts_exact_transport_envelope() -> None:
    """Carry exact object coordinates without declaring them verified."""
    payload = NvdBronzeObjectPayloadV1(
        key="bronze/nvd/cve/page.json",
        version_id="page-version-1",
        raw_bytes=b"{}",
    )

    request = NvdSilverTransformRequestV1(
        source_kind=NvdSilverSourceKind.INCREMENTAL,
        manifest_key="bronze/nvd/cve/manifest.json",
        manifest_version_id="manifest-version-1",
        manifest_bytes=b"{}\n",
        object_payloads=(payload,),
    )

    assert request.object_payloads == (payload,)


def test_transform_request_rejects_empty_manifest_bytes() -> None:
    """Do not start orchestration without the exact manifest payload."""
    with pytest.raises(
        ValueError,
        match="manifest_bytes",
    ):
        NvdSilverTransformRequestV1(
            source_kind=NvdSilverSourceKind.INCREMENTAL,
            manifest_key="bronze/nvd/cve/manifest.json",
            manifest_version_id="manifest-version-1",
            manifest_bytes=b"",
            object_payloads=(),
        )


def test_prepared_batch_accepts_zero_result_incremental_source() -> None:
    """Preserve the frozen zero-result incremental Silver contract."""
    evidence = _incremental_evidence(
        total_results=0,
    )

    prepared = NvdSilverPreparedBatchV1(
        evidence=evidence,
        records=(),
        parquet_artifact=_empty_incremental_artifact(
            source_batch_id=evidence.source_batch_id,
        ),
        keys=_keys(),
    )

    assert prepared.parquet_artifact.row_count == 0
    assert prepared.records == ()


def test_prepared_batch_rejects_source_batch_mismatch() -> None:
    """Prevent a physical artifact from being bound to another Bronze batch."""
    evidence = _incremental_evidence()

    with pytest.raises(
        ValueError,
        match="source_batch_id",
    ):
        NvdSilverPreparedBatchV1(
            evidence=evidence,
            records=(),
            parquet_artifact=_empty_incremental_artifact(
                source_batch_id="different-batch",
            ),
            keys=_keys(),
        )


def test_prepared_batch_rejects_incremental_cardinality_mismatch() -> None:
    """Fail before persistence when Bronze and Silver cardinality diverge."""
    evidence = _incremental_evidence(
        total_results=1,
    )

    with pytest.raises(
        ValueError,
        match="total_results",
    ):
        NvdSilverPreparedBatchV1(
            evidence=evidence,
            records=(),
            parquet_artifact=_empty_incremental_artifact(
                source_batch_id=evidence.source_batch_id,
            ),
            keys=_keys(),
        )
