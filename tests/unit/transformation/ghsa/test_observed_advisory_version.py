"""Tests for the versioned GHSA observed-advisory identity contract."""

import hashlib
from copy import deepcopy

import pytest

from opslens.transformation.ghsa.domain.errors import (
    InvalidGhsaObservedAdvisoryVersionError,
)
from opslens.transformation.ghsa.domain.models import ObservedGhsaAdvisoryVersion


def _source_advisory() -> dict[str, object]:
    """Return one representative minimal GitHub advisory source object."""
    return {
        "ghsa_id": "GHSA-2345-cfgh-jmpq",
        "cve_id": "CVE-2026-12345",
        "updated_at": "2026-08-27T10:00:00Z",
        "summary": "Example advisory.",
        "vulnerabilities": [
            {
                "package": {
                    "ecosystem": "pip",
                    "name": "example-package",
                },
                "vulnerable_version_range": "< 2.0.0",
                "first_patched_version": "2.0.0",
            }
        ],
    }


def test_object_key_order_does_not_change_version_identity() -> None:
    """Ignore JSON object-key order when calculating version identity."""
    left: dict[str, object] = {
        "ghsa_id": "GHSA-2345-cfgh-jmpq",
        "severity": "high",
        "metadata": {
            "beta": 2,
            "alpha": 1,
        },
    }
    right: dict[str, object] = {
        "metadata": {
            "alpha": 1,
            "beta": 2,
        },
        "severity": "high",
        "ghsa_id": "GHSA-2345-cfgh-jmpq",
    }

    left_version = ObservedGhsaAdvisoryVersion.from_source(left)
    right_version = ObservedGhsaAdvisoryVersion.from_source(right)

    assert left_version.canonical_json == right_version.canonical_json
    assert left_version.source_advisory_sha256 == right_version.source_advisory_sha256
    assert left_version.observed_advisory_version_id == right_version.observed_advisory_version_id


def test_same_content_replay_preserves_version_identity() -> None:
    """Preserve version identity when identical advisory content is replayed."""
    source = _source_advisory()

    first = ObservedGhsaAdvisoryVersion.from_source(source)
    replay = ObservedGhsaAdvisoryVersion.from_source(deepcopy(source))

    assert replay == first
    assert replay.observed_advisory_version_id == first.observed_advisory_version_id


def test_changed_additive_content_creates_new_version_identity() -> None:
    """Create a new version identity when additive source evidence changes."""
    original = _source_advisory()
    changed = deepcopy(original)
    changed["future_additive_field"] = "new-source-evidence"

    original_version = ObservedGhsaAdvisoryVersion.from_source(original)
    changed_version = ObservedGhsaAdvisoryVersion.from_source(changed)

    assert changed_version.ghsa_id == original_version.ghsa_id
    assert changed_version.source_advisory_sha256 != original_version.source_advisory_sha256
    assert (
        changed_version.observed_advisory_version_id
        != original_version.observed_advisory_version_id
    )


def test_updated_at_is_not_the_version_identity() -> None:
    """Detect changed content even when GitHub updated_at remains unchanged."""
    original = _source_advisory()
    changed = deepcopy(original)
    changed["summary"] = "Corrected advisory summary."

    assert changed["updated_at"] == original["updated_at"]

    original_version = ObservedGhsaAdvisoryVersion.from_source(original)
    changed_version = ObservedGhsaAdvisoryVersion.from_source(changed)

    assert changed_version.ghsa_id == original_version.ghsa_id
    assert changed_version.source_advisory_sha256 != original_version.source_advisory_sha256


def test_withdrawal_change_creates_new_historical_version() -> None:
    """Preserve advisory withdrawal as changed historical source evidence."""
    active = _source_advisory()
    active["withdrawn_at"] = None

    withdrawn = deepcopy(active)
    withdrawn["withdrawn_at"] = "2026-08-27T11:00:00Z"

    active_version = ObservedGhsaAdvisoryVersion.from_source(active)
    withdrawn_version = ObservedGhsaAdvisoryVersion.from_source(withdrawn)

    assert active_version.ghsa_id == withdrawn_version.ghsa_id
    assert active_version.source_advisory_sha256 != withdrawn_version.source_advisory_sha256


def test_array_order_is_preserved_by_version_identity() -> None:
    """Treat source-array order changes as different observed content."""
    original = _source_advisory()
    original["identifiers"] = [
        {"type": "GHSA", "value": "GHSA-2345-cfgh-jmpq"},
        {"type": "CVE", "value": "CVE-2026-12345"},
    ]

    reordered = deepcopy(original)
    reordered["identifiers"] = [
        {"type": "CVE", "value": "CVE-2026-12345"},
        {"type": "GHSA", "value": "GHSA-2345-cfgh-jmpq"},
    ]

    original_version = ObservedGhsaAdvisoryVersion.from_source(original)
    reordered_version = ObservedGhsaAdvisoryVersion.from_source(reordered)

    assert original_version.source_advisory_sha256 != reordered_version.source_advisory_sha256


def test_invalid_ghsa_identifier_fails_closed() -> None:
    """Reject a source advisory whose GHSA identifier is not canonical."""
    source = _source_advisory()
    source["ghsa_id"] = "not-a-ghsa"

    with pytest.raises(
        InvalidGhsaObservedAdvisoryVersionError,
        match="canonical GHSA format",
    ):
        ObservedGhsaAdvisoryVersion.from_source(source)


def test_non_finite_json_number_fails_closed() -> None:
    """Reject non-finite numbers from the canonical JSON contract."""
    source = _source_advisory()
    source["unexpected_score"] = float("nan")

    with pytest.raises(
        InvalidGhsaObservedAdvisoryVersionError,
        match="must be finite",
    ):
        ObservedGhsaAdvisoryVersion.from_source(source)


def test_direct_construction_rejects_noncanonical_json() -> None:
    """Reject stored JSON bytes that do not use canonical encoding."""
    noncanonical_json = b'{"ghsa_id": "GHSA-2345-cfgh-jmpq", "severity": "high"}'
    source_sha256 = hashlib.sha256(noncanonical_json).hexdigest()

    with pytest.raises(
        InvalidGhsaObservedAdvisoryVersionError,
        match="Canonical JSON v1",
    ):
        ObservedGhsaAdvisoryVersion(
            ghsa_id="GHSA-2345-cfgh-jmpq",
            canonical_json=noncanonical_json,
            source_advisory_sha256=source_sha256,
        )
