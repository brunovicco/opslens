"""Tests for deterministic NVD Silver COMPLETE evidence."""

import json
from dataclasses import replace
from datetime import UTC, datetime
from hashlib import sha256

import pytest

from opslens.transformation.nvd.completion.key_factory import (
    NvdSilverKeyFactoryV1,
)
from opslens.transformation.nvd.completion.manifest import (
    NvdSilverCompletionManifestFactoryV1,
    NvdSilverCompletionManifestSerializerV1,
)
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
from opslens.transformation.nvd.provenance.models import (
    NvdBronzeObjectReferenceV1,
    NvdBronzeObjectRole,
    VerifiedNvdBronzeEvidenceV1,
)
from opslens.transformation.nvd.provenance.verifier import (
    NvdSilverProvenanceFactoryV1,
)
from opslens.transformation.nvd.serialization.logical_hash import (
    NvdLogicalRecordSetHasherV1,
)
from opslens.transformation.nvd.serialization.models import (
    NvdSilverRecordV1,
    NvdSilverSourceKind,
)
from opslens.transformation.nvd.serialization.parquet import (
    NvdSilverParquetSerializerV1,
)


def _incremental_evidence() -> VerifiedNvdBronzeEvidenceV1:
    """Build verified incremental evidence for completion tests."""
    update_id = "a" * 64

    page = NvdBronzeObjectReferenceV1(
        role=NvdBronzeObjectRole.PAGE,
        key=(f"bronze/nvd/cve/updates/update_id={update_id}/page_start=000000/response.json"),
        version_id="page-version-1",
        size_bytes=123,
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
        manifest_size_bytes=456,
        objects=(page,),
        bootstrap_feed_year=None,
        bootstrap_feed_revision=None,
        bootstrap_source_observed_at=None,
        incremental_update_id=update_id,
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


def _bootstrap_evidence() -> VerifiedNvdBronzeEvidenceV1:
    """Build verified bootstrap evidence for key tests."""
    revision = "20260821T000000Z-" + ("d" * 64)

    feed = NvdBronzeObjectReferenceV1(
        role=NvdBronzeObjectRole.FEED,
        key=(
            "bronze/nvd/cve/bootstrap/"
            f"feed_year=2026/feed_revision={revision}/"
            "nvdcve-2.0-2026.json.gz"
        ),
        version_id="feed-version-1",
        size_bytes=100,
        sha256="e" * 64,
        page_start=None,
        source_timestamp=None,
    )

    meta = NvdBronzeObjectReferenceV1(
        role=NvdBronzeObjectRole.META,
        key=(
            f"bronze/nvd/cve/bootstrap/feed_year=2026/feed_revision={revision}/nvdcve-2.0-2026.meta"
        ),
        version_id="meta-version-1",
        size_bytes=50,
        sha256="f" * 64,
        page_start=None,
        source_timestamp=None,
    )

    return VerifiedNvdBronzeEvidenceV1(
        source_kind=NvdSilverSourceKind.BOOTSTRAP,
        source_batch_id=(f"feed_year=2026/feed_revision={revision}"),
        manifest_key=(
            f"bronze/nvd/cve/bootstrap/feed_year=2026/feed_revision={revision}/manifest.json"
        ),
        manifest_version_id="manifest-version-1",
        manifest_sha256="1" * 64,
        manifest_size_bytes=222,
        objects=(feed, meta),
        bootstrap_feed_year=2026,
        bootstrap_feed_revision=revision,
        bootstrap_source_observed_at=datetime(
            2026,
            8,
            21,
            tzinfo=UTC,
        ),
        incremental_update_id=None,
        incremental_window_start_at=None,
        incremental_window_end_at=None,
    )


def _record(
    *,
    cve_id: str,
    record_index: int,
    evidence: VerifiedNvdBronzeEvidenceV1,
    unsupported: tuple[str, ...] = (),
) -> NvdSilverRecordV1:
    """Build one complete Silver record bound to verified evidence."""
    source_cve: dict[str, object] = {
        "id": cve_id,
        "recordIndex": record_index,
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

    provenance = NvdSilverProvenanceFactoryV1().build(
        evidence=evidence,
        bronze_object_key=evidence.objects[0].key,
        record_index=record_index,
    )

    return NvdSilverRecordV1(
        core=core,
        collections=collections,
        cvss=NvdCvssMetrics(
            metrics=(),
            unsupported_cvss_families=unsupported,
        ),
        configurations=NvdCpeConfigurations(
            configurations_json="[]",
            configuration_count=0,
        ),
        provenance=provenance,
    )


def test_incremental_silver_keys_are_deterministic() -> None:
    """Use source identity rather than runtime time in Silver paths."""
    evidence = _incremental_evidence()

    keys = NvdSilverKeyFactoryV1().build(evidence)

    assert keys.parquet_key == (
        "silver/nvd/cve/schema_version=1/"
        "source_kind=incremental/"
        f"update_id={evidence.incremental_update_id}/"
        "part-00000.parquet"
    )

    assert keys.manifest_key.endswith("/manifest.json")


def test_bootstrap_silver_keys_preserve_feed_identity() -> None:
    """Partition Bootstrap Silver by exact feed revision."""
    evidence = _bootstrap_evidence()

    keys = NvdSilverKeyFactoryV1().build(evidence)

    assert "/source_kind=bootstrap/feed_year=2026/" in keys.parquet_key

    assert f"feed_revision={evidence.bootstrap_feed_revision}/" in keys.parquet_key


def test_logical_hash_is_independent_of_input_order() -> None:
    """Hash the record set rather than caller iteration order."""
    evidence = _incremental_evidence()

    first = _record(
        cve_id="CVE-2026-10001",
        record_index=0,
        evidence=evidence,
    )
    second = _record(
        cve_id="CVE-2026-10002",
        record_index=1,
        evidence=evidence,
    )

    hasher = NvdLogicalRecordSetHasherV1()

    forward = hasher.digest((first, second))
    reverse = hasher.digest((second, first))

    assert forward == reverse
    assert len(forward) == 64


def test_logical_hash_changes_when_record_set_changes() -> None:
    """Detect any change in the logical Silver record set."""
    evidence = _incremental_evidence()

    first = _record(
        cve_id="CVE-2026-10001",
        record_index=0,
        evidence=evidence,
    )
    changed = _record(
        cve_id="CVE-2026-99999",
        record_index=0,
        evidence=evidence,
    )

    hasher = NvdLogicalRecordSetHasherV1()

    assert hasher.digest((first,)) != hasher.digest((changed,))


def test_completion_manifest_binds_bronze_and_silver() -> None:
    """Bind exact Bronze evidence to exact persisted Parquet evidence."""
    evidence = _incremental_evidence()
    records = (
        _record(
            cve_id="CVE-2026-10001",
            record_index=0,
            evidence=evidence,
        ),
    )

    parquet = NvdSilverParquetSerializerV1().serialize(records)

    manifest, keys = NvdSilverCompletionManifestFactoryV1().build(
        evidence=evidence,
        records=records,
        parquet_artifact=parquet,
        silver_object_version_id="silver-version-1",
    )

    assert manifest.bronze_evidence is evidence
    assert manifest.silver_object.key == keys.parquet_key
    assert manifest.silver_object.version_id == "silver-version-1"
    assert manifest.silver_object.sha256 == parquet.parquet_sha256
    assert manifest.silver_object.size_bytes == parquet.size_bytes
    assert manifest.silver_object.row_count == 1


def test_completion_manifest_bytes_are_replay_deterministic() -> None:
    """Serialize identical completion proof byte-for-byte."""
    evidence = _incremental_evidence()
    records = (
        _record(
            cve_id="CVE-2026-10001",
            record_index=0,
            evidence=evidence,
        ),
    )

    parquet = NvdSilverParquetSerializerV1().serialize(records)

    manifest, keys = NvdSilverCompletionManifestFactoryV1().build(
        evidence=evidence,
        records=records,
        parquet_artifact=parquet,
        silver_object_version_id="silver-version-1",
    )

    serializer = NvdSilverCompletionManifestSerializerV1()

    first = serializer.serialize(
        manifest=manifest,
        manifest_key=keys.manifest_key,
    )
    replay = serializer.serialize(
        manifest=manifest,
        manifest_key=keys.manifest_key,
    )

    assert first.manifest_bytes == replay.manifest_bytes
    assert first.manifest_sha256 == replay.manifest_sha256


def test_manifest_contains_exact_bronze_inventory() -> None:
    """Make the completion proof independently auditable."""
    evidence = _incremental_evidence()
    records = (
        _record(
            cve_id="CVE-2026-10001",
            record_index=0,
            evidence=evidence,
        ),
    )

    parquet = NvdSilverParquetSerializerV1().serialize(records)

    manifest, keys = NvdSilverCompletionManifestFactoryV1().build(
        evidence=evidence,
        records=records,
        parquet_artifact=parquet,
        silver_object_version_id="silver-version-1",
    )

    artifact = NvdSilverCompletionManifestSerializerV1().serialize(
        manifest=manifest,
        manifest_key=keys.manifest_key,
    )

    document = json.loads(artifact.manifest_bytes)

    assert document["completion_status"] == "complete"
    assert document["manifest_version"] == "1"
    assert document["schema_version"] == 1
    assert document["bronze_manifest"]["version_id"] == (evidence.manifest_version_id)
    assert document["bronze_objects"][0]["version_id"] == (evidence.objects[0].version_id)
    assert document["silver_object"]["version_id"] == ("silver-version-1")


def test_unsupported_cvss_family_becomes_manifest_warning() -> None:
    """Preserve additive future CVSS as a non-fatal completion warning."""
    evidence = _incremental_evidence()
    records = (
        _record(
            cve_id="CVE-2026-10001",
            record_index=0,
            evidence=evidence,
            unsupported=("cvssMetricV50",),
        ),
    )

    parquet = NvdSilverParquetSerializerV1().serialize(records)

    manifest, _ = NvdSilverCompletionManifestFactoryV1().build(
        evidence=evidence,
        records=records,
        parquet_artifact=parquet,
        silver_object_version_id="silver-version-1",
    )

    assert manifest.warnings == ("unsupported_cvss_family:cvssMetricV50",)


def test_additional_warnings_are_sorted_and_unique() -> None:
    """Ensure warning order cannot change manifest bytes."""
    evidence = _incremental_evidence()
    records = (
        _record(
            cve_id="CVE-2026-10001",
            record_index=0,
            evidence=evidence,
        ),
    )

    parquet = NvdSilverParquetSerializerV1().serialize(records)

    manifest, _ = NvdSilverCompletionManifestFactoryV1().build(
        evidence=evidence,
        records=records,
        parquet_artifact=parquet,
        silver_object_version_id="silver-version-1",
        additional_warnings=(
            "warning-b",
            "warning-a",
            "warning-b",
        ),
    )

    assert manifest.warnings == (
        "warning-a",
        "warning-b",
    )


def test_completion_rejects_parquet_from_different_batch() -> None:
    """Prevent a Parquet artifact from being attached to another batch."""
    evidence = _incremental_evidence()
    records = (
        _record(
            cve_id="CVE-2026-10001",
            record_index=0,
            evidence=evidence,
        ),
    )

    parquet = NvdSilverParquetSerializerV1().serialize(records)

    wrong = replace(
        parquet,
        source_batch_id="different-batch",
    )

    with pytest.raises(
        ValueError,
        match="source_batch_id",
    ):
        NvdSilverCompletionManifestFactoryV1().build(
            evidence=evidence,
            records=records,
            parquet_artifact=wrong,
            silver_object_version_id="silver-version-1",
        )


def test_completion_rejects_row_with_wrong_bronze_version() -> None:
    """Require every row to bind to exact Bronze manifest evidence."""
    evidence = _incremental_evidence()

    record = _record(
        cve_id="CVE-2026-10001",
        record_index=0,
        evidence=evidence,
    )

    wrong_provenance = replace(
        record.provenance,
        bronze_manifest_version_id="wrong-version",
    )

    wrong_record = replace(
        record,
        provenance=wrong_provenance,
    )

    parquet = NvdSilverParquetSerializerV1().serialize((wrong_record,))

    with pytest.raises(
        ValueError,
        match="manifest VersionId",
    ):
        NvdSilverCompletionManifestFactoryV1().build(
            evidence=evidence,
            records=(wrong_record,),
            parquet_artifact=parquet,
            silver_object_version_id="silver-version-1",
        )


def test_completion_requires_exact_silver_version_id() -> None:
    """Silver cannot be COMPLETE without exact persisted object version."""
    evidence = _incremental_evidence()
    records = (
        _record(
            cve_id="CVE-2026-10001",
            record_index=0,
            evidence=evidence,
        ),
    )

    parquet = NvdSilverParquetSerializerV1().serialize(records)

    with pytest.raises(
        ValueError,
        match="VersionId",
    ):
        NvdSilverCompletionManifestFactoryV1().build(
            evidence=evidence,
            records=records,
            parquet_artifact=parquet,
            silver_object_version_id="",
        )


def test_completion_manifest_has_no_runtime_timestamp() -> None:
    """Keep COMPLETE evidence stable across deterministic replay."""
    evidence = _incremental_evidence()
    records = (
        _record(
            cve_id="CVE-2026-10001",
            record_index=0,
            evidence=evidence,
        ),
    )

    parquet = NvdSilverParquetSerializerV1().serialize(records)

    manifest, keys = NvdSilverCompletionManifestFactoryV1().build(
        evidence=evidence,
        records=records,
        parquet_artifact=parquet,
        silver_object_version_id="silver-version-1",
    )

    artifact = NvdSilverCompletionManifestSerializerV1().serialize(
        manifest=manifest,
        manifest_key=keys.manifest_key,
    )

    text = artifact.manifest_bytes.decode("utf-8")

    assert "retrieved_at" not in text
    assert "created_at" not in text
    assert artifact.manifest_sha256 == sha256(artifact.manifest_bytes).hexdigest()


def test_completion_rejects_parquet_from_different_record_set() -> None:
    """Prove the Parquet bytes came from the supplied logical rows."""
    evidence = _incremental_evidence()

    expected_record = _record(
        cve_id="CVE-2026-10001",
        record_index=0,
        evidence=evidence,
    )

    different_record = _record(
        cve_id="CVE-2026-99999",
        record_index=0,
        evidence=evidence,
    )

    wrong_parquet = NvdSilverParquetSerializerV1().serialize((different_record,))

    # Coarse batch coordinates still match.
    assert wrong_parquet.source_kind is evidence.source_kind
    assert wrong_parquet.source_batch_id == evidence.source_batch_id
    assert wrong_parquet.row_count == 1

    # But the logical record content does not.
    with pytest.raises(
        ValueError,
        match="deterministic serialization",
    ):
        NvdSilverCompletionManifestFactoryV1().build(
            evidence=evidence,
            records=(expected_record,),
            parquet_artifact=wrong_parquet,
            silver_object_version_id="silver-version-1",
        )
