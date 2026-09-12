"""Content-addressed publication contract for AgentCore direct-code artifacts."""

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, cast, runtime_checkable

from botocore.exceptions import ClientError

AGENTCORE_RUNTIME_PACKAGE_ARTIFACT_VERSION = "agentcore-runtime-package:v1"
AGENTCORE_RUNTIME_ARTIFACT_PREFIX = "agentcore/runtime"
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$", re.ASCII)


class AgentCoreArtifactPublicationError(ValueError):
    """Raised when an AgentCore deployment artifact cannot be admitted safely."""


@runtime_checkable
class _ReadableBody(Protocol):
    """Minimum body contract required to verify an existing S3 object."""

    def read(self) -> bytes:
        """Read the complete response body."""
        ...

    def close(self) -> None:
        """Close the response body."""
        ...


class S3AgentCoreArtifactClient(Protocol):
    """Narrow S3 client surface required for create-only artifact publication."""

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
        """Create an artifact only when the content-addressed key is absent."""
        ...

    def head_object(self, *, Bucket: str, Key: str) -> Mapping[str, object]:
        """Read exact current object metadata for replay verification."""
        ...

    def get_object(
        self,
        *,
        Bucket: str,
        Key: str,
        VersionId: str,
    ) -> Mapping[str, object]:
        """Read one exact object version for byte verification."""
        ...


@dataclass(frozen=True, slots=True)
class VerifiedAgentCoreArtifact:
    """Represent an artifact whose ZIP bytes agree with its deterministic manifest."""

    path: Path
    manifest_path: Path
    raw_bytes: bytes
    sha256: str
    size_bytes: int
    key: str


@dataclass(frozen=True, slots=True)
class AgentCoreArtifactPublicationEvidence:
    """Describe one successful create-only publication or exact replay verification."""

    bucket: str
    key: str
    sha256: str
    size_bytes: int
    version_id: str
    status: str

    def to_payload(self) -> dict[str, object]:
        """Return deterministic JSON-safe publication evidence."""
        return {
            "bucket": self.bucket,
            "key": self.key,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
            "status": self.status,
            "version_id": self.version_id,
        }


def _require_string(mapping: Mapping[str, object], key: str) -> str:
    value = mapping.get(key)
    if type(value) is not str or not value:
        raise AgentCoreArtifactPublicationError(f"manifest {key} must be a non-empty string")
    return value


def _require_int(mapping: Mapping[str, object], key: str) -> int:
    value = mapping.get(key)
    if type(value) is not int or value < 0:
        raise AgentCoreArtifactPublicationError(
            f"manifest {key} must be a non-negative integer"
        )
    return value


def _load_manifest(path: Path) -> Mapping[str, object]:
    try:
        parsed = cast(object, json.loads(path.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError) as exc:
        raise AgentCoreArtifactPublicationError("package manifest cannot be read as JSON") from exc
    if not isinstance(parsed, dict):
        raise AgentCoreArtifactPublicationError("package manifest must contain one JSON object")
    return cast(dict[str, object], parsed)


def verify_agentcore_artifact(
    *,
    artifact_path: Path,
    manifest_path: Path,
) -> VerifiedAgentCoreArtifact:
    """Bind direct-code ZIP bytes to the package builder's deterministic manifest."""
    try:
        raw_bytes = artifact_path.read_bytes()
    except OSError as exc:
        raise AgentCoreArtifactPublicationError("runtime ZIP cannot be read") from exc
    if not raw_bytes:
        raise AgentCoreArtifactPublicationError("runtime ZIP cannot be empty")

    manifest = _load_manifest(manifest_path)
    if _require_string(manifest, "artifact_version") != AGENTCORE_RUNTIME_PACKAGE_ARTIFACT_VERSION:
        raise AgentCoreArtifactPublicationError("unexpected AgentCore package artifact_version")

    expected_sha256 = _require_string(manifest, "sha256")
    if _SHA256_PATTERN.fullmatch(expected_sha256) is None:
        raise AgentCoreArtifactPublicationError("manifest sha256 must be lowercase hexadecimal")
    actual_sha256 = hashlib.sha256(raw_bytes).hexdigest()
    if actual_sha256 != expected_sha256:
        raise AgentCoreArtifactPublicationError("runtime ZIP sha256 differs from package manifest")

    expected_size = _require_int(manifest, "compressed_bytes")
    if len(raw_bytes) != expected_size:
        raise AgentCoreArtifactPublicationError("runtime ZIP size differs from package manifest")

    expected_zip_file = _require_string(manifest, "zip_file")
    if artifact_path.name != expected_zip_file:
        raise AgentCoreArtifactPublicationError(
            "runtime ZIP filename differs from package manifest"
        )

    key = f"{AGENTCORE_RUNTIME_ARTIFACT_PREFIX}/{actual_sha256}/{artifact_path.name}"
    return VerifiedAgentCoreArtifact(
        path=artifact_path,
        manifest_path=manifest_path,
        raw_bytes=raw_bytes,
        sha256=actual_sha256,
        size_bytes=len(raw_bytes),
        key=key,
    )


def _client_error_http_status(exc: ClientError) -> int | None:
    response = cast(Mapping[str, object], exc.response)
    metadata = response.get("ResponseMetadata")
    if not isinstance(metadata, Mapping):
        return None
    status = cast(Mapping[object, object], metadata).get("HTTPStatusCode")
    return status if type(status) is int else None


def _required_version_id(response: Mapping[str, object], *, context: str) -> str:
    version_id = response.get("VersionId")
    if type(version_id) is not str or not version_id.strip():
        raise AgentCoreArtifactPublicationError(f"{context} requires a non-empty S3 VersionId")
    return version_id


def _verify_existing(
    *,
    client: S3AgentCoreArtifactClient,
    bucket: str,
    artifact: VerifiedAgentCoreArtifact,
) -> str:
    head = client.head_object(Bucket=bucket, Key=artifact.key)
    version_id = _required_version_id(head, context="existing artifact")
    size = head.get("ContentLength")
    if type(size) is not int or size != artifact.size_bytes:
        raise AgentCoreArtifactPublicationError(
            "existing content-addressed artifact size differs from local ZIP"
        )

    response = client.get_object(
        Bucket=bucket,
        Key=artifact.key,
        VersionId=version_id,
    )
    body = response.get("Body")
    if not isinstance(body, _ReadableBody):
        raise AgentCoreArtifactPublicationError(
            "existing artifact response is missing readable Body"
        )
    try:
        existing_bytes = body.read()
    finally:
        body.close()
    if existing_bytes != artifact.raw_bytes:
        raise AgentCoreArtifactPublicationError(
            "existing content-addressed artifact bytes differ from local ZIP"
        )
    return version_id


def publish_agentcore_artifact(
    *,
    client: S3AgentCoreArtifactClient,
    bucket: str,
    artifact: VerifiedAgentCoreArtifact,
) -> AgentCoreArtifactPublicationEvidence:
    """Publish one immutable artifact or prove an exact idempotent replay."""
    if type(bucket) is not str or not bucket.strip():
        raise AgentCoreArtifactPublicationError("bucket must be a non-empty string")

    status = "created"
    try:
        response = client.put_object(
            Bucket=bucket,
            Key=artifact.key,
            Body=artifact.raw_bytes,
            ContentType="application/zip",
            Metadata={
                "sha256": artifact.sha256,
                "component": "agentcore-runtime",
                "artifact-version": AGENTCORE_RUNTIME_PACKAGE_ARTIFACT_VERSION,
            },
            IfNoneMatch="*",
        )
        version_id = _required_version_id(response, context="successful artifact publication")
    except ClientError as exc:
        if _client_error_http_status(exc) != 412:
            raise
        status = "replay_verified"
        version_id = _verify_existing(
            client=client,
            bucket=bucket,
            artifact=artifact,
        )

    return AgentCoreArtifactPublicationEvidence(
        bucket=bucket,
        key=artifact.key,
        sha256=artifact.sha256,
        size_bytes=artifact.size_bytes,
        version_id=version_id,
        status=status,
    )


__all__ = [
    "AGENTCORE_RUNTIME_ARTIFACT_PREFIX",
    "AGENTCORE_RUNTIME_PACKAGE_ARTIFACT_VERSION",
    "AgentCoreArtifactPublicationError",
    "AgentCoreArtifactPublicationEvidence",
    "S3AgentCoreArtifactClient",
    "VerifiedAgentCoreArtifact",
    "publish_agentcore_artifact",
    "verify_agentcore_artifact",
]
