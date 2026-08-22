# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false
"""Tests for deterministic NVD Silver Parquet serialization."""

from datetime import UTC, datetime
from hashlib import sha256

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from opslens.transformation.nvd.domain.canonicalization import (
    canonicalize_nvd_cve,
    sha256_hex,
)
from opslens.transformation.nvd.domain.models import (
    NvdCpeConfigurations,
    NvdCveCollections,
    NvdCveCoreRecord,
    NvdCvssMetrics,
    NvdLocalizedText,
    NvdVulnerabilityStatus,
    ObservedCveVersion,
)
from opslens.transformation.nvd.serialization.models import (
    NvdSilverProvenanceV1,
    NvdSilverRecordV1,
    NvdSilverSourceKind,
)
from opslens.transformation.nvd.serialization.parquet import (
    NVD_PARQUET_COMPRESSION,
    NVD_PARQUET_DATA_PAGE_VERSION,
    NVD_PARQUET_FORMAT_VERSION,
    NVD_PARQUET_ROW_GROUP_SIZE,
    NVD_PARQUET_WRITER_CONTRACT_VERSION,
    NvdSilverParquetSerializerV1,
)
from opslens.transformation.nvd.serialization.schema import (
    NVD_CVE_VERSIONS_SCHEMA_V1,
)


def _record(
    *,
    cve_id: str,
    observation_id: str,
    record_index: int,
    source_batch_id: str = "update-20260821T120000Z",
) -> NvdSilverRecordV1:
    """Build one minimal complete serialization record."""
    source_cve: dict[str, object] = {
        "id": cve_id,
        "futureField": {
            "recordIndex": record_index,
        },
    }

    canonical = canonicalize_nvd_cve(source_cve)

    observed = ObservedCveVersion(
        cve_id=cve_id,
        canonical_json=canonical,
        source_cve_sha256=sha256_hex(canonical),
    )

    core = NvdCveCoreRecord(
        observed_version=observed,
        source_identifier="security@example.com",
        published_at=datetime(
            2026,
            8,
            20,
            10,
            0,
            tzinfo=UTC,
        ),
        last_modified_at=datetime(
            2026,
            8,
            21,
            11,
            0,
            tzinfo=UTC,
        ),
        vuln_status=NvdVulnerabilityStatus.ANALYZED,
    )

    collections = NvdCveCollections(
        descriptions=(
            NvdLocalizedText(
                lang="en",
                value=f"Description for {cve_id}.",
            ),
        ),
        cve_tags=(),
        weaknesses=(),
        references=(),
    )

    provenance = NvdSilverProvenanceV1(
        source_kind=NvdSilverSourceKind.INCREMENTAL,
        source_batch_id=source_batch_id,
        observation_id=observation_id,
        source_observed_at=datetime(
            2026,
            8,
            21,
            12,
            0,
            tzinfo=UTC,
        ),
        bronze_manifest_key=(f"bronze/nvd/cve/updates/update_id={source_batch_id}/manifest.json"),
        bronze_manifest_version_id="manifest-version-1",
        bronze_manifest_sha256="a" * 64,
        bronze_object_key=(
            "bronze/nvd/cve/updates/"
            f"update_id={source_batch_id}/"
            f"page_start={record_index:06d}/response.json"
        ),
        bronze_object_version_id=(f"object-version-{record_index}"),
        bronze_object_sha256="b" * 64,
        bronze_record_index=record_index,
        bootstrap_feed_year=None,
        bootstrap_feed_revision=None,
        incremental_update_id=source_batch_id,
        incremental_page_start=0,
    )

    return NvdSilverRecordV1(
        core=core,
        collections=collections,
        cvss=NvdCvssMetrics(
            metrics=(),
            unsupported_cvss_families=(),
        ),
        configurations=NvdCpeConfigurations(
            configurations_json="[]",
            configuration_count=0,
        ),
        provenance=provenance,
    )


def test_writer_contract_settings_are_explicit() -> None:
    """Freeze the physical Parquet writer contract separately from schema v1."""
    assert NVD_PARQUET_WRITER_CONTRACT_VERSION == 1
    assert NVD_PARQUET_FORMAT_VERSION == "1.0"
    assert NVD_PARQUET_DATA_PAGE_VERSION == "1.0"
    assert NVD_PARQUET_COMPRESSION == "snappy"
    assert NVD_PARQUET_ROW_GROUP_SIZE == 5_000


def test_empty_record_set_fails_closed() -> None:
    """Do not create ambiguous empty Silver Parquet artifacts."""
    with pytest.raises(
        ValueError,
        match="at least one record",
    ):
        NvdSilverParquetSerializerV1().serialize([])


def test_mixed_source_batches_fail_closed() -> None:
    """Require one physical artifact to map to one source batch."""
    first = _record(
        cve_id="CVE-2026-10001",
        observation_id="obs-1",
        record_index=0,
        source_batch_id="batch-a",
    )
    second = _record(
        cve_id="CVE-2026-10002",
        observation_id="obs-2",
        record_index=1,
        source_batch_id="batch-b",
    )

    with pytest.raises(
        ValueError,
        match="source_batch_id",
    ):
        NvdSilverParquetSerializerV1().serialize(
            [
                first,
                second,
            ]
        )


def test_duplicate_observation_id_fails_closed() -> None:
    """Reject duplicate physical observations before serialization."""
    first = _record(
        cve_id="CVE-2026-10001",
        observation_id="same-observation",
        record_index=0,
    )
    second = _record(
        cve_id="CVE-2026-10002",
        observation_id="same-observation",
        record_index=1,
    )

    with pytest.raises(
        ValueError,
        match="duplicate observation_id",
    ):
        NvdSilverParquetSerializerV1().serialize(
            [
                first,
                second,
            ]
        )


def test_input_order_does_not_change_parquet_bytes() -> None:
    """Canonical sorting makes equivalent record sets byte-identical."""
    first = _record(
        cve_id="CVE-2026-20002",
        observation_id="obs-2",
        record_index=2,
    )
    second = _record(
        cve_id="CVE-2026-10001",
        observation_id="obs-1",
        record_index=1,
    )

    serializer = NvdSilverParquetSerializerV1()

    forward = serializer.serialize(
        [
            first,
            second,
        ]
    )
    reverse = serializer.serialize(
        [
            second,
            first,
        ]
    )

    assert forward.parquet_bytes == reverse.parquet_bytes
    assert forward.parquet_sha256 == reverse.parquet_sha256


def test_replay_is_byte_for_byte_deterministic() -> None:
    """Serialize the same logical artifact twice with identical bytes."""
    records = [
        _record(
            cve_id="CVE-2026-10001",
            observation_id="obs-1",
            record_index=1,
        ),
        _record(
            cve_id="CVE-2026-10002",
            observation_id="obs-2",
            record_index=2,
        ),
    ]

    serializer = NvdSilverParquetSerializerV1()

    first = serializer.serialize(records)
    replay = serializer.serialize(records)

    assert first.parquet_bytes == replay.parquet_bytes
    assert first.parquet_sha256 == replay.parquet_sha256


def test_parquet_round_trip_preserves_schema_and_canonical_order() -> None:
    """Read the artifact back using the frozen Arrow schema."""
    later = _record(
        cve_id="CVE-2026-90000",
        observation_id="obs-later",
        record_index=9,
    )
    earlier = _record(
        cve_id="CVE-2026-10000",
        observation_id="obs-earlier",
        record_index=1,
    )

    artifact = NvdSilverParquetSerializerV1().serialize(
        [
            later,
            earlier,
        ]
    )

    table = pq.read_table(pa.BufferReader(artifact.parquet_bytes))

    assert table.schema == NVD_CVE_VERSIONS_SCHEMA_V1
    assert table.num_rows == 2

    rows = table.to_pylist()

    assert [row["cve_id"] for row in rows] == [
        "CVE-2026-10000",
        "CVE-2026-90000",
    ]

    parquet_file = pq.ParquetFile(pa.BufferReader(artifact.parquet_bytes))

    assert parquet_file.metadata.num_row_groups == 1
    assert parquet_file.metadata.row_group(0).column(0).compression == "SNAPPY"


def test_artifact_exposes_exact_payload_hash_and_size() -> None:
    """Bind artifact metadata to the exact emitted Parquet bytes."""
    artifact = NvdSilverParquetSerializerV1().serialize(
        [
            _record(
                cve_id="CVE-2026-12345",
                observation_id="obs-12345",
                record_index=0,
            )
        ]
    )

    assert artifact.parquet_bytes.startswith(b"PAR1")
    assert artifact.parquet_bytes.endswith(b"PAR1")
    assert artifact.size_bytes == len(artifact.parquet_bytes)
    assert artifact.parquet_sha256 == sha256(artifact.parquet_bytes).hexdigest()
    assert artifact.row_count == 1
    assert artifact.schema_version == 1


def test_explicit_empty_incremental_parquet_is_valid() -> None:
    """Represent a proven zero-result incremental batch with schema v1."""
    artifact = NvdSilverParquetSerializerV1().serialize_empty(
        source_kind=NvdSilverSourceKind.INCREMENTAL,
        source_batch_id="a" * 64,
    )

    assert artifact.row_count == 0
    assert artifact.parquet_bytes.startswith(b"PAR1")
    assert artifact.parquet_bytes.endswith(b"PAR1")

    table = pq.read_table(pa.BufferReader(artifact.parquet_bytes))

    assert table.num_rows == 0
    assert table.schema == NVD_CVE_VERSIONS_SCHEMA_V1


def test_explicit_empty_incremental_parquet_replays_identically() -> None:
    """Keep zero-result physical evidence byte deterministic."""
    serializer = NvdSilverParquetSerializerV1()

    first = serializer.serialize_empty(
        source_kind=NvdSilverSourceKind.INCREMENTAL,
        source_batch_id="a" * 64,
    )
    replay = serializer.serialize_empty(
        source_kind=NvdSilverSourceKind.INCREMENTAL,
        source_batch_id="a" * 64,
    )

    assert first.parquet_bytes == replay.parquet_bytes
    assert first.parquet_sha256 == replay.parquet_sha256


def test_explicit_empty_bootstrap_parquet_fails_closed() -> None:
    """Do not generalize incremental zero-result semantics to bootstrap."""
    with pytest.raises(
        ValueError,
        match="only for incremental",
    ):
        NvdSilverParquetSerializerV1().serialize_empty(
            source_kind=NvdSilverSourceKind.BOOTSTRAP,
            source_batch_id="bootstrap-batch",
        )
