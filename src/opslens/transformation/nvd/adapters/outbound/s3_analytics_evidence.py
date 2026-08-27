"""Exact-version Amazon S3 reader for NVD analytics authority evidence."""

from collections.abc import Mapping
from typing import NoReturn, Protocol, TypedDict, cast

from botocore.exceptions import ClientError

from opslens.shared.observability.ports import OperationalTelemetry
from opslens.transformation.nvd.completion.promotion import (
    NvdPersistedObjectPayloadV1,
)


class NvdAnalyticsEvidenceS3ReadError(RuntimeError):
    """Raised when exact analytics authority evidence cannot be read from S3."""


class NvdAnalyticsEvidenceS3EvidenceError(RuntimeError):
    """Raised when S3 returns invalid exact-version analytics evidence."""


class _ReadableBody(Protocol):
    """Define the bounded S3 response-body operations used by this adapter."""

    def read(
        self,
        amt: int | None = None,
    ) -> bytes:
        """Read response bytes."""
        ...

    def close(self) -> None:
        """Close the response stream."""
        ...


class S3NvdAnalyticsEvidenceClient(Protocol):
    """Define the minimal S3 capability required for exact analytics reads."""

    def get_object(
        self,
        *,
        Bucket: str,
        Key: str,
        VersionId: str,
    ) -> Mapping[str, object]:
        """Read one exact versioned object."""
        ...


class _S3ResponseMetadata(TypedDict, total=False):
    """Represent HTTP metadata inspected from Botocore errors."""

    HTTPStatusCode: int


class _S3ClientErrorResponse(TypedDict, total=False):
    """Represent the Botocore error response fields inspected here."""

    ResponseMetadata: _S3ResponseMetadata


class S3NvdAnalyticsEvidenceReaderV1:
    """Read bounded exact authority versions for permanent analytics projection."""

    def __init__(
        self,
        *,
        client: S3NvdAnalyticsEvidenceClient,
        bucket_name: str,
        telemetry: OperationalTelemetry,
    ) -> None:
        """Initialize exact-version S3 access with analytics-owned telemetry."""
        normalized_bucket = bucket_name.strip()
        if not normalized_bucket or normalized_bucket != bucket_name:
            raise ValueError(
                "NVD analytics evidence S3 bucket name must be exact and non-empty."
            )

        self._client = client
        self._bucket_name = normalized_bucket
        self._telemetry = telemetry

    def read_exact(
        self,
        *,
        key: str,
        version_id: str,
        max_bytes: int,
    ) -> NvdPersistedObjectPayloadV1:
        """Read exactly one immutable authority object within a hard byte bound."""
        normalized_key = key.strip()
        if not normalized_key or normalized_key != key:
            raise ValueError(
                "NVD analytics evidence S3 object key must be exact and non-empty."
            )

        normalized_version_id = version_id.strip()
        if not normalized_version_id or normalized_version_id != version_id:
            raise ValueError(
                "NVD analytics evidence S3 VersionId must be exact and non-empty."
            )

        if type(max_bytes) is not int or max_bytes <= 0:
            raise ValueError(
                "NVD analytics evidence S3 max_bytes must be a positive integer."
            )

        fields = {
            "bucket": self._bucket_name,
            "object_key": normalized_key,
            "version_id": normalized_version_id,
            "max_bytes": max_bytes,
        }

        self._telemetry.info(
            "Reading exact NVD analytics authority evidence object",
            fields=fields,
        )

        try:
            with self._telemetry.span(
                "nvd.analytics.s3.get_authority_object_version"
            ):
                response = self._client.get_object(
                    Bucket=self._bucket_name,
                    Key=normalized_key,
                    VersionId=normalized_version_id,
                )
        except ClientError as exc:
            self._telemetry.metric(
                name="NvdAnalyticsEvidenceReadFailure",
                value=1.0,
                unit="Count",
            )
            self._telemetry.exception(
                "Failed to read exact NVD analytics authority evidence object",
                fields={
                    **fields,
                    "http_status": self._extract_http_status(exc),
                },
            )
            raise NvdAnalyticsEvidenceS3ReadError(
                "Failed to read exact NVD analytics authority evidence object."
            ) from exc

        body_value = response.get("Body")
        if (
            body_value is None
            or not hasattr(body_value, "read")
            or not hasattr(body_value, "close")
        ):
            self._raise_evidence_mismatch(
                "Versioned S3 GetObject response Body is invalid.",
                fields=fields,
            )

        body = cast(_ReadableBody, body_value)

        try:
            response_version_id = response.get("VersionId")
            if (
                not isinstance(response_version_id, str)
                or not response_version_id
            ):
                self._raise_evidence_mismatch(
                    "Versioned S3 GetObject response VersionId must be non-empty.",
                    fields=fields,
                )

            if response_version_id != normalized_version_id:
                self._raise_evidence_mismatch(
                    "S3 response VersionId does not match requested analytics authority.",
                    fields=fields,
                )

            content_length = response.get("ContentLength")
            if type(content_length) is not int or content_length <= 0:
                self._raise_evidence_mismatch(
                    "Versioned S3 GetObject response ContentLength must be positive.",
                    fields=fields,
                )

            if content_length > max_bytes:
                self._raise_evidence_mismatch(
                    "NVD analytics authority evidence exceeds configured read bound.",
                    fields=fields,
                )

            payload = body.read(content_length + 1)

            if len(payload) != content_length:
                self._raise_evidence_mismatch(
                    "S3 response ContentLength does not match bytes actually read.",
                    fields=fields,
                )

            if len(payload) > max_bytes:
                self._raise_evidence_mismatch(
                    "NVD analytics authority evidence bytes exceed configured read bound.",
                    fields=fields,
                )
        finally:
            body.close()

        self._telemetry.metric(
            name="NvdAnalyticsEvidenceBytes",
            value=float(len(payload)),
            unit="Bytes",
        )
        self._telemetry.info(
            "Loaded exact NVD analytics authority evidence object",
            fields={
                **fields,
                "payload_size_bytes": len(payload),
            },
        )

        return NvdPersistedObjectPayloadV1(
            key=normalized_key,
            version_id=normalized_version_id,
            raw_bytes=payload,
        )

    def _raise_evidence_mismatch(
        self,
        message: str,
        *,
        fields: Mapping[str, object],
    ) -> NoReturn:
        """Emit analytics-owned evidence telemetry and fail closed."""
        self._telemetry.metric(
            name="NvdAnalyticsEvidenceMismatch",
            value=1.0,
            unit="Count",
        )
        self._telemetry.exception(
            message,
            fields=fields,
        )
        raise NvdAnalyticsEvidenceS3EvidenceError(message)

    @staticmethod
    def _extract_http_status(exc: ClientError) -> int | None:
        """Return the Botocore HTTP status when present."""
        response = cast(_S3ClientErrorResponse, exc.response)
        metadata = response.get("ResponseMetadata")
        if metadata is None:
            return None

        status = metadata.get("HTTPStatusCode")
        return status if type(status) is int else None
