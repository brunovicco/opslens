"""Amazon S3 persistence for immutable GHSA Silver COMPLETE manifests."""

import base64
from collections.abc import Mapping
from typing import Protocol, TypedDict, cast

from botocore.exceptions import ClientError

from opslens.shared.observability.ports import OperationalTelemetry
from opslens.transformation.ghsa.completion.manifest import (
    GhsaSilverCompletionArtifactV1,
)
from opslens.transformation.ghsa.completion.models import (
    GhsaSilverStoredCompletionV1,
)


class GhsaSilverCompletionConcurrentWriteError(RuntimeError):
    """Raised when S3 reports a concurrent COMPLETE conditional write."""


class GhsaSilverCompletionWriteEvidenceError(RuntimeError):
    """Raised when a successful COMPLETE write lacks exact persistence evidence."""


class GhsaSilverCompletionReplayMismatchError(RuntimeError):
    """Raised when an existing COMPLETE object fails exact replay verification."""


class S3ObjectBody(Protocol):
    """Define the readable S3 response body required for replay verification."""

    def read(self) -> bytes:
        """Read the complete object payload."""
        ...

    def close(self) -> None:
        """Release response-body resources."""
        ...


class _S3ResponseMetadata(TypedDict, total=False):
    """Represent S3 HTTP response metadata used for error classification."""

    HTTPStatusCode: int


class _S3ClientErrorResponse(TypedDict, total=False):
    """Represent the subset of S3 ClientError response we require."""

    ResponseMetadata: _S3ResponseMetadata


class S3PutCompletionResponse(TypedDict, total=False):
    """Represent successful COMPLETE PutObject evidence."""

    VersionId: str
    ChecksumSHA256: str


class S3HeadCompletionResponse(TypedDict, total=False):
    """Represent current COMPLETE discovery evidence."""

    ContentLength: int
    VersionId: str
    Metadata: dict[str, str]


class S3GetCompletionResponse(TypedDict, total=False):
    """Represent exact-version COMPLETE retrieval evidence."""

    Body: S3ObjectBody
    ContentLength: int
    VersionId: str
    Metadata: dict[str, str]


class S3GhsaSilverCompletionClient(Protocol):
    """Define S3 operations required for immutable COMPLETE persistence."""

    def put_object(
        self,
        *,
        Bucket: str,
        Key: str,
        Body: bytes,
        ContentType: str,
        Metadata: Mapping[str, str],
        ChecksumSHA256: str,
        IfNoneMatch: str,
    ) -> S3PutCompletionResponse:
        """Conditionally create one COMPLETE object."""
        ...

    def head_object(
        self,
        *,
        Bucket: str,
        Key: str,
    ) -> S3HeadCompletionResponse:
        """Discover the current COMPLETE object version."""
        ...

    def get_object(
        self,
        *,
        Bucket: str,
        Key: str,
        VersionId: str,
    ) -> S3GetCompletionResponse:
        """Read one exact COMPLETE object version."""
        ...


class S3GhsaSilverCompletionRepository:
    """Create immutable GHSA Silver COMPLETE manifests in Amazon S3."""

    CONTENT_TYPE = "application/json"

    def __init__(
        self,
        *,
        client: S3GhsaSilverCompletionClient,
        bucket_name: str,
        telemetry: OperationalTelemetry,
    ) -> None:
        """Initialize exact COMPLETE persistence dependencies."""
        normalized_bucket = bucket_name.strip()

        if not normalized_bucket:
            raise ValueError(
                "S3 GHSA Silver COMPLETE bucket name cannot be empty."
            )

        self._client = client
        self._bucket_name = normalized_bucket
        self._telemetry = telemetry

    def put_if_absent(
        self,
        artifact: GhsaSilverCompletionArtifactV1,
    ) -> GhsaSilverStoredCompletionV1:
        """Create COMPLETE or verify an exact immutable replay."""
        checksum_sha256 = self._checksum_sha256_base64(
            artifact.manifest_sha256
        )
        metadata = self._build_metadata(artifact)
        fields = {
            "bucket": self._bucket_name,
            "object_key": artifact.key,
            "manifest_sha256": artifact.manifest_sha256,
            "size_bytes": len(artifact.manifest_bytes),
            "attempt_id": artifact.manifest.context.attempt_id,
        }

        try:
            with self._telemetry.span("ghsa.silver.s3.put_complete"):
                response = self._client.put_object(
                    Bucket=self._bucket_name,
                    Key=artifact.key,
                    Body=artifact.manifest_bytes,
                    ContentType=self.CONTENT_TYPE,
                    Metadata=metadata,
                    ChecksumSHA256=checksum_sha256,
                    IfNoneMatch="*",
                )
        except ClientError as exc:
            status_code = self._extract_http_status(exc)

            if status_code == 412:
                return self._verify_existing_replay(
                    artifact=artifact,
                    expected_metadata=metadata,
                )

            if status_code == 409:
                self._telemetry.metric(
                    name="GhsaSilverCompleteConcurrentWrite",
                    value=1.0,
                    unit="Count",
                )
                self._telemetry.exception(
                    "Concurrent GHSA Silver COMPLETE conditional write conflict",
                    fields=fields,
                )
                raise GhsaSilverCompletionConcurrentWriteError(
                    "Concurrent GHSA Silver COMPLETE conditional write conflict."
                ) from exc

            self._telemetry.metric(
                name="GhsaSilverCompleteWriteFailure",
                value=1.0,
                unit="Count",
            )
            self._telemetry.exception(
                "Failed to persist GHSA Silver COMPLETE manifest",
                fields={
                    **fields,
                    "http_status": status_code,
                },
            )
            raise

        try:
            version_id = self._require_version_id(response)
            self._require_write_checksum(
                response=response,
                expected_checksum_sha256=checksum_sha256,
            )
        except GhsaSilverCompletionWriteEvidenceError:
            self._telemetry.metric(
                name="GhsaSilverCompleteWriteEvidenceMismatch",
                value=1.0,
                unit="Count",
            )
            self._telemetry.exception(
                "GHSA Silver COMPLETE write lacks exact S3 evidence",
                fields=fields,
            )
            raise

        stored = self._stored_completion(
            artifact=artifact,
            version_id=version_id,
        )

        self._telemetry.metric(
            name="GhsaSilverCompleteCreated",
            value=1.0,
            unit="Count",
        )
        self._telemetry.metric(
            name="GhsaSilverCompleteWriteBytes",
            value=float(stored.size_bytes),
            unit="Bytes",
        )
        self._telemetry.info(
            "GHSA Silver COMPLETE manifest created",
            fields={
                **fields,
                "version_id": version_id,
            },
        )

        return stored

    def _verify_existing_replay(
        self,
        *,
        artifact: GhsaSilverCompletionArtifactV1,
        expected_metadata: Mapping[str, str],
    ) -> GhsaSilverStoredCompletionV1:
        """Accept existing COMPLETE only after exact immutable-version proof."""
        fields = {
            "bucket": self._bucket_name,
            "object_key": artifact.key,
            "attempt_id": artifact.manifest.context.attempt_id,
        }
        self._telemetry.metric(
            name="GhsaSilverCompleteAlreadyExists",
            value=1.0,
            unit="Count",
        )

        try:
            with self._telemetry.span("ghsa.silver.s3.verify_complete_replay"):
                head = self._client.head_object(
                    Bucket=self._bucket_name,
                    Key=artifact.key,
                )
                version_id = self._validate_head(
                    artifact=artifact,
                    response=head,
                    expected_metadata=expected_metadata,
                )
                response = self._client.get_object(
                    Bucket=self._bucket_name,
                    Key=artifact.key,
                    VersionId=version_id,
                )
                body = response.get("Body")

                if body is None:
                    raise GhsaSilverCompletionReplayMismatchError(
                        "GHSA Silver COMPLETE replay response is missing Body."
                    )

                try:
                    self._validate_get_before_read(
                        artifact=artifact,
                        requested_version_id=version_id,
                        response=response,
                        expected_metadata=expected_metadata,
                    )
                    payload = body.read()
                finally:
                    body.close()

                if payload != artifact.manifest_bytes:
                    raise GhsaSilverCompletionReplayMismatchError(
                        "GHSA Silver COMPLETE replay bytes do not match."
                    )
        except GhsaSilverCompletionReplayMismatchError:
            self._telemetry.metric(
                name="GhsaSilverCompleteReplayMismatch",
                value=1.0,
                unit="Count",
            )
            self._telemetry.exception(
                "Existing GHSA Silver COMPLETE failed replay verification",
                fields=fields,
            )
            raise

        stored = self._stored_completion(
            artifact=artifact,
            version_id=version_id,
        )
        self._telemetry.metric(
            name="GhsaSilverCompleteReplayVerified",
            value=1.0,
            unit="Count",
        )
        self._telemetry.info(
            "Existing GHSA Silver COMPLETE replay verified",
            fields={
                **fields,
                "version_id": version_id,
            },
        )

        return stored

    @staticmethod
    def _build_metadata(
        artifact: GhsaSilverCompletionArtifactV1,
    ) -> Mapping[str, str]:
        """Build bounded deterministic metadata for COMPLETE evidence."""
        manifest = artifact.manifest

        return {
            "dataset": "ghsa_advisory_versions",
            "schema_version": "1",
            "completion_status": "complete",
            "sync_id": manifest.context.sync_id,
            "attempt_id": manifest.context.attempt_id,
            "record_count": str(manifest.record_count),
            "manifest_sha256": artifact.manifest_sha256,
        }

    @staticmethod
    def _checksum_sha256_base64(manifest_sha256: str) -> str:
        """Convert hexadecimal manifest SHA-256 to S3 base64 checksum form."""
        return base64.b64encode(bytes.fromhex(manifest_sha256)).decode("ascii")

    @staticmethod
    def _require_version_id(response: S3PutCompletionResponse) -> str:
        """Require exact VersionId evidence from a successful write."""
        version_id = response.get("VersionId")

        if not isinstance(version_id, str) or not version_id.strip():
            raise GhsaSilverCompletionWriteEvidenceError(
                "Successful GHSA Silver COMPLETE PutObject requires VersionId."
            )

        return version_id

    @staticmethod
    def _require_write_checksum(
        *,
        response: S3PutCompletionResponse,
        expected_checksum_sha256: str,
    ) -> None:
        """Require S3 to acknowledge the exact SHA-256 supplied for COMPLETE."""
        if response.get("ChecksumSHA256") != expected_checksum_sha256:
            raise GhsaSilverCompletionWriteEvidenceError(
                "Successful GHSA Silver COMPLETE PutObject requires the exact "
                "ChecksumSHA256."
            )

    @staticmethod
    def _validate_head(
        *,
        artifact: GhsaSilverCompletionArtifactV1,
        response: S3HeadCompletionResponse,
        expected_metadata: Mapping[str, str],
    ) -> str:
        """Validate current COMPLETE discovery before exact retrieval."""
        version_id = response.get("VersionId")

        if not isinstance(version_id, str) or not version_id.strip():
            raise GhsaSilverCompletionReplayMismatchError(
                "GHSA Silver COMPLETE HeadObject requires VersionId."
            )

        if response.get("ContentLength") != len(artifact.manifest_bytes):
            raise GhsaSilverCompletionReplayMismatchError(
                "GHSA Silver COMPLETE HeadObject ContentLength does not match."
            )

        if response.get("Metadata") != dict(expected_metadata):
            raise GhsaSilverCompletionReplayMismatchError(
                "GHSA Silver COMPLETE HeadObject metadata does not match."
            )

        return version_id

    @staticmethod
    def _validate_get_before_read(
        *,
        artifact: GhsaSilverCompletionArtifactV1,
        requested_version_id: str,
        response: S3GetCompletionResponse,
        expected_metadata: Mapping[str, str],
    ) -> None:
        """Validate exact COMPLETE version evidence before reading bytes."""
        if response.get("VersionId") != requested_version_id:
            raise GhsaSilverCompletionReplayMismatchError(
                "GHSA Silver COMPLETE GetObject VersionId does not match."
            )

        if response.get("ContentLength") != len(artifact.manifest_bytes):
            raise GhsaSilverCompletionReplayMismatchError(
                "GHSA Silver COMPLETE GetObject ContentLength does not match."
            )

        if response.get("Metadata") != dict(expected_metadata):
            raise GhsaSilverCompletionReplayMismatchError(
                "GHSA Silver COMPLETE GetObject metadata does not match."
            )

    @staticmethod
    def _stored_completion(
        *,
        artifact: GhsaSilverCompletionArtifactV1,
        version_id: str,
    ) -> GhsaSilverStoredCompletionV1:
        """Bind exact persisted S3 evidence to one COMPLETE artifact."""
        return GhsaSilverStoredCompletionV1(
            key=artifact.key,
            version_id=version_id,
            sha256=artifact.manifest_sha256,
            size_bytes=len(artifact.manifest_bytes),
        )

    @staticmethod
    def _extract_http_status(error: ClientError) -> int | None:
        """Extract HTTP status from one Botocore ClientError."""
        response = cast(_S3ClientErrorResponse, error.response)
        status_code = response.get("ResponseMetadata", {}).get(
            "HTTPStatusCode"
        )

        return status_code if isinstance(status_code, int) else None
