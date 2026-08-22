"""Tests for deterministic NVD Silver record composition."""

from datetime import UTC, datetime
from hashlib import sha256

import pytest

from opslens.transformation.nvd.application.record_composer import (
    NvdSilverRecordComposerV1,
)
from opslens.transformation.nvd.application.source_reader import (
    NvdSilverSourceRecordV1,
)
from opslens.transformation.nvd.domain.collections_transformer import (
    NvdCveCollectionsTransformer,
)
from opslens.transformation.nvd.domain.configurations_transformer import (
    NvdCpeConfigurationsTransformer,
)
from opslens.transformation.nvd.domain.cvss_transformer import (
    NvdCvssMetricsTransformer,
)
from opslens.transformation.nvd.domain.transformer import (
    NvdCveCoreTransformer,
)
from opslens.transformation.nvd.provenance.models import (
    NvdBronzeObjectReferenceV1,
    NvdBronzeObjectRole,
    VerifiedNvdBronzeEvidenceV1,
)
from opslens.transformation.nvd.provenance.verifier import (
    NvdSilverProvenanceFactoryV1,
)
from opslens.transformation.nvd.serialization.models import (
    NvdSilverSourceKind,
)


def _composer() -> NvdSilverRecordComposerV1:
    """Build the production deterministic record-composition graph."""
    return NvdSilverRecordComposerV1(
        core_transformer=NvdCveCoreTransformer(),
        collections_transformer=NvdCveCollectionsTransformer(),
        cvss_transformer=NvdCvssMetricsTransformer(),
        configurations_transformer=NvdCpeConfigurationsTransformer(),
        provenance_factory=NvdSilverProvenanceFactoryV1(),
    )


def _source_cve(
    cve_id: str = "CVE-2026-4000",
) -> dict[str, object]:
    """Return one minimal valid NVD CVE for Silver normalization."""
    return {
        "id": cve_id,
        "sourceIdentifier": "security@example.com",
        "published": "2026-08-20T10:00:00.000Z",
        "lastModified": "2026-08-21T11:00:00.000Z",
        "vulnStatus": "Analyzed",
        "descriptions": [
            {
                "lang": "en",
                "value": "Example vulnerability.",
            }
        ],
        "references": [],
    }


def _incremental_evidence(
    *,
    page_key: str = "bronze/nvd/page.json",
) -> VerifiedNvdBronzeEvidenceV1:
    """Build valid verified incremental evidence."""
    update_id = "a" * 64
    raw_bytes = b'{"example":"page"}'

    reference = NvdBronzeObjectReferenceV1(
        role=NvdBronzeObjectRole.PAGE,
        key=page_key,
        version_id="page-version-1",
        size_bytes=len(raw_bytes),
        sha256=sha256(raw_bytes).hexdigest(),
        page_start=0,
        source_timestamp="2026-08-21T12:00:00.000",
    )

    return VerifiedNvdBronzeEvidenceV1(
        source_kind=NvdSilverSourceKind.INCREMENTAL,
        source_batch_id=update_id,
        manifest_key=(f"bronze/nvd/cve/updates/update_id={update_id}/manifest.json"),
        manifest_version_id="manifest-version-1",
        manifest_sha256="b" * 64,
        manifest_size_bytes=123,
        objects=(reference,),
        bootstrap_feed_year=None,
        bootstrap_feed_revision=None,
        bootstrap_source_observed_at=None,
        incremental_update_id=update_id,
        incremental_total_results=1,
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


def test_composes_complete_incremental_silver_record() -> None:
    """Compose every frozen Silver-v1 record component."""
    page_key = "bronze/nvd/page.json"
    evidence = _incremental_evidence(
        page_key=page_key,
    )

    source_record = NvdSilverSourceRecordV1(
        bronze_object_key=page_key,
        record_index=0,
        source_cve=_source_cve(),
    )

    record = _composer().compose(
        evidence=evidence,
        source_record=source_record,
    )

    assert record.core.observed_version.cve_id == "CVE-2026-4000"
    assert record.core.source_identifier == "security@example.com"
    assert record.core.vuln_status.value == "Analyzed"

    assert len(record.collections.descriptions) == 1
    assert record.collections.references == ()

    assert record.cvss.metrics == ()
    assert record.cvss.unsupported_cvss_families == ()

    assert record.configurations.configuration_count == 0
    assert record.configurations.configurations_json == "[]"

    assert record.provenance.source_kind is NvdSilverSourceKind.INCREMENTAL
    assert record.provenance.bronze_object_key == page_key
    assert record.provenance.bronze_record_index == 0
    assert record.provenance.incremental_page_start == 0


def test_same_source_occurrence_produces_same_record_identity() -> None:
    """Preserve deterministic content and observation identities."""
    page_key = "bronze/nvd/page.json"
    evidence = _incremental_evidence(
        page_key=page_key,
    )

    source_record = NvdSilverSourceRecordV1(
        bronze_object_key=page_key,
        record_index=0,
        source_cve=_source_cve(),
    )

    first = _composer().compose(
        evidence=evidence,
        source_record=source_record,
    )
    second = _composer().compose(
        evidence=evidence,
        source_record=source_record,
    )

    assert (
        first.core.observed_version.observed_cve_version_id
        == second.core.observed_version.observed_cve_version_id
    )
    assert first.provenance.observation_id == second.provenance.observation_id
    assert first == second


def test_content_version_changes_when_complete_source_cve_changes() -> None:
    """Use complete canonical CVE content rather than lastModified as identity."""
    page_key = "bronze/nvd/page.json"
    evidence = _incremental_evidence(
        page_key=page_key,
    )

    original = _source_cve()
    changed = _source_cve()
    changed["descriptions"] = [
        {
            "lang": "en",
            "value": "Changed vulnerability description.",
        }
    ]

    first = _composer().compose(
        evidence=evidence,
        source_record=NvdSilverSourceRecordV1(
            bronze_object_key=page_key,
            record_index=0,
            source_cve=original,
        ),
    )
    second = _composer().compose(
        evidence=evidence,
        source_record=NvdSilverSourceRecordV1(
            bronze_object_key=page_key,
            record_index=0,
            source_cve=changed,
        ),
    )

    assert (
        first.core.observed_version.observed_cve_version_id
        != second.core.observed_version.observed_cve_version_id
    )

    # Observation identity describes the source occurrence coordinate.
    assert first.provenance.observation_id == second.provenance.observation_id


def test_rejects_source_record_not_bound_to_verified_object() -> None:
    """Never manufacture provenance for an unverified Bronze object."""
    evidence = _incremental_evidence()

    source_record = NvdSilverSourceRecordV1(
        bronze_object_key="bronze/nvd/not-verified.json",
        record_index=0,
        source_cve=_source_cve(),
    )

    with pytest.raises(
        ValueError,
        match="was not found",
    ):
        _composer().compose(
            evidence=evidence,
            source_record=source_record,
        )


def test_rejects_invalid_source_cve_through_existing_domain_contract() -> None:
    """Preserve fail-closed behavior from the frozen deterministic transformers."""
    page_key = "bronze/nvd/page.json"
    evidence = _incremental_evidence(
        page_key=page_key,
    )
    source_cve = _source_cve()
    source_cve["vulnStatus"] = "Future Unknown Status"

    source_record = NvdSilverSourceRecordV1(
        bronze_object_key=page_key,
        record_index=0,
        source_cve=source_cve,
    )

    with pytest.raises(
        ValueError,
        match="Unsupported NVD vulnStatus",
    ):
        _composer().compose(
            evidence=evidence,
            source_record=source_record,
        )
