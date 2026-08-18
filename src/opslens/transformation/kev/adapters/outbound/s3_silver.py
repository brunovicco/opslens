"""Amazon S3 adapter for conditionally persisting CISA KEV Silver artifacts."""

from collections.abc import Mapping
from typing import BinaryIO, Protocol, TypedDict, cast

from botocore.exceptions import ClientError

from opslens.shared.observability.ports import OperationalTelemetry
from opslens.transformation.kev.application.runtime_models import (
    KevSilverRepositoryWriteStatus,
)


class _S3ResponseMetadata(TypedDict, total=False):
    """Represent HTTP metadata returned inside an S3 client error."""

    HTTPStatusCode: int


class _S3ClientErrorResponse(TypedDict, total=False):
    """Represent the subset of a Botocore S3 error used by this adapter."""

    ResponseMetadata: _S3ResponseMetadata


class S3PutSilverObjectClient(Protocol):
    """Define the minimal S3 PutObject capability required by KEV Silver."""

    def put_object(
        self,
        *,
        Bucket: str,
        Key: str,
        Body: BinaryIO,
        ContentType: str,
        Metadata: Mapping[str, str],
        IfNoneMatch: str,
    ) -> Mapping[str, object]:
        """Conditionally create one immutable KEV Silver object."""
        ...


class S3SilverKevArtifactRepository:
    """Persist immutable CISA KEV Silver Parquet artifacts in Amazon S3."""

    CONTENT_TYPE = "application/vnd.apache.parquet"

    def __init__(
        self,
        *,
        client: S3PutSilverObjectClient,
        bucket_name: str,
        telemetry: OperationalTelemetry,
    ) -> None:
        """Initialize the Silver repository.

        Args:
            client: Minimal S3 PutObject-capable client.
            bucket_name: Destination OpsLens data bucket.
            telemetry: Runtime observability implementation.
        """
        normalized_bucket = bucket_name.strip()

        if not normalized_bucket:
            raise ValueError("S3 KEV Silver bucket name cannot be empty.")

        self._client = client
        self._bucket_name = normalized_bucket
        self._telemetry = telemetry

    def put_if_absent(
        self,
        *,
        key: str,
        artifact: BinaryIO,
        metadata: Mapping[str, str],
    ) -> KevSilverRepositoryWriteStatus:
        """Persist one KEV Silver artifact only when its key is absent.

        Args:
            key: Deterministic KEV Silver object key.
            artifact: Parquet artifact positioned at the beginning.
            metadata: Immutable provenance metadata.

        Returns:
            CREATED when a new object is persisted, or ALREADY_EXISTS when
            S3 rejects the conditional write because the key already exists.

        Raises:
            ClientError: If S3 returns any failure other than the expected
                412 response used for idempotency.
        """
        normalized_key = key.strip()

        if not normalized_key:
            raise ValueError("S3 KEV Silver object key cannot be empty.")

        self._telemetry.info(
            "Persisting CISA KEV Silver artifact",
            fields={
                "bucket": self._bucket_name,
                "object_key": normalized_key,
            },
        )

        try:
            with self._telemetry.span("kev.silver.s3.put_object"):
                self._client.put_object(
                    Bucket=self._bucket_name,
                    Key=normalized_key,
                    Body=artifact,
                    ContentType=self.CONTENT_TYPE,
                    Metadata=metadata,
                    IfNoneMatch="*",
                )

        except ClientError as exc:
            return self._handle_client_error(
                error=exc,
                object_key=normalized_key,
            )

        self._telemetry.metric(
            name="KevSilverCreated",
            value=1.0,
            unit="Count",
        )

        self._telemetry.info(
            "CISA KEV Silver artifact created",
            fields={
                "bucket": self._bucket_name,
                "object_key": normalized_key,
            },
        )

        return KevSilverRepositoryWriteStatus.CREATED

    def _handle_client_error(
        self,
        *,
        error: ClientError,
        object_key: str,
    ) -> KevSilverRepositoryWriteStatus:
        """Translate conditional-write outcomes into application semantics."""
        status_code = self._extract_http_status(error)

        if status_code == 412:
            self._telemetry.metric(
                name="KevSilverAlreadyExists",
                value=1.0,
                unit="Count",
            )

            self._telemetry.info(
                "CISA KEV Silver artifact already exists",
                fields={
                    "bucket": self._bucket_name,
                    "object_key": object_key,
                    "http_status": status_code,
                },
            )

            return KevSilverRepositoryWriteStatus.ALREADY_EXISTS

        self._telemetry.metric(
            name="KevSilverWriteFailure",
            value=1.0,
            unit="Count",
        )

        self._telemetry.exception(
            "Failed to persist CISA KEV Silver artifact",
            fields={
                "bucket": self._bucket_name,
                "object_key": object_key,
                "http_status": status_code,
            },
        )

        raise error

    @staticmethod
    def _extract_http_status(
        error: ClientError,
    ) -> int | None:
        """Extract an HTTP status code from a Botocore client error."""
        response = cast(
            _S3ClientErrorResponse,
            error.response,
        )

        response_metadata = response.get(
            "ResponseMetadata",
            {},
        )

        status_code = response_metadata.get("HTTPStatusCode")

        return status_code if isinstance(status_code, int) else None
