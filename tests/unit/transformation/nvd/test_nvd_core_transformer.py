"""Tests for deterministic NVD CVE core-field normalization."""

from datetime import UTC, datetime

import pytest

from opslens.transformation.nvd.domain.errors import (
    InvalidNvdCveCoreRecordError,
)
from opslens.transformation.nvd.domain.models import NvdVulnerabilityStatus
from opslens.transformation.nvd.domain.transformer import NvdCveCoreTransformer


def _source_cve() -> dict[str, object]:
    """Return one representative NVD CVE core source object."""
    return {
        "id": "CVE-2026-12345",
        "sourceIdentifier": "security@example.com",
        "published": "2026-08-20T10:00:00.000",
        "lastModified": "2026-08-21T10:30:00.000",
        "vulnStatus": "Analyzed",
    }


def test_core_transformer_normalizes_required_scalar_fields() -> None:
    """Normalize the required scalar NVD fields without changing identity."""
    record = NvdCveCoreTransformer().transform(_source_cve())

    assert record.observed_version.cve_id == "CVE-2026-12345"
    assert record.source_identifier == "security@example.com"
    assert record.published_at == datetime(
        2026,
        8,
        20,
        10,
        0,
        tzinfo=UTC,
    )
    assert record.last_modified_at == datetime(
        2026,
        8,
        21,
        10,
        30,
        tzinfo=UTC,
    )
    assert record.vuln_status is NvdVulnerabilityStatus.ANALYZED
    assert not record.is_rejected


def test_rejected_status_is_preserved_explicitly() -> None:
    """Represent a rejected CVE as a valid core record."""
    source = _source_cve()
    source["vulnStatus"] = "Rejected"

    record = NvdCveCoreTransformer().transform(source)

    assert record.vuln_status is NvdVulnerabilityStatus.REJECTED
    assert record.is_rejected


@pytest.mark.parametrize(
    "status",
    [
        "UndergoingAnalysis",
        "Modified",
        "AwaitingAnalysis",
        "Rejected",
        "Received",
        "Analyzed",
        "Deferred",
    ],
)
def test_documented_nvd_statuses_are_supported(status: str) -> None:
    """Accept every currently documented NVD vulnerability status."""
    source = _source_cve()
    source["vulnStatus"] = status

    record = NvdCveCoreTransformer().transform(source)

    assert record.vuln_status.value == status


def test_unknown_vulnerability_status_fails_closed() -> None:
    """Reject an unknown status instead of guessing its lifecycle semantics."""
    source = _source_cve()
    source["vulnStatus"] = "FutureUnknownStatus"

    with pytest.raises(
        InvalidNvdCveCoreRecordError,
        match="Unsupported NVD vulnStatus",
    ):
        NvdCveCoreTransformer().transform(source)


def test_missing_required_core_field_fails_closed() -> None:
    """Reject a CVE missing one of the required NVD core fields."""
    source = _source_cve()
    del source["sourceIdentifier"]

    with pytest.raises(
        InvalidNvdCveCoreRecordError,
        match="sourceIdentifier",
    ):
        NvdCveCoreTransformer().transform(source)


def test_invalid_timestamp_fails_closed() -> None:
    """Reject a malformed NVD timestamp."""
    source = _source_cve()
    source["published"] = "not-a-timestamp"

    with pytest.raises(
        InvalidNvdCveCoreRecordError,
        match="invalid timestamp",
    ):
        NvdCveCoreTransformer().transform(source)


def test_offset_timestamp_is_normalized_to_utc() -> None:
    """Normalize an offset-aware source timestamp to UTC."""
    source = _source_cve()
    source["published"] = "2026-08-20T12:00:00+02:00"

    record = NvdCveCoreTransformer().transform(source)

    assert record.published_at == datetime(
        2026,
        8,
        20,
        10,
        0,
        tzinfo=UTC,
    )


def test_additive_unknown_field_is_preserved_in_version_identity() -> None:
    """Keep additive source evidence in the observed-version content hash."""
    original = _source_cve()
    additive = dict(original)
    additive["futureNvdField"] = {"value": "future"}

    original_record = NvdCveCoreTransformer().transform(original)
    additive_record = NvdCveCoreTransformer().transform(additive)

    assert original_record.source_identifier == additive_record.source_identifier
    assert (
        original_record.observed_version.source_cve_sha256
        != additive_record.observed_version.source_cve_sha256
    )
