"""Amazon S3 adapter for reading exact NVD Bronze object versions."""

from typing import Protocol, TypedDict

from opslens.shared.observability.ports import OperationalTelemetry
from opslens.transformation.nvd.provenance.models import (
    NvdBronzeObjectPayloadV1,
)


class NvdS3ObjectEvidenceMismatchError(ValueError):
    """Raised when S3 response evidence disagrees with the requested version."""


class S3ObjectBody(Protocol):
    """Define the readable S3 response-body capability used by this adapter."""

    def read(self) -> bytes:
        """Read the complete S3 object payload."""
        ...

    def close(self) -> None:
        """Release the underlying response-body resources."""
        ...


class S3GetObjectVersionResponse(TypedDict, total=False):
    """Represent the subset of versioned GetObject response fields we require."""

    Body: S3ObjectBody
    ContentLength: int
    VersionId: str


class S3GetObjectVersionClient(Protocol):
    """Define the exact-version S3 capability required by NVD Silver."""

    def get_object(
        self,
        *,
        Bucket: str,
        Key: str,
        VersionId: str,
    ) -> S3GetObjectVersionResponse:
        """Read one exact immutable S3 object version."""
        ...


class S3VersionedNvdBronzeObjectReader:
    """Read exact NVD Bronze versions from one configured S3 bucket."""

    def __init__(
        self,
        *,
        client: S3GetObjectVersionClient,
        bucket_name: str,
        telemetry: OperationalTelemetry,
    ) -> None:
        """Initialize the repository with explicit infrastructure dependencies."""
        normalized_bucket = bucket_name.strip()

        if not normalized_bucket:
            raise ValueError("S3 NVD Bronze bucket name cannot be empty.")

        self._client = client
        self._bucket_name = normalized_bucket
        self._telemetry = telemetry

    def get(
        self,
        *,
        key: str,
        version_id: str,
    ) -> NvdBronzeObjectPayloadV1:
        """Read one exact object version and verify S3 transport evidence."""
        normalized_key = key.strip()
        normalized_version_id = version_id.strip()

        if not normalized_key:
            raise ValueError("NVD Bronze object key cannot be empty.")

        if not normalized_version_id:
            raise ValueError("NVD Bronze object VersionId cannot be empty.")

        fields = {
            "bucket": self._bucket_name,
            "object_key": normalized_key,
            "version_id": normalized_version_id,
        }

        self._telemetry.info(
            "Reading exact NVD Bronze object version",
            fields=fields,
        )

        try:
            with self._telemetry.span("nvd.silver.s3.get_object_version"):
                response = self._client.get_object(
                    Bucket=self._bucket_name,
                    Key=normalized_key,
                    VersionId=normalized_version_id,
                )

                body = response.get("Body")

                if body is None:
                    raise NvdS3ObjectEvidenceMismatchError(
                        "Versioned S3 GetObject response is missing Body."
                    )

                try:
                    payload = body.read()
                finally:
                    body.close()

        except NvdS3ObjectEvidenceMismatchError:
            self._record_evidence_mismatch(
                key=normalized_key,
                version_id=normalized_version_id,
            )
            raise
        except Exception:
            self._telemetry.metric(
                name="NvdSilverBronzeReadFailure",
                value=1.0,
                unit="Count",
            )
            self._telemetry.exception(
                "Failed to read exact NVD Bronze object version",
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
        except NvdS3ObjectEvidenceMismatchError:
            self._record_evidence_mismatch(
                key=normalized_key,
                version_id=normalized_version_id,
            )
            raise

        self._telemetry.metric(
            name="NvdSilverBronzeReadBytes",
            value=float(len(payload)),
            unit="Bytes",
        )

        self._telemetry.info(
            "Exact NVD Bronze object version read",
            fields={
                "bucket": self._bucket_name,
                "object_key": normalized_key,
                "version_id": result.version_id,
                "payload_size_bytes": len(payload),
            },
        )

        return result

    @staticmethod
    def _verify_response(
        *,
        key: str,
        requested_version_id: str,
        response: S3GetObjectVersionResponse,
        payload: bytes,
    ) -> NvdBronzeObjectPayloadV1:
        """Cross-check the S3 response against the requested exact version."""
        response_version_id = response.get("VersionId")

        if not isinstance(response_version_id, str) or not response_version_id:
            raise NvdS3ObjectEvidenceMismatchError(
                "Versioned S3 GetObject response VersionId must be non-empty."
            )

        if response_version_id != requested_version_id:
            raise NvdS3ObjectEvidenceMismatchError(
                "S3 response VersionId does not match the requested NVD Bronze version."
            )

        content_length = response.get("ContentLength")

        if type(content_length) is not int or content_length <= 0:
            raise NvdS3ObjectEvidenceMismatchError(
                "Versioned S3 GetObject response ContentLength must be positive."
            )

        if content_length != len(payload):
            raise NvdS3ObjectEvidenceMismatchError(
                "S3 response ContentLength does not match the bytes actually read."
            )

        return NvdBronzeObjectPayloadV1(
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
            name="NvdSilverBronzeEvidenceMismatch",
            value=1.0,
            unit="Count",
        )

        self._telemetry.exception(
            "NVD Bronze transport evidence mismatch",
            fields={
                "bucket": self._bucket_name,
                "object_key": key,
                "version_id": version_id,
            },
        )
