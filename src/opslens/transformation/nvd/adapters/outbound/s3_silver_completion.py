"""Amazon S3 persistence and exact replay verification for NVD Silver COMPLETE."""

from collections.abc import Mapping
from hashlib import sha256
from typing import Protocol, TypedDict, cast

from botocore.exceptions import ClientError

from opslens.shared.observability.ports import OperationalTelemetry
from opslens.transformation.nvd.application.errors import (
    NvdSilverCompletionAlreadyExistsError,
)
from opslens.transformation.nvd.application.persistence_models import (
    NvdSilverStoredCompletionV1,
)
from opslens.transformation.nvd.completion.manifest import (
    NvdSilverCompletionArtifactV1,
)


class NvdSilverCompletionConcurrentWriteError(RuntimeError):
    """Raised when S3 reports a concurrent COMPLETE conditional write."""


class NvdSilverCompletionWriteEvidenceError(RuntimeError):
    """Raised when a successful COMPLETE write lacks exact version evidence."""


class NvdSilverCompletionReplayMismatchError(ValueError):
    """Raised when persisted COMPLETE bytes differ from the expected artifact."""


class S3ObjectBody(Protocol):
    """Define the readable S3 body capability required for COMPLETE replay."""

    def read(self) -> bytes:
        """Read the complete response body."""
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


class S3HeadCompletionResponse(TypedDict, total=False):
    """Represent current COMPLETE metadata."""

    ContentLength: int
    VersionId: str


class S3GetCompletionResponse(TypedDict, total=False):
    """Represent exact-version COMPLETE GetObject evidence."""

    Body: S3ObjectBody
    ContentLength: int
    VersionId: str


class S3NvdSilverCompletionClient(Protocol):
    """Define the minimal S3 operations required for COMPLETE persistence."""

    def put_object(
        self,
        *,
        Bucket: str,
        Key: str,
        Body: bytes,
        ContentType: str,
        Metadata: Mapping[str, str],
        IfNoneMatch: str,
    ) -> S3PutCompletionResponse:
        """Conditionally create COMPLETE."""
        ...

    def head_object(
        self,
        *,
        Bucket: str,
        Key: str,
    ) -> S3HeadCompletionResponse:
        """Read metadata for the current COMPLETE version."""
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


class S3NvdSilverCompletionRepository:
    """Create immutable NVD Silver COMPLETE manifests in S3."""

    CONTENT_TYPE = "application/json"

    def __init__(
        self,
        *,
        client: S3NvdSilverCompletionClient,
        bucket_name: str,
        telemetry: OperationalTelemetry,
    ) -> None:
        """Initialize COMPLETE persistence dependencies."""
        normalized_bucket = bucket_name.strip()

        if not normalized_bucket:
            raise ValueError("S3 NVD Silver COMPLETE bucket name cannot be empty.")

        self._client = client
        self._bucket_name = normalized_bucket
        self._telemetry = telemetry

    def put_if_absent(
        self,
        *,
        artifact: NvdSilverCompletionArtifactV1,
    ) -> NvdSilverStoredCompletionV1:
        """Create COMPLETE only when the deterministic key is absent."""
        fields = {
            "bucket": self._bucket_name,
            "object_key": artifact.manifest_key,
            "manifest_sha256": artifact.manifest_sha256,
            "size_bytes": len(artifact.manifest_bytes),
        }

        try:
            with self._telemetry.span("nvd.silver.s3.put_complete"):
                response = self._client.put_object(
                    Bucket=self._bucket_name,
                    Key=artifact.manifest_key,
                    Body=artifact.manifest_bytes,
                    ContentType=self.CONTENT_TYPE,
                    Metadata={
                        "dataset": "nvd_cve_versions",
                        "completion_status": "complete",
                        "manifest_sha256": artifact.manifest_sha256,
                    },
                    IfNoneMatch="*",
                )
        except ClientError as exc:
            self._handle_client_error(
                error=exc,
                artifact=artifact,
            )
            raise AssertionError("Unreachable after COMPLETE S3 error handling.") from exc

        version_id = response.get("VersionId")

        if not isinstance(version_id, str) or not version_id.strip():
            self._telemetry.metric(
                name="NvdSilverCompleteWriteEvidenceMismatch",
                value=1.0,
                unit="Count",
            )
            raise NvdSilverCompletionWriteEvidenceError(
                "Successful NVD Silver COMPLETE PutObject requires VersionId."
            )

        stored = NvdSilverStoredCompletionV1(
            key=artifact.manifest_key,
            version_id=version_id,
            sha256=artifact.manifest_sha256,
            size_bytes=len(artifact.manifest_bytes),
        )

        self._telemetry.metric(
            name="NvdSilverCompleteCreated",
            value=1.0,
            unit="Count",
        )
        self._telemetry.metric(
            name="NvdSilverCompleteWriteBytes",
            value=float(stored.size_bytes),
            unit="Bytes",
        )
        self._telemetry.info(
            "NVD Silver COMPLETE manifest created",
            fields={
                **fields,
                "version_id": stored.version_id,
            },
        )

        return stored

    def _handle_client_error(
        self,
        *,
        error: ClientError,
        artifact: NvdSilverCompletionArtifactV1,
    ) -> None:
        """Classify COMPLETE conditional-write failures."""
        status_code = self._extract_http_status(error)

        fields = {
            "bucket": self._bucket_name,
            "object_key": artifact.manifest_key,
            "http_status": status_code,
        }

        if status_code == 412:
            self._telemetry.metric(
                name="NvdSilverCompleteAlreadyExists",
                value=1.0,
                unit="Count",
            )
            raise NvdSilverCompletionAlreadyExistsError(
                "NVD Silver COMPLETE already exists and requires exact replay verification."
            ) from error

        if status_code == 409:
            self._telemetry.metric(
                name="NvdSilverCompleteConcurrentWrite",
                value=1.0,
                unit="Count",
            )
            raise NvdSilverCompletionConcurrentWriteError(
                "Concurrent NVD Silver COMPLETE conditional write conflict."
            ) from error

        self._telemetry.metric(
            name="NvdSilverCompleteWriteFailure",
            value=1.0,
            unit="Count",
        )
        self._telemetry.exception(
            "Failed to persist NVD Silver COMPLETE manifest",
            fields=fields,
        )
        raise error

    @staticmethod
    def _extract_http_status(
        error: ClientError,
    ) -> int | None:
        """Extract HTTP status from one Botocore ClientError."""
        response = cast(
            _S3ClientErrorResponse,
            error.response,
        )

        status_code = response.get(
            "ResponseMetadata",
            {},
        ).get("HTTPStatusCode")

        return status_code if isinstance(status_code, int) else None


class S3NvdSilverCompletionReplayVerifier:
    """Verify a pre-existing COMPLETE manifest by exact immutable version."""

    def __init__(
        self,
        *,
        client: S3NvdSilverCompletionClient,
        bucket_name: str,
        telemetry: OperationalTelemetry,
    ) -> None:
        """Initialize exact COMPLETE replay dependencies."""
        normalized_bucket = bucket_name.strip()

        if not normalized_bucket:
            raise ValueError("S3 NVD Silver COMPLETE replay bucket name cannot be empty.")

        self._client = client
        self._bucket_name = normalized_bucket
        self._telemetry = telemetry

    def verify_current(
        self,
        *,
        artifact: NvdSilverCompletionArtifactV1,
    ) -> NvdSilverStoredCompletionV1:
        """Accept replay only after byte-for-byte immutable-version proof."""
        try:
            with self._telemetry.span("nvd.silver.s3.head_complete"):
                head = self._client.head_object(
                    Bucket=self._bucket_name,
                    Key=artifact.manifest_key,
                )

            version_id = self._require_version_id(
                head.get("VersionId"),
                context="HeadObject",
            )

            content_length = self._require_content_length(
                head.get("ContentLength"),
                context="HeadObject",
            )

            if content_length != len(artifact.manifest_bytes):
                raise NvdSilverCompletionReplayMismatchError(
                    "Current NVD Silver COMPLETE size does not match."
                )

            with self._telemetry.span("nvd.silver.s3.get_complete_version"):
                response = self._client.get_object(
                    Bucket=self._bucket_name,
                    Key=artifact.manifest_key,
                    VersionId=version_id,
                )

                body = response.get("Body")

                if body is None:
                    raise NvdSilverCompletionReplayMismatchError(
                        "Exact COMPLETE GetObject response is missing Body."
                    )

                try:
                    payload = body.read()
                finally:
                    body.close()

            response_version_id = self._require_version_id(
                response.get("VersionId"),
                context="GetObject",
            )

            if response_version_id != version_id:
                raise NvdSilverCompletionReplayMismatchError(
                    "Exact COMPLETE GetObject VersionId does not match HEAD."
                )

            get_length = self._require_content_length(
                response.get("ContentLength"),
                context="GetObject",
            )

            if get_length != len(artifact.manifest_bytes):
                raise NvdSilverCompletionReplayMismatchError(
                    "Exact COMPLETE ContentLength does not match."
                )

            if len(payload) != len(artifact.manifest_bytes):
                raise NvdSilverCompletionReplayMismatchError(
                    "Exact COMPLETE payload size does not match."
                )

            persisted_sha256 = sha256(payload).hexdigest()

            if persisted_sha256 != artifact.manifest_sha256:
                raise NvdSilverCompletionReplayMismatchError(
                    "Exact COMPLETE SHA-256 does not match."
                )

            if payload != artifact.manifest_bytes:
                raise NvdSilverCompletionReplayMismatchError("Exact COMPLETE bytes do not match.")

        except NvdSilverCompletionReplayMismatchError:
            self._telemetry.metric(
                name="NvdSilverCompleteReplayMismatch",
                value=1.0,
                unit="Count",
            )
            raise
        except Exception:
            self._telemetry.metric(
                name="NvdSilverCompleteReplayFailure",
                value=1.0,
                unit="Count",
            )
            raise

        stored = NvdSilverStoredCompletionV1(
            key=artifact.manifest_key,
            version_id=version_id,
            sha256=persisted_sha256,
            size_bytes=len(payload),
        )

        self._telemetry.metric(
            name="NvdSilverCompleteReplayVerified",
            value=1.0,
            unit="Count",
        )

        return stored

    @staticmethod
    def _require_version_id(
        value: object,
        *,
        context: str,
    ) -> str:
        """Require exact S3 VersionId evidence."""
        if not isinstance(value, str) or not value.strip():
            raise NvdSilverCompletionReplayMismatchError(
                f"NVD Silver COMPLETE {context} requires VersionId."
            )

        return value

    @staticmethod
    def _require_content_length(
        value: object,
        *,
        context: str,
    ) -> int:
        """Require positive S3 ContentLength evidence."""
        if type(value) is not int or value <= 0:
            raise NvdSilverCompletionReplayMismatchError(
                f"NVD Silver COMPLETE {context} requires positive ContentLength."
            )

        return value
