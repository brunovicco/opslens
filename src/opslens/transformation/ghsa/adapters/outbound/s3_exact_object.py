"""Amazon S3 adapter for reading exact GHSA Bronze object versions."""

from typing import Protocol, TypedDict

from opslens.shared.observability.ports import OperationalTelemetry
from opslens.transformation.ghsa.runtime.object_payload import (
    GhsaBronzeObjectPayloadV1,
)

GHSA_SILVER_MAX_MANIFEST_BYTES = 1 * 1024 * 1024
GHSA_SILVER_MAX_PAGE_BYTES = 8 * 1024 * 1024


class GhsaS3ObjectEvidenceMismatchError(ValueError):
    """Raised when S3 evidence disagrees with the requested exact version."""


class S3ObjectBody(Protocol):
    """Define the readable S3 response-body capability used by this adapter."""

    def read(self) -> bytes:
        """Read the complete S3 object payload."""
        ...

    def close(self) -> None:
        """Release the underlying response-body resources."""
        ...


class S3GetObjectVersionResponse(TypedDict, total=False):
    """Represent the versioned GetObject fields required by GHSA Silver."""

    Body: S3ObjectBody
    ContentLength: int
    VersionId: str


class S3GetObjectVersionClient(Protocol):
    """Define the exact-version S3 capability required by GHSA Silver."""

    def get_object(
        self,
        *,
        Bucket: str,
        Key: str,
        VersionId: str,
    ) -> S3GetObjectVersionResponse:
        """Read one exact immutable S3 object version."""
        ...


class S3VersionedGhsaBronzeObjectReader:
    """Read exact GHSA Bronze versions from one configured S3 bucket."""

    def __init__(
        self,
        *,
        client: S3GetObjectVersionClient,
        bucket_name: str,
        telemetry: OperationalTelemetry,
        max_manifest_bytes: int = GHSA_SILVER_MAX_MANIFEST_BYTES,
        max_page_bytes: int = GHSA_SILVER_MAX_PAGE_BYTES,
    ) -> None:
        """Initialize the adapter with explicit infrastructure dependencies."""
        normalized_bucket = bucket_name.strip()

        if not normalized_bucket:
            raise ValueError(
                "S3 GHSA Bronze bucket name cannot be empty."
            )

        if type(max_manifest_bytes) is not int or max_manifest_bytes <= 0:
            raise ValueError(
                "GHSA Silver maximum Bronze manifest size "
                "must be a positive integer."
            )

        if type(max_page_bytes) is not int or max_page_bytes <= 0:
            raise ValueError(
                "GHSA Silver maximum Bronze page size "
                "must be a positive integer."
            )

        self._client = client
        self._bucket_name = normalized_bucket
        self._telemetry = telemetry
        self._max_manifest_bytes = max_manifest_bytes
        self._max_page_bytes = max_page_bytes

    def get(
        self,
        *,
        key: str,
        version_id: str,
    ) -> GhsaBronzeObjectPayloadV1:
        """Read one exact object version and verify S3 transport evidence."""
        normalized_key = key.strip()
        normalized_version_id = version_id.strip()

        if not normalized_key:
            raise ValueError(
                "GHSA Bronze object key cannot be empty."
            )

        if not normalized_version_id:
            raise ValueError(
                "GHSA Bronze object VersionId cannot be empty."
            )

        fields = {
            "bucket": self._bucket_name,
            "object_key": normalized_key,
            "version_id": normalized_version_id,
        }

        self._telemetry.info(
            "Reading exact GHSA Bronze object version",
            fields=fields,
        )

        try:
            with self._telemetry.span(
                "ghsa.silver.s3.get_object_version"
            ):
                response = self._client.get_object(
                    Bucket=self._bucket_name,
                    Key=normalized_key,
                    VersionId=normalized_version_id,
                )

                body = response.get("Body")

                if body is None:
                    raise GhsaS3ObjectEvidenceMismatchError(
                        "Versioned S3 GetObject response is missing Body."
                    )

                max_object_bytes = self._max_object_bytes_for_key(
                    normalized_key
                )

                try:
                    self._validate_pre_read_response(
                        requested_version_id=normalized_version_id,
                        response=response,
                        max_object_bytes=max_object_bytes,
                    )

                    payload = body.read()
                finally:
                    body.close()

        except GhsaS3ObjectEvidenceMismatchError:
            self._record_evidence_mismatch(
                key=normalized_key,
                version_id=normalized_version_id,
            )
            raise

        except Exception:
            self._telemetry.metric(
                name="GhsaSilverBronzeReadFailure",
                value=1.0,
                unit="Count",
            )

            self._telemetry.exception(
                "Failed to read exact GHSA Bronze object version",
                fields=fields,
            )
            raise

        try:
            result = self._verify_response(
                key=normalized_key,
                requested_version_id=normalized_version_id,
                response=response,
                payload=payload,
            )

        except GhsaS3ObjectEvidenceMismatchError:
            self._record_evidence_mismatch(
                key=normalized_key,
                version_id=normalized_version_id,
            )
            raise

        self._telemetry.metric(
            name="GhsaSilverBronzeReadBytes",
            value=float(len(payload)),
            unit="Bytes",
        )

        self._telemetry.info(
            "Exact GHSA Bronze object version read",
            fields={
                "bucket": self._bucket_name,
                "object_key": normalized_key,
                "version_id": result.version_id,
                "payload_size_bytes": len(payload),
            },
        )

        return result

    def _max_object_bytes_for_key(
        self,
        key: str,
    ) -> int:
        """Return the bounded read envelope for one GHSA Bronze object."""
        if key.endswith("/manifest.json"):
            return self._max_manifest_bytes

        return self._max_page_bytes

    @staticmethod
    def _validate_pre_read_response(
        *,
        requested_version_id: str,
        response: S3GetObjectVersionResponse,
        max_object_bytes: int,
    ) -> None:
        """Validate exact S3 metadata before materializing object bytes."""
        response_version_id = response.get("VersionId")

        if (
            not isinstance(response_version_id, str)
            or not response_version_id
        ):
            raise GhsaS3ObjectEvidenceMismatchError(
                "Versioned S3 GetObject response VersionId "
                "must be non-empty."
            )

        if response_version_id != requested_version_id:
            raise GhsaS3ObjectEvidenceMismatchError(
                "S3 response VersionId does not match the requested "
                "GHSA Bronze version."
            )

        content_length = response.get("ContentLength")

        if type(content_length) is not int or content_length <= 0:
            raise GhsaS3ObjectEvidenceMismatchError(
                "Versioned S3 GetObject response ContentLength "
                "must be positive."
            )

        if content_length > max_object_bytes:
            raise GhsaS3ObjectEvidenceMismatchError(
                "Versioned S3 GetObject response ContentLength "
                "exceeds the configured GHSA Bronze object size limit."
            )

    @staticmethod
    def _verify_response(
        *,
        key: str,
        requested_version_id: str,
        response: S3GetObjectVersionResponse,
        payload: bytes,
    ) -> GhsaBronzeObjectPayloadV1:
        """Cross-check S3 transport evidence against bytes actually read."""
        response_version_id = response.get("VersionId")

        if (
            not isinstance(response_version_id, str)
            or not response_version_id
        ):
            raise GhsaS3ObjectEvidenceMismatchError(
                "Versioned S3 GetObject response VersionId "
                "must be non-empty."
            )

        if response_version_id != requested_version_id:
            raise GhsaS3ObjectEvidenceMismatchError(
                "S3 response VersionId does not match the requested "
                "GHSA Bronze version."
            )

        content_length = response.get("ContentLength")

        if type(content_length) is not int or content_length <= 0:
            raise GhsaS3ObjectEvidenceMismatchError(
                "Versioned S3 GetObject response ContentLength "
                "must be positive."
            )

        if content_length != len(payload):
            raise GhsaS3ObjectEvidenceMismatchError(
                "S3 response ContentLength does not match "
                "the bytes actually read."
            )

        return GhsaBronzeObjectPayloadV1(
            key=key,
            version_id=response_version_id,
            raw_bytes=payload,
        )

    def _record_evidence_mismatch(
        self,
        *,
        key: str,
        version_id: str,
    ) -> None:
        """Record exact-version transport evidence failures."""
        self._telemetry.metric(
            name="GhsaSilverBronzeEvidenceMismatch",
            value=1.0,
            unit="Count",
        )

        self._telemetry.exception(
            "GHSA Bronze transport evidence mismatch",
            fields={
                "bucket": self._bucket_name,
                "object_key": key,
                "version_id": version_id,
            },
        )
