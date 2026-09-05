"""Tests for bounded checksummed Gate 7.3 S3 publication and verification."""

from __future__ import annotations

import base64
from hashlib import sha256
from typing import cast

import pytest

from opslens.knowledge_retrieval.adapters.s3_publication import (
    BoundedS3PublicationStore,
    S3PublicationStoreError,
    S3PublicationTarget,
)
from opslens.knowledge_retrieval.application.bedrock_publication import (
    BEDROCK_PUBLICATION_PREFIX,
    BedrockPublicationObject,
    BedrockPublicationPlan,
)
from opslens.knowledge_retrieval.application.s3_publication import (
    CONTENT_APPLICATION_JSON,
    CONTENT_TEXT_PLAIN,
    PublicationPayload,
    S3PublicationValidationError,
    publish_bedrock_plan,
)


def _digest(value: str) -> str:
    """Return one UTF-8 SHA-256 test digest."""
    return sha256(value.encode("utf-8")).hexdigest()


def _publication_object(*, suffix: str, text: str) -> BedrockPublicationObject:
    """Return one fully validated publication object for S3 adapter tests."""
    content_sha256 = _digest(text)
    metadata_json = '{"metadataAttributes":{}}\n'
    return BedrockPublicationObject(
        chunk_id=f"knowledge-chunk:test-s3:{suffix}:v1",
        document_id="knowledge-doc:test-s3:v1",
        content_key=f"{BEDROCK_PUBLICATION_PREFIX}/chunks/{content_sha256}.txt",
        metadata_key=(
            f"{BEDROCK_PUBLICATION_PREFIX}/chunks/{content_sha256}.txt.metadata.json"
        ),
        content_text=text,
        content_sha256=content_sha256,
        metadata_json=metadata_json,
        metadata_sha256=_digest(metadata_json),
        custom_metadata_byte_count=2,
        custom_metadata_key_count=1,
    )


def _plan() -> BedrockPublicationPlan:
    """Return a deterministic two-chunk plan for remote-store tests."""
    return BedrockPublicationPlan(
        prefix=BEDROCK_PUBLICATION_PREFIX,
        source_manifest_sha256="a" * 64,
        objects=(
            _publication_object(suffix="first", text="alpha"),
            _publication_object(suffix="second", text="beta"),
        ),
    )


class _FakeS3Client:
    """Stateful dynamic SDK fake that stores only bytes supplied through PutObject."""

    def __init__(self) -> None:
        self.objects: dict[str, tuple[bytes, str, str]] = {}
        self.put_requests: list[dict[str, object]] = []
        self.truncated = False
        self.corrupt_head_checksum = False

    def put_object(self, **kwargs: object) -> object:
        """Capture one PutObject request and persist its exact fake object state."""
        request = dict(kwargs)
        self.put_requests.append(request)
        key = cast(str, request["Key"])
        body = cast(bytes, request["Body"])
        content_type = cast(str, request["ContentType"])
        checksum = cast(str, request["ChecksumSHA256"])
        self.objects[key] = (body, content_type, checksum)
        return {"ChecksumSHA256": checksum}

    def list_objects_v2(self, **kwargs: object) -> object:
        """Return keys beneath the requested prefix with an explicit truncation flag."""
        prefix = cast(str, kwargs["Prefix"])
        keys = sorted(key for key in self.objects if key.startswith(prefix))
        return {
            "IsTruncated": self.truncated,
            "KeyCount": len(keys),
            "Contents": [{"Key": key} for key in keys],
        }

    def head_object(self, **kwargs: object) -> object:
        """Return size/type/checksum evidence for one captured object."""
        key = cast(str, kwargs["Key"])
        body, content_type, checksum = self.objects[key]
        if self.corrupt_head_checksum:
            checksum = base64.b64encode(b"x" * 32).decode("ascii")
        return {
            "ContentLength": len(body),
            "ContentType": content_type,
            "ChecksumSHA256": checksum,
            "ServerSideEncryption": "AES256",
        }


class _ProviderCodeError(RuntimeError):
    """Small SDK-style exception carrying only a synthetic provider response."""

    def __init__(self, code: str) -> None:
        super().__init__("synthetic provider failure")
        self.response: dict[str, object] = {"Error": {"Code": code}}


class _FailingPutClient(_FakeS3Client):
    """Fake S3 client that raises one SDK-style provider code on PutObject."""

    def put_object(self, **kwargs: object) -> object:
        """Raise one deterministic provider error without storing the object."""
        _ = kwargs
        raise _ProviderCodeError("AccessDenied")


def _store(client: _FakeS3Client) -> BoundedS3PublicationStore:
    """Return one adapter fixed to the real OpsLens account-shape boundary."""
    return BoundedS3PublicationStore(
        client,
        S3PublicationTarget(
            bucket_name="opslens-dev-data-487757851499-us-east-1",
            expected_bucket_owner="487757851499",
        ),
    )


def test_publish_writes_checksummed_objects_then_verifies_exact_prefix() -> None:
    """Successful publication proves all content and sidecars through HeadObject checksums."""
    client = _FakeS3Client()
    evidence = publish_bedrock_plan(_plan(), _store(client))

    assert evidence.payload_count == 4
    assert len(evidence.objects) == 4
    assert evidence.total_byte_count == sum(item.byte_count for item in evidence.objects)
    assert len(client.put_requests) == 4
    assert {cast(str, request["ContentType"]) for request in client.put_requests} == {
        CONTENT_TEXT_PLAIN,
        CONTENT_APPLICATION_JSON,
    }
    assert all(request["ServerSideEncryption"] == "AES256" for request in client.put_requests)
    assert all(
        request["ExpectedBucketOwner"] == "487757851499"
        for request in client.put_requests
    )
    for request in client.put_requests:
        body = cast(bytes, request["Body"])
        expected_base64 = base64.b64encode(sha256(body).digest()).decode("ascii")
        assert request["ChecksumSHA256"] == expected_base64


def test_publish_rejects_unexpected_object_under_authorized_prefix() -> None:
    """One stale/foreign object prevents the prefix from becoming ingestible authority."""
    client = _FakeS3Client()
    client.objects[f"{BEDROCK_PUBLICATION_PREFIX}/unexpected.txt"] = (
        b"unexpected",
        CONTENT_TEXT_PLAIN,
        base64.b64encode(sha256(b"unexpected").digest()).decode("ascii"),
    )

    with pytest.raises(S3PublicationValidationError, match="unexpected"):
        publish_bedrock_plan(_plan(), _store(client))


def test_publish_rejects_remote_checksum_drift() -> None:
    """A stored checksum mismatch fails verification without trusting ETag semantics."""
    client = _FakeS3Client()
    client.corrupt_head_checksum = True

    with pytest.raises(S3PublicationValidationError, match="SHA-256"):
        publish_bedrock_plan(_plan(), _store(client))


def test_adapter_fails_closed_when_prefix_requires_pagination() -> None:
    """The tiny v1 publisher never follows an unexpectedly large object listing."""
    client = _FakeS3Client()
    client.truncated = True

    with pytest.raises(S3PublicationStoreError, match="exceeds"):
        _store(client).list_keys(f"{BEDROCK_PUBLICATION_PREFIX}/")


def test_adapter_exposes_only_bounded_provider_error_code() -> None:
    """Transport diagnostics retain a safe provider code without provider response bodies."""
    client = _FailingPutClient()
    payload = PublicationPayload(
        key=f"{BEDROCK_PUBLICATION_PREFIX}/chunks/example.txt",
        body=b"example",
        content_type=CONTENT_TEXT_PLAIN,
        checksum_sha256=sha256(b"example").hexdigest(),
    )

    with pytest.raises(S3PublicationStoreError, match="provider_code=AccessDenied") as exc_info:
        _store(client).put(payload)

    assert "synthetic provider failure" not in str(exc_info.value)
