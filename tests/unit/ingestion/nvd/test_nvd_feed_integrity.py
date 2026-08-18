"""Unit tests for deterministic NVD yearly-feed integrity verification."""

import gzip
import hashlib

import pytest

from opslens.ingestion.nvd.domain.errors import InvalidNvdFeedArtifactError
from opslens.ingestion.nvd.domain.feed_integrity import (
    NvdFeedIntegrityVerifier,
)
from opslens.ingestion.nvd.domain.meta_parser import NvdFeedMetaParser
from opslens.ingestion.nvd.domain.models import NvdFeedMeta

UNCOMPRESSED_PAYLOAD = b'{"format":"NVD_CVE","version":"2.0"}'


def _gzip_payload(payload: bytes = UNCOMPRESSED_PAYLOAD) -> bytes:
    """Return deterministic gzip bytes for test source content."""
    return gzip.compress(payload, mtime=0)


def _build_meta(
    gzip_payload: bytes,
    *,
    uncompressed_payload: bytes = UNCOMPRESSED_PAYLOAD,
    declared_uncompressed_size: int | None = None,
    declared_gzip_size: int | None = None,
    source_sha256: str | None = None,
) -> NvdFeedMeta:
    """Build valid META evidence with optionally overridden integrity values."""
    uncompressed_size = (
        len(uncompressed_payload)
        if declared_uncompressed_size is None
        else declared_uncompressed_size
    )
    gzip_size = len(gzip_payload) if declared_gzip_size is None else declared_gzip_size
    sha256 = source_sha256 or hashlib.sha256(uncompressed_payload).hexdigest()

    payload = (
        "lastModifiedDate:2026-08-18T03:00:12-04:00\n"
        f"size:{uncompressed_size}\n"
        "zipSize:1\n"
        f"gzSize:{gzip_size}\n"
        f"sha256:{sha256}\n"
    ).encode()

    return NvdFeedMetaParser().parse(payload)


def test_verify_accepts_matching_nvd_feed_and_meta() -> None:
    """Accept gzip bytes whose source evidence matches the META contract."""
    gzip_payload = _gzip_payload()
    meta = _build_meta(gzip_payload)

    artifact = NvdFeedIntegrityVerifier().verify(
        payload=gzip_payload,
        meta=meta,
    )

    assert artifact.raw_gzip_bytes == gzip_payload
    assert artifact.meta == meta
    assert artifact.gzip_size_bytes == len(gzip_payload)
    assert artifact.bronze_object_sha256 == hashlib.sha256(gzip_payload).hexdigest()


def test_verify_rejects_empty_gzip_payload() -> None:
    """Reject missing feed bytes before attempting decompression."""
    gzip_payload = _gzip_payload()
    meta = _build_meta(gzip_payload)

    with pytest.raises(
        InvalidNvdFeedArtifactError,
        match="payload is empty",
    ):
        NvdFeedIntegrityVerifier().verify(
            payload=b"",
            meta=meta,
        )


def test_verify_rejects_compressed_size_mismatch() -> None:
    """Reject gzip bytes whose size differs from NVD META gzSize."""
    gzip_payload = _gzip_payload()
    meta = _build_meta(
        gzip_payload,
        declared_gzip_size=len(gzip_payload) + 1,
    )

    with pytest.raises(
        InvalidNvdFeedArtifactError,
        match="does not match META gzSize",
    ):
        NvdFeedIntegrityVerifier().verify(
            payload=gzip_payload,
            meta=meta,
        )


def test_verify_rejects_uncompressed_size_mismatch() -> None:
    """Reject content shorter than the uncompressed META size."""
    gzip_payload = _gzip_payload()
    meta = _build_meta(
        gzip_payload,
        declared_uncompressed_size=len(UNCOMPRESSED_PAYLOAD) + 1,
    )

    with pytest.raises(
        InvalidNvdFeedArtifactError,
        match="does not match META size",
    ):
        NvdFeedIntegrityVerifier().verify(
            payload=gzip_payload,
            meta=meta,
        )


def test_verify_rejects_content_exceeding_declared_size() -> None:
    """Stop when decompressed content exceeds its declared META bound."""
    gzip_payload = _gzip_payload()
    meta = _build_meta(
        gzip_payload,
        declared_uncompressed_size=len(UNCOMPRESSED_PAYLOAD) - 1,
    )

    with pytest.raises(
        InvalidNvdFeedArtifactError,
        match="exceeds META size",
    ):
        NvdFeedIntegrityVerifier().verify(
            payload=gzip_payload,
            meta=meta,
        )


def test_verify_rejects_source_sha256_mismatch() -> None:
    """Reject gzip content whose uncompressed digest differs from META."""
    gzip_payload = _gzip_payload()
    meta = _build_meta(
        gzip_payload,
        source_sha256="0" * 64,
    )

    with pytest.raises(
        InvalidNvdFeedArtifactError,
        match="SHA-256 does not match META",
    ):
        NvdFeedIntegrityVerifier().verify(
            payload=gzip_payload,
            meta=meta,
        )


def test_verify_rejects_invalid_gzip_payload() -> None:
    """Reject bytes that satisfy size evidence but are not valid gzip."""
    gzip_payload = b"this-is-not-a-gzip"
    meta = _build_meta(
        gzip_payload,
        declared_uncompressed_size=100,
    )

    with pytest.raises(
        InvalidNvdFeedArtifactError,
        match="not a valid complete gzip",
    ):
        NvdFeedIntegrityVerifier().verify(
            payload=gzip_payload,
            meta=meta,
        )


def test_verify_rejects_truncated_gzip_payload() -> None:
    """Reject an incomplete gzip artifact instead of accepting partial data."""
    complete_payload = _gzip_payload()
    truncated_payload = complete_payload[:-4]

    meta = _build_meta(
        truncated_payload,
        declared_uncompressed_size=len(UNCOMPRESSED_PAYLOAD),
    )

    with pytest.raises(
        InvalidNvdFeedArtifactError,
        match="not a valid complete gzip",
    ):
        NvdFeedIntegrityVerifier().verify(
            payload=truncated_payload,
            meta=meta,
        )
