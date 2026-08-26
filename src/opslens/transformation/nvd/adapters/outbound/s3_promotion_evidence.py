"""Exact-version Amazon S3 reader for NVD watermark promotion evidence."""

from collections.abc import Mapping
from typing import Protocol, TypedDict, cast

from botocore.exceptions import ClientError

from opslens.shared.observability.ports import OperationalTelemetry
from opslens.transformation.nvd.completion.promotion import (
    NvdPersistedObjectPayloadV1,
)


class NvdPromotionS3ReadError(RuntimeError):
    """Raised when exact promotion evidence cannot be read from S3."""


class NvdPromotionS3EvidenceError(RuntimeError):
    """Raised when S3 returns invalid exact-version promotion evidence."""


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


class S3NvdPromotionEvidenceClient(Protocol):
    """Define the minimal S3 capability required for exact promotion reads."""

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


class S3NvdPromotionEvidenceReaderV1:
    """Read bounded exact Silver object versions for watermark promotion."""

    def __init__(
        self,
        *,
        client: S3NvdPromotionEvidenceClient,
        bucket_name: str,
        telemetry: OperationalTelemetry,
    ) -> None:
        """Initialize exact-version S3 access with explicit dependencies."""
        normalized_bucket = bucket_name.strip()
        if not normalized_bucket:
            raise ValueError(
                "NVD promotion S3 bucket name cannot be empty."
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
        """Read exactly one immutable object version within a hard byte bound."""
        normalized_key = key.strip()
        if not normalized_key or normalized_key != key:
            raise ValueError(
                "NVD promotion S3 object key must be exact and non-empty."
            )

        normalized_version_id = version_id.strip()
        if not normalized_version_id or normalized_version_id != version_id:
            raise ValueError(
                "NVD promotion S3 object VersionId must be exact and non-empty."
            )

        if type(max_bytes) is not int or max_bytes <= 0:
            raise ValueError(
                "NVD promotion S3 max_bytes must be a positive integer."
            )

        self._telemetry.info(
            "Reading exact NVD promotion evidence object",
            fields={
                "bucket": self._bucket_name,
                "object_key": normalized_key,
                "version_id": normalized_version_id,
                "max_bytes": max_bytes,
            },
        )

        try:
            with self._telemetry.span(
                "nvd.promotion.s3.get_object_version"
            ):
                response = self._client.get_object(
                    Bucket=self._bucket_name,
                    Key=normalized_key,
                    VersionId=normalized_version_id,
                )
        except ClientError as exc:
            status_code = self._extract_http_status(exc)
            self._telemetry.metric(
                name="NvdPromotionS3ObjectReadFailure",
                value=1.0,
                unit="Count",
            )
            self._telemetry.exception(
                "Failed to read exact NVD promotion evidence object",
                fields={
                    "bucket": self._bucket_name,
                    "object_key": normalized_key,
                    "version_id": normalized_version_id,
                    "http_status": status_code,
                },
            )
            raise NvdPromotionS3ReadError(
                "Failed to read exact NVD promotion evidence object."
            ) from exc

        body_value = response.get("Body")
        if (
            body_value is None
            or not hasattr(body_value, "read")
            or not hasattr(body_value, "close")
        ):
            raise NvdPromotionS3EvidenceError(
                "Versioned S3 GetObject response Body is invalid."
            )

        body = cast(_ReadableBody, body_value)

        try:
            response_version_id = response.get("VersionId")
            if (
                not isinstance(response_version_id, str)
                or not response_version_id
            ):
                raise NvdPromotionS3EvidenceError(
                    "Versioned S3 GetObject response VersionId must be non-empty."
                )

            if response_version_id != normalized_version_id:
                raise NvdPromotionS3EvidenceError(
                    "S3 response VersionId does not match the requested "
                    "NVD promotion evidence version."
                )

            content_length = response.get("ContentLength")
            if type(content_length) is not int or content_length <= 0:
                raise NvdPromotionS3EvidenceError(
                    "Versioned S3 GetObject response ContentLength must be positive."
                )

            if content_length > max_bytes:
                raise NvdPromotionS3EvidenceError(
                    "NVD promotion evidence object exceeds the configured read bound."
                )

            payload = body.read(content_length + 1)

            if len(payload) != content_length:
                raise NvdPromotionS3EvidenceError(
                    "S3 response ContentLength does not match the bytes actually read."
                )

            if len(payload) > max_bytes:
                raise NvdPromotionS3EvidenceError(
                    "NVD promotion evidence bytes exceed the configured read bound."
                )
        finally:
            body.close()

        self._telemetry.metric(
            name="NvdPromotionS3ObjectBytes",
            value=float(len(payload)),
            unit="Bytes",
        )
        self._telemetry.info(
            "Loaded exact NVD promotion evidence object",
            fields={
                "bucket": self._bucket_name,
                "object_key": normalized_key,
                "version_id": normalized_version_id,
                "payload_size_bytes": len(payload),
            },
        )

        return NvdPersistedObjectPayloadV1(
            key=normalized_key,
            version_id=normalized_version_id,
            raw_bytes=payload,
        )

    @staticmethod
    def _extract_http_status(exc: ClientError) -> int | None:
        """Return the Botocore HTTP status when present."""
        response = cast(_S3ClientErrorResponse, exc.response)
        metadata = response.get("ResponseMetadata")
        if metadata is None:
            return None

        status = metadata.get("HTTPStatusCode")
        return status if type(status) is int else None
