"""Tests for deterministic GitHub advisory core normalization."""

from datetime import UTC, datetime

import pytest

from opslens.transformation.ghsa.domain.errors import (
    InvalidGhsaAdvisoryCoreRecordError,
)
from opslens.transformation.ghsa.domain.models import (
    GhsaAdvisorySeverity,
    GhsaAdvisoryType,
)
from opslens.transformation.ghsa.domain.transformer import GhsaAdvisoryCoreTransformer


def _source_advisory() -> dict[str, object]:
    """Return one representative official-shape reviewed advisory."""
    return {
        "ghsa_id": "GHSA-2345-cfgh-jmpq",
        "cve_id": "CVE-2026-12345",
        "url": "https://api.github.com/advisories/GHSA-2345-cfgh-jmpq",
        "html_url": "https://github.com/advisories/GHSA-2345-cfgh-jmpq",
        "repository_advisory_url": None,
        "summary": "Example advisory.",
        "description": "Example advisory description.",
        "type": "reviewed",
        "severity": "high",
        "source_code_location": "https://github.com/example/project",
        "published_at": "2026-08-25T10:00:00Z",
        "updated_at": "2026-08-26T12:00:00+00:00",
        "github_reviewed_at": "2026-08-25T11:00:00Z",
        "nvd_published_at": None,
        "withdrawn_at": None,
        "identifiers": [
            {"type": "GHSA", "value": "GHSA-2345-cfgh-jmpq"},
            {"type": "CVE", "value": "CVE-2026-12345"},
        ],
        "references": [],
        "vulnerabilities": [],
        "cvss": {"vector_string": None, "score": 0.0},
        "cvss_severities": {},
        "cwes": [],
        "credits": [],
    }


def test_transform_normalizes_reviewed_advisory_core() -> None:
    """Normalize documented scalar fields without source reinterpretation."""
    result = GhsaAdvisoryCoreTransformer().transform(_source_advisory())

    assert result.observed_version.ghsa_id == "GHSA-2345-cfgh-jmpq"
    assert result.cve_id == "CVE-2026-12345"
    assert result.advisory_type is GhsaAdvisoryType.REVIEWED
    assert result.severity is GhsaAdvisorySeverity.HIGH
    assert result.published_at == datetime(2026, 8, 25, 10, 0, tzinfo=UTC)
    assert result.updated_at == datetime(2026, 8, 26, 12, 0, tzinfo=UTC)
    assert result.github_reviewed_at == datetime(2026, 8, 25, 11, 0, tzinfo=UTC)
    assert result.nvd_published_at is None
    assert result.withdrawn_at is None
    assert result.is_withdrawn is False


def test_cve_id_is_nullable() -> None:
    """Preserve reviewed GHSAs that do not have a CVE alias."""
    source = _source_advisory()
    source["cve_id"] = None

    result = GhsaAdvisoryCoreTransformer().transform(source)

    assert result.cve_id is None


def test_withdrawn_advisory_remains_a_valid_historical_record() -> None:
    """Preserve withdrawn_at instead of treating withdrawal as deletion."""
    source = _source_advisory()
    source["withdrawn_at"] = "2026-08-27T09:30:00Z"

    result = GhsaAdvisoryCoreTransformer().transform(source)

    assert result.withdrawn_at == datetime(2026, 8, 27, 9, 30, tzinfo=UTC)
    assert result.is_withdrawn is True


@pytest.mark.parametrize("advisory_type", ["unreviewed", "malware"])
def test_non_reviewed_advisory_fails_scope_closed(advisory_type: str) -> None:
    """Reject advisory classes outside the accepted Phase 2.4 source scope."""
    source = _source_advisory()
    source["type"] = advisory_type

    with pytest.raises(
        InvalidGhsaAdvisoryCoreRecordError,
        match="reviewed advisories only",
    ):
        GhsaAdvisoryCoreTransformer().transform(source)


def test_unknown_advisory_type_fails_closed() -> None:
    """Reject undocumented advisory type values."""
    source = _source_advisory()
    source["type"] = "future-type"

    with pytest.raises(
        InvalidGhsaAdvisoryCoreRecordError,
        match="Unsupported GitHub advisory type",
    ):
        GhsaAdvisoryCoreTransformer().transform(source)


def test_unknown_severity_fails_closed() -> None:
    """Reject undocumented severity values in known core semantics."""
    source = _source_advisory()
    source["severity"] = "urgent"

    with pytest.raises(
        InvalidGhsaAdvisoryCoreRecordError,
        match="Unsupported GitHub advisory severity",
    ):
        GhsaAdvisoryCoreTransformer().transform(source)


def test_invalid_cve_id_fails_closed_when_present() -> None:
    """Reject malformed CVE alias evidence instead of normalizing it."""
    source = _source_advisory()
    source["cve_id"] = "CVE-bad"

    with pytest.raises(
        InvalidGhsaAdvisoryCoreRecordError,
        match="canonical CVE format",
    ):
        GhsaAdvisoryCoreTransformer().transform(source)


def test_naive_timestamp_fails_closed() -> None:
    """Require the source timestamp to declare its timezone."""
    source = _source_advisory()
    source["updated_at"] = "2026-08-26T12:00:00"

    with pytest.raises(
        InvalidGhsaAdvisoryCoreRecordError,
        match="must include a timezone offset",
    ):
        GhsaAdvisoryCoreTransformer().transform(source)


def test_missing_required_core_field_fails_closed() -> None:
    """Reject an advisory that cannot satisfy the frozen core contract."""
    source = _source_advisory()
    del source["severity"]

    with pytest.raises(
        InvalidGhsaAdvisoryCoreRecordError,
        match="missing required core fields: severity",
    ):
        GhsaAdvisoryCoreTransformer().transform(source)
