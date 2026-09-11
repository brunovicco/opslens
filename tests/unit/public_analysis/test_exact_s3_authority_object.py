"""Tests for exact-version S3 authority object reads used before Gate 19.2 measurement."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from opslens.public_analysis.adapters.exact_s3_authority_object import (
    ExactS3AuthorityObjectError,
    ExactS3AuthorityObjectReader,
    ExactS3GetObjectResponse,
)


def _call_log() -> list[tuple[str, str, str]]:
    """Return a typed mutable call log for strict Pyright."""
    return []


@dataclass(slots=True)
class FakeBody:
    """Return deterministic bytes and record resource closure."""

    payload: bytes
    closed: bool = False

    def read(self) -> bytes:
        """Return the configured payload."""
        return self.payload

    def close(self) -> None:
        """Record that response-body resources were released."""
        self.closed = True


@dataclass(slots=True)
class FakeS3Client:
    """Expose only exact-version GetObject and record every physical call."""

    response: ExactS3GetObjectResponse
    calls: list[tuple[str, str, str]] = field(default_factory=_call_log)

    def get_object(
        self,
        *,
        Bucket: str,
        Key: str,
        VersionId: str,
    ) -> ExactS3GetObjectResponse:
        """Record one exact immutable request and return configured evidence."""
        self.calls.append((Bucket, Key, VersionId))
        return self.response


def _reader(client: FakeS3Client, *, max_bytes: int = 1024) -> ExactS3AuthorityObjectReader:
    """Build one bounded exact-version reader for test evidence."""
    return ExactS3AuthorityObjectReader(
        client=client,
        bucket_name="opslens-dev-data",
        max_bytes=max_bytes,
    )


def test_reader_performs_one_exact_version_get_and_closes_body() -> None:
    """One admitted coordinate becomes exactly one bounded GetObject request."""
    body = FakeBody(b"authority")
    client = FakeS3Client(
        {
            "Body": body,
            "VersionId": "version-7",
            "ContentLength": len(body.payload),
        }
    )

    result = _reader(client).read(
        object_key="silver/example.parquet",
        version_id="version-7",
    )

    assert result.object_key == "silver/example.parquet"
    assert result.version_id == "version-7"
    assert result.payload == b"authority"
    assert result.metadata == ()
    assert client.calls == [
        ("opslens-dev-data", "silver/example.parquet", "version-7")
    ]
    assert body.closed is True


def test_reader_preserves_metadata_as_frozen_deterministic_evidence() -> None:
    """User metadata from the same exact GetObject remains immutable and ordered."""
    body = FakeBody(b"authority")
    client = FakeS3Client(
        {
            "Body": body,
            "VersionId": "version-7",
            "ContentLength": len(body.payload),
            "Metadata": {
                "retrieved_at": "2026-09-10T14:03:00+00:00",
                "source": "cisa-kev",
                "catalog_version": "2026.09.10",
            },
        }
    )

    result = _reader(client).read(
        object_key="bronze/kev/catalog.json",
        version_id="version-7",
    )

    assert result.metadata == (
        ("catalog_version", "2026.09.10"),
        ("retrieved_at", "2026-09-10T14:03:00+00:00"),
        ("source", "cisa-kev"),
    )
    assert result.metadata_value("retrieved_at") == "2026-09-10T14:03:00+00:00"
    assert result.metadata_value("missing") is None
    assert client.calls == [
        ("opslens-dev-data", "bronze/kev/catalog.json", "version-7")
    ]


def test_reader_rejects_malformed_metadata_before_body_read() -> None:
    """Contradictory user metadata fails closed without consuming object bytes."""
    body = FakeBody(b"authority")
    client = FakeS3Client(
        {
            "Body": body,
            "VersionId": "version-7",
            "ContentLength": len(body.payload),
            "Metadata": {"retrieved_at": ""},
        }
    )

    with pytest.raises(ExactS3AuthorityObjectError, match="metadata values"):
        _reader(client).read(
            object_key="bronze/kev/catalog.json",
            version_id="version-7",
        )

    assert body.closed is False
    assert client.calls == [
        ("opslens-dev-data", "bronze/kev/catalog.json", "version-7")
    ]


def test_reader_fails_before_provider_io_for_invalid_coordinates() -> None:
    """Empty physical coordinates never become mutable or ambiguous S3 reads."""
    client = FakeS3Client({})
    reader = _reader(client)

    with pytest.raises(ExactS3AuthorityObjectError, match="object_key"):
        reader.read(object_key=" ", version_id="version-7")
    with pytest.raises(ExactS3AuthorityObjectError, match="version_id"):
        reader.read(object_key="silver/example.parquet", version_id="")

    assert client.calls == []


def test_reader_rejects_contradictory_version_and_missing_body() -> None:
    """Successful transport without exact immutable evidence fails closed."""
    mismatch = FakeS3Client(
        {
            "Body": FakeBody(b"x"),
            "VersionId": "different-version",
            "ContentLength": 1,
        }
    )
    with pytest.raises(ExactS3AuthorityObjectError, match="VersionId"):
        _reader(mismatch).read(
            object_key="silver/example.parquet",
            version_id="version-7",
        )

    missing_body = FakeS3Client({"VersionId": "version-7", "ContentLength": 1})
    with pytest.raises(ExactS3AuthorityObjectError, match="missing Body"):
        _reader(missing_body).read(
            object_key="silver/example.parquet",
            version_id="version-7",
        )


def test_reader_rejects_oversize_before_body_read() -> None:
    """ContentLength enforces the source-specific budget before bytes are consumed."""
    body = FakeBody(b"0123456789")
    client = FakeS3Client(
        {"Body": body, "VersionId": "version-7", "ContentLength": 10}
    )

    with pytest.raises(ExactS3AuthorityObjectError, match="byte limit"):
        _reader(client, max_bytes=5).read(
            object_key="silver/example.parquet",
            version_id="version-7",
        )

    assert body.closed is False


def test_reader_closes_body_and_rejects_content_length_mismatch() -> None:
    """Read bytes remain bound to provider ContentLength evidence."""
    body = FakeBody(b"abc")
    client = FakeS3Client(
        {"Body": body, "VersionId": "version-7", "ContentLength": 4}
    )

    with pytest.raises(ExactS3AuthorityObjectError, match="ContentLength"):
        _reader(client).read(
            object_key="silver/example.parquet",
            version_id="version-7",
        )

    assert body.closed is True


def test_reader_requires_explicit_bucket_and_positive_budget() -> None:
    """Composition cannot omit resource identity or bounded-read policy."""
    client = FakeS3Client({})

    with pytest.raises(ValueError, match="bucket"):
        ExactS3AuthorityObjectReader(
            client=client,
            bucket_name=" ",
            max_bytes=1024,
        )
    with pytest.raises(ValueError, match="max_bytes"):
        ExactS3AuthorityObjectReader(
            client=client,
            bucket_name="opslens-dev-data",
            max_bytes=0,
        )
