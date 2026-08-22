# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false
"""Tests for deterministic NVD Silver v1 row mapping."""

from datetime import UTC, datetime

import pyarrow as pa
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
from opslens.transformation.nvd.serialization.row_mapper import (
    map_nvd_silver_record_v1,
)
from opslens.transformation.nvd.serialization.schema import (
    NVD_CVE_VERSIONS_SCHEMA_V1,
)


def _observed_version() -> ObservedCveVersion:
    source: dict[str, object] = {
        "id": "CVE-2026-12345",
        "futureField": {
            "preserved": True,
        },
    }

    canonical = canonicalize_nvd_cve(source)

    return ObservedCveVersion(
        cve_id="CVE-2026-12345",
        canonical_json=canonical,
        source_cve_sha256=sha256_hex(canonical),
    )


def _provenance() -> NvdSilverProvenanceV1:
    return NvdSilverProvenanceV1(
        source_kind=NvdSilverSourceKind.INCREMENTAL,
        source_batch_id="update-20260821T120000Z",
        observation_id="obs-000001",
        source_observed_at=datetime(
            2026,
            8,
            21,
            12,
            0,
            tzinfo=UTC,
        ),
        bronze_manifest_key=(
            "bronze/nvd/cve/updates/update_id=update-20260821T120000Z/manifest.json"
        ),
        bronze_manifest_version_id="manifest-version-1",
        bronze_manifest_sha256="a" * 64,
        bronze_object_key=(
            "bronze/nvd/cve/updates/"
            "update_id=update-20260821T120000Z/"
            "page_start=000000/response.json"
        ),
        bronze_object_version_id="object-version-1",
        bronze_object_sha256="b" * 64,
        bronze_record_index=0,
        bootstrap_feed_year=None,
        bootstrap_feed_revision=None,
        incremental_update_id="update-20260821T120000Z",
        incremental_page_start=0,
    )


def _record() -> NvdSilverRecordV1:
    observed = _observed_version()

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
                value="Example vulnerability.",
            ),
        ),
        cve_tags=(),
        weaknesses=(),
        references=(),
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
        provenance=_provenance(),
    )


def test_row_mapper_preserves_observed_version_identity() -> None:
    """Map content identity independently from source lastModified."""
    record = _record()

    row = map_nvd_silver_record_v1(record)

    assert row["cve_id"] == "CVE-2026-12345"
    assert row["observed_cve_version_id"] == record.core.observed_version.observed_cve_version_id
    assert row["source_cve_sha256"] == record.core.observed_version.source_cve_sha256


def test_row_mapper_preserves_normalized_nested_content() -> None:
    """Preserve normalized collection and configuration structure."""
    row = map_nvd_silver_record_v1(_record())

    assert row["descriptions"] == [
        {
            "lang": "en",
            "value": "Example vulnerability.",
        }
    ]
    assert row["cve_tags"] == []
    assert row["weaknesses"] == []
    assert row["cwe_ids"] == []
    assert row["references"] == []
    assert row["cvss_metrics"] == []
    assert row["configurations_json"] == "[]"
    assert row["configuration_count"] == 0


def test_row_matches_explicit_arrow_schema() -> None:
    """Prove the mapper produces a row accepted by schema v1."""
    row = map_nvd_silver_record_v1(_record())

    table = pa.Table.from_pylist(
        [row],
        schema=NVD_CVE_VERSIONS_SCHEMA_V1,
    )

    assert table.num_rows == 1
    assert table.schema == NVD_CVE_VERSIONS_SCHEMA_V1


def test_incremental_provenance_requires_page_coordinates() -> None:
    """Reject incomplete incremental serialization provenance."""
    valid = _provenance()

    with pytest.raises(
        ValueError,
        match="incremental_page_start",
    ):
        NvdSilverProvenanceV1(
            source_kind=valid.source_kind,
            source_batch_id=valid.source_batch_id,
            observation_id=valid.observation_id,
            source_observed_at=valid.source_observed_at,
            bronze_manifest_key=valid.bronze_manifest_key,
            bronze_manifest_version_id=(valid.bronze_manifest_version_id),
            bronze_manifest_sha256=valid.bronze_manifest_sha256,
            bronze_object_key=valid.bronze_object_key,
            bronze_object_version_id=valid.bronze_object_version_id,
            bronze_object_sha256=valid.bronze_object_sha256,
            bronze_record_index=valid.bronze_record_index,
            bootstrap_feed_year=None,
            bootstrap_feed_revision=None,
            incremental_update_id=valid.incremental_update_id,
            incremental_page_start=None,
        )


def test_bootstrap_provenance_rejects_incremental_coordinates() -> None:
    """Keep bootstrap and incremental coordinates mutually exclusive."""
    with pytest.raises(
        ValueError,
        match="incremental_update_id",
    ):
        NvdSilverProvenanceV1(
            source_kind=NvdSilverSourceKind.BOOTSTRAP,
            source_batch_id="bootstrap-2025",
            observation_id="obs-bootstrap",
            source_observed_at=datetime(
                2026,
                8,
                21,
                tzinfo=UTC,
            ),
            bronze_manifest_key="bootstrap/manifest.json",
            bronze_manifest_version_id="version-1",
            bronze_manifest_sha256="a" * 64,
            bronze_object_key="bootstrap/feed.json.gz",
            bronze_object_version_id="version-2",
            bronze_object_sha256="b" * 64,
            bronze_record_index=0,
            bootstrap_feed_year=2025,
            bootstrap_feed_revision="revision-1",
            incremental_update_id="must-not-exist",
            incremental_page_start=None,
        )


def test_provenance_requires_lowercase_sha256() -> None:
    """Reject ambiguous or malformed provenance content digests."""
    valid = _provenance()

    with pytest.raises(
        ValueError,
        match="bronze_object_sha256",
    ):
        NvdSilverProvenanceV1(
            source_kind=valid.source_kind,
            source_batch_id=valid.source_batch_id,
            observation_id=valid.observation_id,
            source_observed_at=valid.source_observed_at,
            bronze_manifest_key=valid.bronze_manifest_key,
            bronze_manifest_version_id=(valid.bronze_manifest_version_id),
            bronze_manifest_sha256=valid.bronze_manifest_sha256,
            bronze_object_key=valid.bronze_object_key,
            bronze_object_version_id=valid.bronze_object_version_id,
            bronze_object_sha256="INVALID",
            bronze_record_index=valid.bronze_record_index,
            bootstrap_feed_year=None,
            bootstrap_feed_revision=None,
            incremental_update_id=valid.incremental_update_id,
            incremental_page_start=valid.incremental_page_start,
        )
