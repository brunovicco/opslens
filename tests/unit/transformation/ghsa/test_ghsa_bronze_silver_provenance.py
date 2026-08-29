"""Tests for deterministic GHSA Bronze-to-Silver provenance."""

import pytest

from opslens.transformation.ghsa.domain.errors import (
    InvalidGhsaObservedAdvisoryVersionError,
)
from opslens.transformation.ghsa.runtime.provenance import (
    GhsaBronzeAdvisoryOccurrenceV1,
)

SYNC_ID = "1" * 64
ATTEMPT_ID = "2" * 64

SOURCE_ADVISORY: dict[str, object] = {
    "ghsa_id": "GHSA-gvrw-qqp5-jgc5",
    "type": "reviewed",
}


def _occurrence(
    **overrides: object,
) -> GhsaBronzeAdvisoryOccurrenceV1:
    values: dict[str, object] = {
        "sync_id": SYNC_ID,
        "attempt_id": ATTEMPT_ID,
        "manifest_key": "bronze/ghsa/advisories/manifest.json",
        "manifest_version_id": "manifest-version",
        "page_ordinal": 1,
        "page_key": "bronze/ghsa/advisories/page=000001/response.json",
        "page_version_id": "page-version",
        "source_index": 0,
        "source_advisory": SOURCE_ADVISORY,
    }
    values.update(overrides)

    return GhsaBronzeAdvisoryOccurrenceV1.from_source(
        **values,  # type: ignore[arg-type]
    )


def test_builds_exact_physical_occurrence_identity() -> None:
    """Build a stable identifier for one exact Bronze advisory occurrence."""
    occurrence = _occurrence(
        page_ordinal=2,
        source_index=7,
    )

    assert occurrence.physical_occurrence_id == (
        f"{ATTEMPT_ID}/page:000002/item:007"
    )


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("sync_id", "invalid"),
        ("attempt_id", "invalid"),
    ],
)
def test_rejects_invalid_sha256_fields(
    field_name: str,
    value: str,
) -> None:
    """Reject malformed physical SHA-256 identifiers."""
    with pytest.raises(ValueError, match=field_name):
        _occurrence(**{field_name: value})


@pytest.mark.parametrize(
    "field_name",
    [
        "manifest_key",
        "manifest_version_id",
        "page_key",
        "page_version_id",
    ],
)
def test_rejects_empty_physical_evidence_fields(
    field_name: str,
) -> None:
    """Reject empty S3 physical-evidence coordinates."""
    with pytest.raises(ValueError, match=field_name):
        _occurrence(**{field_name: " "})


def test_rejects_zero_page_ordinal() -> None:
    """Reject page ordinals outside the one-based Bronze page contract."""
    with pytest.raises(ValueError, match="page_ordinal"):
        _occurrence(page_ordinal=0)


def test_rejects_negative_source_index() -> None:
    """Reject negative advisory indexes inside a Bronze page."""
    with pytest.raises(ValueError, match="source_index"):
        _occurrence(source_index=-1)


def test_rejects_invalid_ghsa_id_from_source() -> None:
    """Reject non-canonical GHSA identifiers found in source evidence."""
    invalid_source = {
        **SOURCE_ADVISORY,
        "ghsa_id": "CVE-2026-12345",
    }


    with pytest.raises(
        InvalidGhsaObservedAdvisoryVersionError,
        match="ghsa_id",
    ):
        _occurrence(source_advisory=invalid_source)


def test_derives_observed_version_identity_from_source() -> None:
    """Derive Silver content identity instead of accepting it from the caller."""
    occurrence = _occurrence()

    assert occurrence.ghsa_id == SOURCE_ADVISORY["ghsa_id"]
    assert len(occurrence.source_advisory_sha256) == 64

    assert occurrence.observed_advisory_version_id == (
        f"{occurrence.ghsa_id}@sha256:"
        f"{occurrence.source_advisory_sha256}"
    )


def test_source_content_change_changes_observed_version_identity() -> None:
    """Change Silver identity when exact advisory source content changes."""
    first = _occurrence()

    changed_source = {
        **SOURCE_ADVISORY,
        "summary": "Changed source evidence",
    }
    second = _occurrence(source_advisory=changed_source)

    assert first.ghsa_id == second.ghsa_id
    assert (
        first.source_advisory_sha256
        != second.source_advisory_sha256
    )
    assert (
        first.observed_advisory_version_id
        != second.observed_advisory_version_id
    )


@pytest.mark.parametrize(
    "caller_controlled_field",
    [
        "ghsa_id",
        "source_advisory_sha256",
        "observed_advisory_version_id",
    ],
)
def test_factory_rejects_caller_supplied_logical_identity(
    caller_controlled_field: str,
) -> None:
    """Keep logical advisory identity derived exclusively from source evidence."""
    values: dict[str, object] = {
        "sync_id": SYNC_ID,
        "attempt_id": ATTEMPT_ID,
        "manifest_key": "manifest.json",
        "manifest_version_id": "manifest-version",
        "page_ordinal": 1,
        "page_key": "response.json",
        "page_version_id": "page-version",
        "source_index": 0,
        "source_advisory": SOURCE_ADVISORY,
        caller_controlled_field: "caller-controlled",
    }

    with pytest.raises(TypeError):
        GhsaBronzeAdvisoryOccurrenceV1.from_source(
            **values,  # type: ignore[arg-type]
        )
