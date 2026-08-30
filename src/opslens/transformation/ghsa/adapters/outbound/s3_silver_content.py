"""Amazon S3 adapter for immutable GHSA Silver content persistence."""

import base64
from collections.abc import Mapping
from typing import Protocol, TypedDict, cast

from botocore.exceptions import ClientError

from opslens.shared.observability.ports import OperationalTelemetry
from opslens.transformation.ghsa.completion.models import (
    GhsaSilverStoredContentObjectV1,
)
from opslens.transformation.ghsa.completion.preparation import (
    GhsaSilverPreparedContentObjectV1,
)


class GhsaSilverContentConcurrentWriteError(RuntimeError):
    """Raised when S3 reports a concurrent conditional-write conflict."""


class GhsaSilverContentWriteEvidenceError(RuntimeError):
    """Raised when a successful S3 write lacks exact persistence evidence."""


class GhsaSilverContentReplayMismatchError(RuntimeError):
    """Raised when an existing content-addressed object fails exact replay checks."""


class S3ObjectBody(Protocol):
    """Define the readable S3 response-body capability used by replay checks."""

    def read(self) -> bytes:
        """Read the complete S3 object payload."""
        ...

    def close(self) -> None:
        """Release the underlying response-body resources."""
        ...


class _S3ResponseMetadata(TypedDict, total=False):
    """Represent S3 HTTP metadata required for ClientError classification."""

    HTTPStatusCode: int


class _S3ClientErrorResponse(TypedDict, total=False):
    """Represent the subset of a Botocore ClientError response we require."""

    ResponseMetadata: _S3ResponseMetadata


class S3PutObjectResponse(TypedDict, total=False):
    """Represent successful conditional PutObject evidence."""

    VersionId: str
    ETag: str
    ChecksumSHA256: str


class S3HeadObjectResponse(TypedDict, total=False):
    """Represent current-version discovery evidence for replay verification."""

    VersionId: str
    ContentLength: int
    Metadata: dict[str, str]


class S3GetObjectResponse(TypedDict, total=False):
    """Represent exact-version GetObject evidence for replay verification."""

    Body: S3ObjectBody
    VersionId: str
    ContentLength: int
    Metadata: dict[str, str]


class S3GhsaSilverContentClient(Protocol):
    """Define the S3 capabilities required for immutable Silver persistence."""

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
    ) -> S3PutObjectResponse:
        """Conditionally create one immutable content-addressed object."""
        ...

    def head_object(
        self,
        *,
        Bucket: str,
        Key: str,
    ) -> S3HeadObjectResponse:
        """Discover the current object version for replay verification."""
        ...

    def get_object(
        self,
        *,
        Bucket: str,
        Key: str,
        VersionId: str,
    ) -> S3GetObjectResponse:
        """Read one exact existing object version for replay verification."""
        ...


class S3GhsaSilverContentRepository:
    """Persist one-row GHSA Silver content objects with exact replay semantics."""

    CONTENT_TYPE = "application/vnd.apache.parquet"
    DATASET = "ghsa_advisory_versions"
    SCHEMA_VERSION = "1"

    def __init__(
        self,
        *,
        client: S3GhsaSilverContentClient,
        bucket_name: str,
        telemetry: OperationalTelemetry,
    ) -> None:
        """Initialize the repository with explicit infrastructure dependencies."""
        normalized_bucket = bucket_name.strip()

        if not normalized_bucket:
            raise ValueError("S3 GHSA Silver bucket name cannot be empty.")

        self._client = client
        self._bucket_name = normalized_bucket
        self._telemetry = telemetry

    def put_if_absent(
        self,
        prepared: GhsaSilverPreparedContentObjectV1,
    ) -> GhsaSilverStoredContentObjectV1:
        """Create one immutable content object or verify an exact existing replay."""
        artifact = prepared.parquet_artifact
        metadata = self._build_metadata(prepared)
        checksum_sha256 = self._checksum_sha256_base64(
            artifact.parquet_sha256
        )
        fields = {
            "bucket": self._bucket_name,
            "object_key": prepared.key,
            "ghsa_id": prepared.ghsa_id,
            "observed_advisory_version_id": (
                prepared.observed_advisory_version_id
            ),
            "parquet_sha256": artifact.parquet_sha256,
            "size_bytes": artifact.size_bytes,
        }

        self._telemetry.info(
            "Persisting GHSA Silver content object",
            fields=fields,
        )

        try:
            with self._telemetry.span("ghsa.silver.s3.put_content"):
                response = self._client.put_object(
                    Bucket=self._bucket_name,
                    Key=prepared.key,
                    Body=artifact.parquet_bytes,
                    ContentType=self.CONTENT_TYPE,
                    Metadata=metadata,
                    ChecksumSHA256=checksum_sha256,
                    IfNoneMatch="*",
                )
        except ClientError as exc:
            status_code = self._extract_http_status(exc)

            if status_code == 412:
                return self._verify_existing_replay(
                    prepared=prepared,
                    expected_metadata=metadata,
                )

            if status_code == 409:
                self._telemetry.metric(
                    name="GhsaSilverContentConcurrentWrite",
                    value=1.0,
                    unit="Count",
                )
                self._telemetry.exception(
                    "Concurrent GHSA Silver content conditional write conflict",
                    fields=fields,
                )
                raise GhsaSilverContentConcurrentWriteError(
                    "Concurrent GHSA Silver content conditional write conflict."
                ) from exc

            self._telemetry.metric(
                name="GhsaSilverContentWriteFailure",
                value=1.0,
                unit="Count",
            )
            self._telemetry.exception(
                "Failed to persist GHSA Silver content object",
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
        except GhsaSilverContentWriteEvidenceError:
            self._telemetry.metric(
                name="GhsaSilverContentWriteEvidenceMismatch",
                value=1.0,
                unit="Count",
            )
            self._telemetry.exception(
                "GHSA Silver content write lacks exact S3 evidence",
                fields=fields,
            )
            raise

        stored = self._stored_content(
            prepared=prepared,
            version_id=version_id,
        )

        self._telemetry.metric(
            name="GhsaSilverContentCreated",
            value=1.0,
            unit="Count",
        )
        self._telemetry.metric(
            name="GhsaSilverContentWriteBytes",
            value=float(artifact.size_bytes),
            unit="Bytes",
        )
        self._telemetry.info(
            "GHSA Silver content object created",
            fields={
                **fields,
                "version_id": version_id,
            },
        )

        return stored

    def _verify_existing_replay(
        self,
        *,
        prepared: GhsaSilverPreparedContentObjectV1,
        expected_metadata: Mapping[str, str],
    ) -> GhsaSilverStoredContentObjectV1:
        """Accept a 412 only after exact current-version replay verification."""
        fields = {
            "bucket": self._bucket_name,
            "object_key": prepared.key,
            "observed_advisory_version_id": (
                prepared.observed_advisory_version_id
            ),
        }
        self._telemetry.metric(
            name="GhsaSilverContentAlreadyExists",
            value=1.0,
            unit="Count",
        )
        self._telemetry.info(
            "GHSA Silver content key already exists; verifying replay",
            fields=fields,
        )

        try:
            with self._telemetry.span("ghsa.silver.s3.verify_content_replay"):
                head = self._client.head_object(
                    Bucket=self._bucket_name,
                    Key=prepared.key,
                )
                version_id = self._validate_head(
                    prepared=prepared,
                    response=head,
                    expected_metadata=expected_metadata,
                )
                response = self._client.get_object(
                    Bucket=self._bucket_name,
                    Key=prepared.key,
                    VersionId=version_id,
                )
                body = response.get("Body")

                if body is None:
                    raise GhsaSilverContentReplayMismatchError(
                        "GHSA Silver replay GetObject response is missing Body."
                    )

                try:
                    self._validate_get_before_read(
                        prepared=prepared,
                        requested_version_id=version_id,
                        response=response,
                        expected_metadata=expected_metadata,
                    )
                    payload = body.read()
                finally:
                    body.close()

                self._validate_replay_payload(
                    prepared=prepared,
                    payload=payload,
                )
        except GhsaSilverContentReplayMismatchError:
            self._telemetry.metric(
                name="GhsaSilverContentReplayMismatch",
                value=1.0,
                unit="Count",
            )
            self._telemetry.exception(
                "Existing GHSA Silver content failed exact replay verification",
                fields=fields,
            )
            raise

        stored = self._stored_content(
            prepared=prepared,
            version_id=version_id,
        )

        self._telemetry.metric(
            name="GhsaSilverContentReplayVerified",
            value=1.0,
            unit="Count",
        )
        self._telemetry.info(
            "Existing GHSA Silver content replay verified",
            fields={
                **fields,
                "version_id": version_id,
            },
        )

        return stored

    @classmethod
    def _build_metadata(
        cls,
        prepared: GhsaSilverPreparedContentObjectV1,
    ) -> Mapping[str, str]:
        """Build bounded identity metadata for one authoritative content row."""
        artifact = prepared.parquet_artifact

        return {
            "dataset": cls.DATASET,
            "schema_version": cls.SCHEMA_VERSION,
            "ghsa_id": prepared.ghsa_id,
            "observed_advisory_version_id": (
                prepared.observed_advisory_version_id
            ),
            "source_advisory_sha256": prepared.source_advisory_sha256,
            "parquet_sha256": artifact.parquet_sha256,
            "row_count": str(artifact.row_count),
        }

    @staticmethod
    def _checksum_sha256_base64(parquet_sha256: str) -> str:
        """Convert the frozen hexadecimal artifact digest to S3 checksum form."""
        return base64.b64encode(bytes.fromhex(parquet_sha256)).decode("ascii")

    @staticmethod
    def _require_version_id(response: S3PutObjectResponse) -> str:
        """Require an exact VersionId from a successful conditional write."""
        version_id = response.get("VersionId")

        if not isinstance(version_id, str) or not version_id.strip():
            raise GhsaSilverContentWriteEvidenceError(
                "Successful GHSA Silver PutObject response requires VersionId."
            )

        return version_id

    @staticmethod
    def _require_write_checksum(
        *,
        response: S3PutObjectResponse,
        expected_checksum_sha256: str,
    ) -> None:
        """Require S3 to acknowledge the exact SHA-256 sent with the upload."""
        actual = response.get("ChecksumSHA256")

        if actual != expected_checksum_sha256:
            raise GhsaSilverContentWriteEvidenceError(
                "Successful GHSA Silver PutObject response requires the exact "
                "ChecksumSHA256."
            )

    @staticmethod
    def _validate_head(
        *,
        prepared: GhsaSilverPreparedContentObjectV1,
        response: S3HeadObjectResponse,
        expected_metadata: Mapping[str, str],
    ) -> str:
        """Validate current-version discovery before exact-version retrieval."""
        version_id = response.get("VersionId")

        if not isinstance(version_id, str) or not version_id.strip():
            raise GhsaSilverContentReplayMismatchError(
                "GHSA Silver replay HeadObject requires VersionId."
            )

        content_length = response.get("ContentLength")

        if content_length != prepared.parquet_artifact.size_bytes:
            raise GhsaSilverContentReplayMismatchError(
                "GHSA Silver replay HeadObject ContentLength does not match."
            )

        metadata = response.get("Metadata")

        if metadata != dict(expected_metadata):
            raise GhsaSilverContentReplayMismatchError(
                "GHSA Silver replay HeadObject metadata does not match."
            )

        return version_id

    @staticmethod
    def _validate_get_before_read(
        *,
        prepared: GhsaSilverPreparedContentObjectV1,
        requested_version_id: str,
        response: S3GetObjectResponse,
        expected_metadata: Mapping[str, str],
    ) -> None:
        """Validate exact-version response metadata before reading replay bytes."""
        version_id = response.get("VersionId")

        if version_id != requested_version_id:
            raise GhsaSilverContentReplayMismatchError(
                "GHSA Silver replay GetObject VersionId does not match request."
            )

        if response.get("ContentLength") != prepared.parquet_artifact.size_bytes:
            raise GhsaSilverContentReplayMismatchError(
                "GHSA Silver replay GetObject ContentLength does not match."
            )

        if response.get("Metadata") != dict(expected_metadata):
            raise GhsaSilverContentReplayMismatchError(
                "GHSA Silver replay GetObject metadata does not match."
            )

    @staticmethod
    def _validate_replay_payload(
        *,
        prepared: GhsaSilverPreparedContentObjectV1,
        payload: bytes,
    ) -> None:
        """Require exact byte equality for a content-addressed replay."""
        if payload != prepared.parquet_artifact.parquet_bytes:
            raise GhsaSilverContentReplayMismatchError(
                "GHSA Silver replay object bytes do not match deterministic Parquet."
            )

    @staticmethod
    def _stored_content(
        *,
        prepared: GhsaSilverPreparedContentObjectV1,
        version_id: str,
    ) -> GhsaSilverStoredContentObjectV1:
        """Bind exact persisted S3 evidence to one advisory content version."""
        artifact = prepared.parquet_artifact

        return GhsaSilverStoredContentObjectV1(
            key=prepared.key,
            version_id=version_id,
            observed_advisory_version_id=(
                prepared.observed_advisory_version_id
            ),
            ghsa_id=prepared.ghsa_id,
            source_advisory_sha256=prepared.source_advisory_sha256,
            parquet_sha256=artifact.parquet_sha256,
            size_bytes=artifact.size_bytes,
            row_count=artifact.row_count,
        )

    @staticmethod
    def _extract_http_status(error: ClientError) -> int | None:
        """Extract the S3 HTTP status from one Botocore ClientError."""
        response = cast(_S3ClientErrorResponse, error.response)
        metadata = response.get("ResponseMetadata", {})
        status_code = metadata.get("HTTPStatusCode")

        return status_code if isinstance(status_code, int) else None
