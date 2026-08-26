"""Unit tests for authoritative NVD incremental watermark semantics."""

import json
from datetime import UTC, datetime, timedelta, timezone

import pytest

from opslens.ingestion.nvd.application.authoritative_watermark import (
    NvdAuthoritativeWatermarkParserV1,
    NvdAuthoritativeWatermarkSerializerV1,
    NvdAuthoritativeWatermarkV1,
    NvdWatermarkBootstrapRecoverySeedV1,
    NvdWatermarkEvidenceObjectV1,
    NvdWatermarkSilverPromotionCommitV1,
)


def _evidence_object(
    *,
    key: str = "evidence/object.json",
    version_id: str = "version-123",
    sha256: str = "a" * 64,
) -> NvdWatermarkEvidenceObjectV1:
    """Build one deterministic immutable evidence reference."""
    return NvdWatermarkEvidenceObjectV1(
        key=key,
        version_id=version_id,
        sha256=sha256,
    )


def _bootstrap_watermark() -> NvdAuthoritativeWatermarkV1:
    """Build the real recovery-boundary shape used by Phase 2.3F."""
    source_revision = datetime(
        2026,
        8,
        18,
        3,
        0,
        12,
        tzinfo=timezone(timedelta(hours=-4)),
    )

    return NvdAuthoritativeWatermarkV1(
        committed_through_at=source_revision,
        commit_basis=NvdWatermarkBootstrapRecoverySeedV1(
            source_revision_at=source_revision,
            bootstrap_manifest=_evidence_object(
                key=(
                    "bronze/nvd/cve/bootstrap/"
                    "feed_year=2026/"
                    "feed_revision=20260818T070012Z-test/"
                    "manifest.json"
                ),
            ),
        ),
    )


def _promotion_watermark() -> NvdAuthoritativeWatermarkV1:
    """Build one promoted authoritative state."""
    return NvdAuthoritativeWatermarkV1(
        committed_through_at=datetime(
            2026,
            8,
            18,
            9,
            0,
            12,
            tzinfo=UTC,
        ),
        commit_basis=NvdWatermarkSilverPromotionCommitV1(
            previous_committed_through_at=datetime(
                2026,
                8,
                18,
                7,
                0,
                12,
                tzinfo=UTC,
            ),
            update_id="b" * 64,
            bronze_manifest=_evidence_object(
                key="bronze/manifest.json",
                sha256="c" * 64,
            ),
            silver_manifest=_evidence_object(
                key="silver/manifest.json",
                sha256="d" * 64,
            ),
            silver_parquet=_evidence_object(
                key="silver/part-00000.parquet",
                sha256="e" * 64,
            ),
            logical_record_set_sha256="f" * 64,
        ),
    )


def test_bootstrap_recovery_seed_normalizes_source_revision_to_utc() -> None:
    """Use the exact NVD source revision instant as the recovery seed."""
    watermark = _bootstrap_watermark()

    assert watermark.committed_through_at == datetime(
        2026,
        8,
        18,
        7,
        0,
        12,
        tzinfo=UTC,
    )
    assert (
        watermark.canonical_committed_through_at
        == "2026-08-18T07:00:12Z"
    )
    assert isinstance(
        watermark.commit_basis,
        NvdWatermarkBootstrapRecoverySeedV1,
    )
    assert (
        watermark.commit_basis.canonical_source_revision_at
        == "2026-08-18T07:00:12Z"
    )


def test_bootstrap_recovery_seed_cannot_commit_a_different_boundary() -> None:
    """Reject an initial watermark not equal to its source revision."""
    basis = NvdWatermarkBootstrapRecoverySeedV1(
        source_revision_at=datetime(
            2026,
            8,
            18,
            7,
            0,
            12,
            tzinfo=UTC,
        ),
        bootstrap_manifest=_evidence_object(),
    )

    with pytest.raises(
        ValueError,
        match="commit exactly the source revision boundary",
    ):
        NvdAuthoritativeWatermarkV1(
            committed_through_at=datetime(
                2026,
                8,
                18,
                8,
                0,
                12,
                tzinfo=UTC,
            ),
            commit_basis=basis,
        )


def test_bootstrap_serializer_records_recovery_reason() -> None:
    """Make the exceptional initial-boundary provenance explicit."""
    payload = NvdAuthoritativeWatermarkSerializerV1().serialize(
        _bootstrap_watermark()
    )

    document = json.loads(payload)

    assert document["committed_through_at"] == (
        "2026-08-18T07:00:12Z"
    )
    assert document["state"] == "committed"
    assert document["watermark_version"] == "1"

    commit_basis = document["commit_basis"]

    assert commit_basis["kind"] == (
        "bootstrap_source_revision_recovery_seed"
    )
    assert commit_basis["recovery_reason"] == (
        "original_bootstrap_boundary_not_persisted"
    )


def test_bootstrap_serializer_is_retry_stable() -> None:
    """Serialize identical authoritative state to identical bytes."""
    serializer = NvdAuthoritativeWatermarkSerializerV1()
    watermark = _bootstrap_watermark()

    assert serializer.serialize(watermark) == serializer.serialize(
        watermark
    )


def test_parser_round_trips_canonical_bootstrap_state() -> None:
    """Read exact persisted canonical bytes without changing identity."""
    serializer = NvdAuthoritativeWatermarkSerializerV1()
    parser = NvdAuthoritativeWatermarkParserV1(
        serializer=serializer
    )

    payload = serializer.serialize(
        _bootstrap_watermark()
    )

    parsed = parser.parse(payload)

    assert serializer.serialize(parsed) == payload
    assert parsed.committed_through_at == datetime(
        2026,
        8,
        18,
        7,
        0,
        12,
        tzinfo=UTC,
    )


def test_parser_rejects_noncanonical_json() -> None:
    """Reject semantically similar bytes that are not canonical evidence."""
    serializer = NvdAuthoritativeWatermarkSerializerV1()
    canonical = serializer.serialize(
        _bootstrap_watermark()
    )

    document = json.loads(canonical)
    noncanonical = json.dumps(
        document,
        indent=2,
    ).encode()

    with pytest.raises(
        ValueError,
        match="not canonical",
    ):
        NvdAuthoritativeWatermarkParserV1().parse(
            noncanonical
        )


def test_parser_rejects_additive_top_level_field() -> None:
    """Fail closed on unsupported state-contract evolution."""
    serializer = NvdAuthoritativeWatermarkSerializerV1()
    document = json.loads(
        serializer.serialize(
            _bootstrap_watermark()
        )
    )

    document["unexpected"] = "value"

    payload = (
        json.dumps(
            document,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode()

    with pytest.raises(
        ValueError,
        match="fields do not match",
    ):
        NvdAuthoritativeWatermarkParserV1().parse(
            payload
        )


def test_promoted_watermark_must_advance() -> None:
    """Reject a Silver promotion that does not move the boundary."""
    basis = NvdWatermarkSilverPromotionCommitV1(
        previous_committed_through_at=datetime(
            2026,
            8,
            18,
            7,
            0,
            12,
            tzinfo=UTC,
        ),
        update_id="b" * 64,
        bronze_manifest=_evidence_object(
            sha256="c" * 64,
        ),
        silver_manifest=_evidence_object(
            sha256="d" * 64,
        ),
        silver_parquet=_evidence_object(
            sha256="e" * 64,
        ),
        logical_record_set_sha256="f" * 64,
    )

    with pytest.raises(
        ValueError,
        match="must advance",
    ):
        NvdAuthoritativeWatermarkV1(
            committed_through_at=datetime(
                2026,
                8,
                18,
                7,
                0,
                12,
                tzinfo=UTC,
            ),
            commit_basis=basis,
        )


def test_parser_round_trips_promoted_state() -> None:
    """Preserve exact promotion evidence in committed-state bytes."""
    serializer = NvdAuthoritativeWatermarkSerializerV1()
    payload = serializer.serialize(
        _promotion_watermark()
    )

    parsed = NvdAuthoritativeWatermarkParserV1().parse(
        payload
    )

    assert serializer.serialize(parsed) == payload
    assert isinstance(
        parsed.commit_basis,
        NvdWatermarkSilverPromotionCommitV1,
    )
    assert (
        parsed.commit_basis.previous_committed_through_at
        == datetime(
            2026,
            8,
            18,
            7,
            0,
            12,
            tzinfo=UTC,
        )
    )
