"""Tests for the versioned NVD observed-CVE identity contract."""

import hashlib
from copy import deepcopy

import pytest

from opslens.transformation.nvd.domain.errors import (
    InvalidNvdObservedCveVersionError,
)
from opslens.transformation.nvd.domain.models import ObservedCveVersion


def _source_cve() -> dict[str, object]:
    """Return one representative minimal NVD CVE source object."""
    return {
        "id": "CVE-2026-12345",
        "sourceIdentifier": "security@example.com",
        "published": "2026-08-20T10:00:00.000",
        "lastModified": "2026-08-21T10:00:00.000",
        "vulnStatus": "Analyzed",
        "descriptions": [
            {
                "lang": "en",
                "value": "Example vulnerability.",
            }
        ],
    }


def test_object_key_order_does_not_change_version_identity() -> None:
    """Ignore JSON object-key order when calculating version identity."""
    left: dict[str, object] = {
        "id": "CVE-2026-12345",
        "lastModified": "2026-08-21T10:00:00.000",
        "vulnStatus": "Analyzed",
        "metrics": {
            "beta": 2,
            "alpha": 1,
        },
    }
    right: dict[str, object] = {
        "metrics": {
            "alpha": 1,
            "beta": 2,
        },
        "vulnStatus": "Analyzed",
        "lastModified": "2026-08-21T10:00:00.000",
        "id": "CVE-2026-12345",
    }

    left_version = ObservedCveVersion.from_source(left)
    right_version = ObservedCveVersion.from_source(right)

    assert left_version.canonical_json == right_version.canonical_json
    assert left_version.source_cve_sha256 == right_version.source_cve_sha256
    assert left_version.observed_cve_version_id == right_version.observed_cve_version_id


def test_same_content_replay_preserves_version_identity() -> None:
    """Preserve version identity when identical CVE content is replayed."""
    source = _source_cve()

    first = ObservedCveVersion.from_source(source)
    replay = ObservedCveVersion.from_source(deepcopy(source))

    assert replay == first
    assert replay.observed_cve_version_id == first.observed_cve_version_id


def test_changed_content_creates_new_version_identity() -> None:
    """Create a new version identity whenever source CVE content changes."""
    original = _source_cve()
    changed = deepcopy(original)
    changed["futureAdditiveField"] = "new-source-evidence"

    original_version = ObservedCveVersion.from_source(original)
    changed_version = ObservedCveVersion.from_source(changed)

    assert changed_version.cve_id == original_version.cve_id
    assert changed_version.source_cve_sha256 != original_version.source_cve_sha256
    assert changed_version.observed_cve_version_id != original_version.observed_cve_version_id


def test_last_modified_is_not_the_version_identity() -> None:
    """Detect changed content even when NVD lastModified remains unchanged."""
    original = _source_cve()
    changed = deepcopy(original)

    descriptions = changed["descriptions"]
    assert isinstance(descriptions, list)

    descriptions[0] = {
        "lang": "en",
        "value": "Corrected vulnerability description.",
    }

    assert changed["lastModified"] == original["lastModified"]

    original_version = ObservedCveVersion.from_source(original)
    changed_version = ObservedCveVersion.from_source(changed)

    assert changed_version.cve_id == original_version.cve_id
    assert changed_version.source_cve_sha256 != original_version.source_cve_sha256


def test_rejected_cve_is_preserved_as_a_new_historical_version() -> None:
    """Preserve rejection as a new historical CVE content version."""
    analyzed = _source_cve()
    rejected = deepcopy(analyzed)
    rejected["vulnStatus"] = "Rejected"

    analyzed_version = ObservedCveVersion.from_source(analyzed)
    rejected_version = ObservedCveVersion.from_source(rejected)

    assert analyzed_version.cve_id == rejected_version.cve_id
    assert analyzed_version.source_cve_sha256 != rejected_version.source_cve_sha256
    assert analyzed_version.observed_cve_version_id != rejected_version.observed_cve_version_id


def test_array_order_is_preserved_by_version_identity() -> None:
    """Treat source-array order changes as different observed content."""
    original = _source_cve()
    original["cveTags"] = [
        {"sourceIdentifier": "a", "tags": ["first"]},
        {"sourceIdentifier": "b", "tags": ["second"]},
    ]

    reordered = deepcopy(original)
    reordered["cveTags"] = [
        {"sourceIdentifier": "b", "tags": ["second"]},
        {"sourceIdentifier": "a", "tags": ["first"]},
    ]

    original_version = ObservedCveVersion.from_source(original)
    reordered_version = ObservedCveVersion.from_source(reordered)

    assert original_version.source_cve_sha256 != reordered_version.source_cve_sha256


def test_invalid_cve_identifier_fails_closed() -> None:
    """Reject a source CVE whose identifier is not canonical."""
    source = _source_cve()
    source["id"] = "not-a-cve"

    with pytest.raises(
        InvalidNvdObservedCveVersionError,
        match="canonical CVE format",
    ):
        ObservedCveVersion.from_source(source)


def test_non_finite_json_number_fails_closed() -> None:
    """Reject non-finite numbers from the canonical JSON contract."""
    source = _source_cve()
    source["unexpectedMetric"] = float("nan")

    with pytest.raises(
        InvalidNvdObservedCveVersionError,
        match="must be finite",
    ):
        ObservedCveVersion.from_source(source)


def test_direct_construction_rejects_noncanonical_json() -> None:
    """Reject stored JSON bytes that do not use canonical encoding."""
    noncanonical_json = b'{"id": "CVE-2026-12345", "vulnStatus": "Analyzed"}'
    source_sha256 = hashlib.sha256(noncanonical_json).hexdigest()

    with pytest.raises(
        InvalidNvdObservedCveVersionError,
        match="Canonical JSON v1",
    ):
        ObservedCveVersion(
            cve_id="CVE-2026-12345",
            canonical_json=noncanonical_json,
            source_cve_sha256=source_sha256,
        )
