"""Tests for exact KEV source-authority decoding before Gate 19.2 measurement."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

import pytest

from opslens.ingestion.kev.domain.parser import KevCatalogParser
from opslens.public_analysis.adapters.exact_kev_authority import (
    ExactKevAuthorityError,
    ExactKevAuthorityReader,
)
from opslens.public_analysis.adapters.exact_s3_authority_object import (
    ExactS3AuthorityObject,
)


def _calls() -> list[tuple[str, str]]:
    """Return a typed mutable call log for strict Pyright."""
    return []


@dataclass(slots=True)
class FakeObjectReader:
    """Return one prebuilt exact S3 authority object and record coordinates."""

    result: ExactS3AuthorityObject
    calls: list[tuple[str, str]] = field(default_factory=_calls)

    def read(self, *, object_key: str, version_id: str) -> ExactS3AuthorityObject:
        """Record one exact physical read request."""
        self.calls.append((object_key, version_id))
        return self.result


def _payload() -> bytes:
    """Return a minimal valid complete CISA KEV catalog source artifact."""
    return (
        b'{"catalogVersion":"2026.09.10","dateReleased":"2026-09-10T12:00:00Z",'
        b'"count":1,"vulnerabilities":[{"cveID":"CVE-2025-0001"}]}'
    )


def _object(*, metadata: tuple[tuple[str, str], ...] | None = None) -> ExactS3AuthorityObject:
    """Build exact immutable KEV bytes with matching source provenance metadata."""
    payload = _payload()
    exact_metadata = metadata or (
        ("catalog_version", "2026.09.10"),
        ("date_released", "2026-09-10T12:00:00+00:00"),
        ("record_count", "1"),
        ("retrieved_at", "2026-09-10T15:30:00+00:00"),
        ("sha256", hashlib.sha256(payload).hexdigest()),
        ("source", "cisa-kev"),
    )
    return ExactS3AuthorityObject(
        object_key="bronze/kev/catalog.json",
        version_id="version-kev-7",
        payload=payload,
        metadata=exact_metadata,
    )


def test_reader_returns_complete_snapshot_from_exact_bytes_and_metadata() -> None:
    """Same-version bytes and metadata reconstruct the complete KEV snapshot."""
    source = FakeObjectReader(_object())
    reader = ExactKevAuthorityReader(object_reader=source, parser=KevCatalogParser())

    result = reader.read(
        object_key="bronze/kev/catalog.json",
        version_id="version-kev-7",
        snapshot_date="2026-09-10",
    )

    assert source.calls == [("bronze/kev/catalog.json", "version-kev-7")]
    assert result.snapshot_date == "2026-09-10"
    assert result.catalog_version == "2026.09.10"
    assert result.record_count == 1
    assert result.raw_bytes == _payload()


def test_reader_rejects_missing_or_extra_metadata() -> None:
    """Incomplete or expanded provenance contracts fail closed."""
    base = dict(_object().metadata)
    base.pop("retrieved_at")
    reader = ExactKevAuthorityReader(
        object_reader=FakeObjectReader(_object(metadata=tuple(base.items()))),
        parser=KevCatalogParser(),
    )
    with pytest.raises(ExactKevAuthorityError, match="exactly the required"):
        reader.read(
            object_key="bronze/kev/catalog.json",
            version_id="version-kev-7",
            snapshot_date="2026-09-10",
        )

    base = dict(_object().metadata)
    base["unexpected"] = "authority-expansion"
    reader = ExactKevAuthorityReader(
        object_reader=FakeObjectReader(_object(metadata=tuple(base.items()))),
        parser=KevCatalogParser(),
    )
    with pytest.raises(ExactKevAuthorityError, match="exactly the required"):
        reader.read(
            object_key="bronze/kev/catalog.json",
            version_id="version-kev-7",
            snapshot_date="2026-09-10",
        )


def test_reader_rejects_source_digest_and_snapshot_drift() -> None:
    """Transport success cannot override contradictory KEV source authority."""
    metadata = dict(_object().metadata)
    metadata["source"] = "other-source"
    reader = ExactKevAuthorityReader(
        object_reader=FakeObjectReader(_object(metadata=tuple(metadata.items()))),
        parser=KevCatalogParser(),
    )
    with pytest.raises(ExactKevAuthorityError, match="source"):
        reader.read(
            object_key="bronze/kev/catalog.json",
            version_id="version-kev-7",
            snapshot_date="2026-09-10",
        )

    metadata = dict(_object().metadata)
    metadata["sha256"] = "0" * 64
    reader = ExactKevAuthorityReader(
        object_reader=FakeObjectReader(_object(metadata=tuple(metadata.items()))),
        parser=KevCatalogParser(),
    )
    with pytest.raises(ExactKevAuthorityError, match="sha256 mismatch"):
        reader.read(
            object_key="bronze/kev/catalog.json",
            version_id="version-kev-7",
            snapshot_date="2026-09-10",
        )

    reader = ExactKevAuthorityReader(
        object_reader=FakeObjectReader(_object()),
        parser=KevCatalogParser(),
    )
    with pytest.raises(ExactKevAuthorityError, match="snapshot date mismatch"):
        reader.read(
            object_key="bronze/kev/catalog.json",
            version_id="version-kev-7",
            snapshot_date="2026-09-09",
        )


def test_reader_rejects_unusable_metadata_before_source_admission() -> None:
    """Naive timestamps and non-canonical counts never become typed authority."""
    metadata = dict(_object().metadata)
    metadata["retrieved_at"] = "2026-09-10T15:30:00"
    reader = ExactKevAuthorityReader(
        object_reader=FakeObjectReader(_object(metadata=tuple(metadata.items()))),
        parser=KevCatalogParser(),
    )
    with pytest.raises(ExactKevAuthorityError, match="timezone"):
        reader.read(
            object_key="bronze/kev/catalog.json",
            version_id="version-kev-7",
            snapshot_date="2026-09-10",
        )

    metadata = dict(_object().metadata)
    metadata["record_count"] = "01"
    reader = ExactKevAuthorityReader(
        object_reader=FakeObjectReader(_object(metadata=tuple(metadata.items()))),
        parser=KevCatalogParser(),
    )
    with pytest.raises(ExactKevAuthorityError, match="canonical"):
        reader.read(
            object_key="bronze/kev/catalog.json",
            version_id="version-kev-7",
            snapshot_date="2026-09-10",
        )
