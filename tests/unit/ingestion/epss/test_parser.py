"""Unit tests for the EPSS snapshot parser."""

import gzip
import hashlib

import pytest

from opslens.ingestion.epss.domain.errors import InvalidEpssSnapshotError
from opslens.ingestion.epss.domain.parser import EpssSnapshotParser


def build_valid_snapshot() -> bytes:
    """Build a deterministic minimal EPSS gzip artifact for unit tests."""
    content = (
        "#model_version:v2026.06.15,score_date:2026-08-14T12:00:27Z\n"
        "cve,epss,percentile\n"
        "CVE-1999-0001,0.03351,0.8762\n"
        "CVE-2026-0001,0.71000,0.9910\n"
    )

    return gzip.compress(content.encode("utf-8"), mtime=0)


def test_parse_valid_snapshot() -> None:
    """Parse model metadata, rows, date, and digest from valid input."""
    payload = build_valid_snapshot()
    parser = EpssSnapshotParser()

    snapshot = parser.parse(payload)

    assert snapshot.model_version == "v2026.06.15"
    assert snapshot.snapshot_date == "2026-08-14"
    assert snapshot.row_count == 2
    assert snapshot.payload_size_bytes == len(payload)
    assert snapshot.sha256 == hashlib.sha256(payload).hexdigest()


def test_reject_invalid_gzip() -> None:
    """Reject source artifacts that are not valid gzip payloads."""
    parser = EpssSnapshotParser()

    with pytest.raises(
        InvalidEpssSnapshotError,
        match="valid gzip",
    ):
        parser.parse(b"not-a-gzip-file")


def test_reject_unexpected_header() -> None:
    """Reject EPSS artifacts whose CSV schema does not match the contract."""
    content = (
        "#model_version:v2026.06.15,score_date:2026-08-14T12:00:27Z\n"
        "cve,score\n"
        "CVE-2026-0001,0.71\n"
    )

    payload = gzip.compress(content.encode("utf-8"), mtime=0)

    parser = EpssSnapshotParser()

    with pytest.raises(
        InvalidEpssSnapshotError,
        match="Unexpected EPSS CSV header",
    ):
        parser.parse(payload)


def test_reject_missing_score_date() -> None:
    """Reject metadata that omits the canonical source score timestamp."""
    content = "#model_version:v2026.06.15\ncve,epss,percentile\nCVE-2026-0001,0.71,0.99\n"

    payload = gzip.compress(content.encode("utf-8"), mtime=0)

    parser = EpssSnapshotParser()

    with pytest.raises(
        InvalidEpssSnapshotError,
        match="score_date",
    ):
        parser.parse(payload)
