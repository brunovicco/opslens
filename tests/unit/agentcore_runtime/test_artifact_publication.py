"""Tests for content-addressed AgentCore deployment artifact publication."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path

import pytest
from botocore.exceptions import ClientError

from opslens.agentcore_runtime.artifact_publication import (
    AGENTCORE_RUNTIME_PACKAGE_ARTIFACT_VERSION,
    AgentCoreArtifactPublicationError,
    publish_agentcore_artifact,
    verify_agentcore_artifact,
)


class _Body:
    def __init__(self, value: bytes) -> None:
        self._value = value
        self.closed = False

    def read(self) -> bytes:
        return self._value

    def close(self) -> None:
        self.closed = True


class _S3Client:
    def __init__(
        self,
        *,
        put_response: Mapping[str, object] | None = None,
        put_error: ClientError | None = None,
        existing_bytes: bytes = b"",
        existing_version_id: str = "version-existing",
    ) -> None:
        self.put_response = put_response or {"VersionId": "version-created"}
        self.put_error = put_error
        self.existing_bytes = existing_bytes
        self.existing_version_id = existing_version_id
        self.put_calls: list[dict[str, object]] = []
        self.body: _Body | None = None

    def put_object(
        self,
        *,
        Bucket: str,
        Key: str,
        Body: bytes,
        ContentType: str,
        Metadata: dict[str, str],
        IfNoneMatch: str,
    ) -> Mapping[str, object]:
        self.put_calls.append(
            {
                "Bucket": Bucket,
                "Key": Key,
                "Body": Body,
                "ContentType": ContentType,
                "Metadata": Metadata,
                "IfNoneMatch": IfNoneMatch,
            }
        )
        if self.put_error is not None:
            raise self.put_error
        return self.put_response

    def head_object(self, *, Bucket: str, Key: str) -> Mapping[str, object]:
        del Bucket, Key
        return {
            "VersionId": self.existing_version_id,
            "ContentLength": len(self.existing_bytes),
        }

    def get_object(
        self,
        *,
        Bucket: str,
        Key: str,
        VersionId: str,
    ) -> Mapping[str, object]:
        del Bucket, Key
        assert VersionId == self.existing_version_id
        self.body = _Body(self.existing_bytes)
        return {"Body": self.body}


def _write_artifact(tmp_path: Path, raw_bytes: bytes = b"bounded-runtime") -> tuple[Path, Path]:
    artifact_path = tmp_path / "opslens-agentcore-runtime.zip"
    manifest_path = tmp_path / "opslens-agentcore-runtime-package.json"
    artifact_path.write_bytes(raw_bytes)
    digest = hashlib.sha256(raw_bytes).hexdigest()
    manifest_path.write_text(
        json.dumps(
            {
                "artifact_version": AGENTCORE_RUNTIME_PACKAGE_ARTIFACT_VERSION,
                "compressed_bytes": len(raw_bytes),
                "sha256": digest,
                "zip_file": artifact_path.name,
            }
        ),
        encoding="utf-8",
    )
    return artifact_path, manifest_path


def _precondition_failed() -> ClientError:
    return ClientError(
        {
            "Error": {"Code": "PreconditionFailed", "Message": "exists"},
            "ResponseMetadata": {"HTTPStatusCode": 412},
        },
        "PutObject",
    )


def test_verified_artifact_uses_content_addressed_agentcore_key(tmp_path: Path) -> None:
    artifact_path, manifest_path = _write_artifact(tmp_path)

    artifact = verify_agentcore_artifact(
        artifact_path=artifact_path,
        manifest_path=manifest_path,
    )

    assert artifact.key == (
        f"agentcore/runtime/{artifact.sha256}/opslens-agentcore-runtime.zip"
    )
    assert artifact.size_bytes == len(b"bounded-runtime")


def test_manifest_digest_mismatch_fails_closed(tmp_path: Path) -> None:
    artifact_path, manifest_path = _write_artifact(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["sha256"] = "0" * 64
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(
        AgentCoreArtifactPublicationError,
        match="sha256 differs",
    ):
        verify_agentcore_artifact(
            artifact_path=artifact_path,
            manifest_path=manifest_path,
        )


def test_new_artifact_publication_is_create_only_and_returns_version(tmp_path: Path) -> None:
    artifact_path, manifest_path = _write_artifact(tmp_path)
    artifact = verify_agentcore_artifact(
        artifact_path=artifact_path,
        manifest_path=manifest_path,
    )
    client = _S3Client()

    evidence = publish_agentcore_artifact(
        client=client,
        bucket="opslens-dev-artifacts-example",
        artifact=artifact,
    )

    assert evidence.status == "created"
    assert evidence.version_id == "version-created"
    assert client.put_calls[0]["IfNoneMatch"] == "*"
    assert client.put_calls[0]["Key"] == artifact.key


def test_existing_exact_artifact_is_admitted_as_idempotent_replay(tmp_path: Path) -> None:
    artifact_path, manifest_path = _write_artifact(tmp_path)
    artifact = verify_agentcore_artifact(
        artifact_path=artifact_path,
        manifest_path=manifest_path,
    )
    client = _S3Client(
        put_error=_precondition_failed(),
        existing_bytes=artifact.raw_bytes,
    )

    evidence = publish_agentcore_artifact(
        client=client,
        bucket="opslens-dev-artifacts-example",
        artifact=artifact,
    )

    assert evidence.status == "replay_verified"
    assert evidence.version_id == "version-existing"
    assert client.body is not None
    assert client.body.closed is True


def test_existing_content_addressed_key_with_different_bytes_fails_closed(
    tmp_path: Path,
) -> None:
    artifact_path, manifest_path = _write_artifact(tmp_path)
    artifact = verify_agentcore_artifact(
        artifact_path=artifact_path,
        manifest_path=manifest_path,
    )
    client = _S3Client(
        put_error=_precondition_failed(),
        existing_bytes=b"different-bytes",
    )

    with pytest.raises(
        AgentCoreArtifactPublicationError,
        match="size differs",
    ):
        publish_agentcore_artifact(
            client=client,
            bucket="opslens-dev-artifacts-example",
            artifact=artifact,
        )
