"""Tests for exact GHSA Bronze page verification and occurrence derivation."""

import hashlib
import json

import pytest

from opslens.transformation.ghsa.runtime.page_processor import (
    GhsaBronzePageEvidenceV1,
    GhsaBronzePageProcessorV1,
)

SYNC_ID = "1" * 64
ATTEMPT_ID = "2" * 64


def _page_bytes() -> bytes:
    """Return deterministic Bronze bytes containing two reviewed advisories."""
    payload = [
        {
            "ghsa_id": "GHSA-gvrw-qqp5-jgc5",
            "type": "reviewed",
        },
        {
            "ghsa_id": "GHSA-vxj7-4xrp-5vr4",
            "type": "reviewed",
        },
    ]
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _evidence(
    page_bytes: bytes,
    **overrides: object,
) -> GhsaBronzePageEvidenceV1:
    """Build valid exact physical page evidence with optional overrides."""
    values: dict[str, object] = {
        "sync_id": SYNC_ID,
        "attempt_id": ATTEMPT_ID,
        "manifest_key": "bronze/ghsa/advisories/manifest.json",
        "manifest_version_id": "manifest-version",
        "page_ordinal": 1,
        "page_key": "bronze/ghsa/advisories/page=000001/response.json",
        "page_version_id": "page-version",
        "expected_size_bytes": len(page_bytes),
        "expected_sha256": hashlib.sha256(page_bytes).hexdigest(),
    }
    values.update(overrides)

    return GhsaBronzePageEvidenceV1(
        **values,  # type: ignore[arg-type]
    )


def test_derives_occurrences_from_exact_verified_page() -> None:
    """Derive one logical occurrence per advisory in source order."""
    page_bytes = _page_bytes()

    result = GhsaBronzePageProcessorV1().process(
        evidence=_evidence(page_bytes),
        page_bytes=page_bytes,
    )

    assert result.item_count == 2

    first, second = result.occurrences

    assert first.source_index == 0
    assert first.ghsa_id == "GHSA-gvrw-qqp5-jgc5"
    assert first.physical_occurrence_id == (
        f"{ATTEMPT_ID}/page:000001/item:000"
    )

    assert second.source_index == 1
    assert second.ghsa_id == "GHSA-vxj7-4xrp-5vr4"
    assert second.physical_occurrence_id == (
        f"{ATTEMPT_ID}/page:000001/item:001"
    )


def test_rejects_page_size_mismatch() -> None:
    """Reject bytes whose size differs from persisted Bronze evidence."""
    page_bytes = _page_bytes()

    with pytest.raises(ValueError, match="expected_size_bytes"):
        GhsaBronzePageProcessorV1().process(
            evidence=_evidence(
                page_bytes,
                expected_size_bytes=len(page_bytes) + 1,
            ),
            page_bytes=page_bytes,
        )


def test_rejects_page_sha256_mismatch() -> None:
    """Reject bytes whose digest differs from persisted Bronze evidence."""
    page_bytes = _page_bytes()

    with pytest.raises(ValueError, match="expected_sha256"):
        GhsaBronzePageProcessorV1().process(
            evidence=_evidence(
                page_bytes,
                expected_sha256="f" * 64,
            ),
            page_bytes=page_bytes,
        )


def test_rejects_invalid_json_after_physical_verification() -> None:
    """Reject physically verified Bronze bytes that are not valid JSON."""
    page_bytes = b"not-json"

    with pytest.raises(ValueError, match="valid JSON"):
        GhsaBronzePageProcessorV1().process(
            evidence=_evidence(page_bytes),
            page_bytes=page_bytes,
        )


def test_rejects_non_array_top_level_json() -> None:
    """Require the Bronze REST representation to remain a JSON array."""
    page_bytes = b'{"ghsa_id":"GHSA-gvrw-qqp5-jgc5"}'

    with pytest.raises(ValueError, match="must be an array"):
        GhsaBronzePageProcessorV1().process(
            evidence=_evidence(page_bytes),
            page_bytes=page_bytes,
        )


def test_rejects_non_object_advisory_entry() -> None:
    """Require every source occurrence to remain an advisory object."""
    page_bytes = b'[{"ghsa_id":"GHSA-gvrw-qqp5-jgc5"},"invalid"]'

    with pytest.raises(ValueError, match="source_index=1"):
        GhsaBronzePageProcessorV1().process(
            evidence=_evidence(page_bytes),
            page_bytes=page_bytes,
        )


def test_accepts_exact_empty_advisory_array() -> None:
    """Preserve a valid empty Bronze source page as zero occurrences."""
    page_bytes = b"[]"

    result = GhsaBronzePageProcessorV1().process(
        evidence=_evidence(page_bytes),
        page_bytes=page_bytes,
    )

    assert result.item_count == 0
    assert result.occurrences == ()
