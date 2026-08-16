"""Amazon S3 adapter for conditionally persisting EPSS Silver artifacts."""

from collections.abc import Mapping
from typing import BinaryIO, Protocol, TypedDict, cast

from botocore.exceptions import ClientError

from opslens.shared.observability.ports import OperationalTelemetry
from opslens.transformation.epss.application.models import (
    SilverRepositoryWriteStatus,
)


class _S3ResponseMetadata(TypedDict, total=False):
    """Represent typed HTTP metadata returned inside an S3 client error."""

    HTTPStatusCode: int


class _S3ClientErrorResponse(TypedDict, total=False):
    """Represent the subset of a Botocore client error used by this adapter."""

    ResponseMetadata: _S3ResponseMetadata


class S3PutSilverObjectClient(Protocol):
    """Define the minimal S3 client capability required by this adapter."""

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
        """Conditionally create one Silver object in Amazon S3."""
        ...


class S3SilverEpssArtifactRepository:
    """Persist immutable EPSS Parquet artifacts in the S3 Silver layer."""

    CONTENT_TYPE = "application/vnd.apache.parquet"

    def __init__(
        self,
        client: S3PutSilverObjectClient,
        bucket_name: str,
        telemetry: OperationalTelemetry,
    ) -> None:
        """Initialize the Silver artifact repository.

        Args:
            client: Minimal S3 PutObject-capable client.
            bucket_name: Destination data bucket.
            telemetry: Runtime observability implementation.
        """
        normalized_bucket = bucket_name.strip()

        if not normalized_bucket:
            raise ValueError("S3 Silver bucket name cannot be empty.")

        self._client = client
        self._bucket_name = normalized_bucket
        self._telemetry = telemetry

    def put_if_absent(
        self,
        *,
        key: str,
        artifact: BinaryIO,
        metadata: Mapping[str, str],
    ) -> SilverRepositoryWriteStatus:
        """Persist one immutable Silver artifact when its key is absent.

        Args:
            key: Canonical Silver object key.
            artifact: Parquet stream positioned at the beginning.
            metadata: Provenance metadata associated with the artifact.

        Returns:
            Whether the artifact was created or already existed.

        Raises:
            ClientError: If S3 returns any error other than the expected
                precondition failure used for idempotency.
        """
        normalized_key = key.strip()

        if not normalized_key:
            raise ValueError("S3 Silver object key cannot be empty.")

        self._telemetry.info(
            "Persisting EPSS Silver artifact",
            fields={
                "bucket": self._bucket_name,
                "object_key": normalized_key,
            },
        )

        try:
            with self._telemetry.span("epss.silver.s3.put_object"):
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
            name="EpssSilverCreated",
            value=1.0,
            unit="Count",
        )

        self._telemetry.info(
            "EPSS Silver artifact created",
            fields={
                "bucket": self._bucket_name,
                "object_key": normalized_key,
            },
        )

        return SilverRepositoryWriteStatus.CREATED

    def _handle_client_error(
        self,
        *,
        error: ClientError,
        object_key: str,
    ) -> SilverRepositoryWriteStatus:
        """Translate S3 conditional-write outcomes into application results."""
        status_code = self._extract_http_status(error)

        if status_code == 412:
            self._telemetry.metric(
                name="EpssSilverAlreadyExists",
                value=1.0,
                unit="Count",
            )

            self._telemetry.info(
                "EPSS Silver artifact already exists",
                fields={
                    "bucket": self._bucket_name,
                    "object_key": object_key,
                    "http_status": status_code,
                },
            )

            return SilverRepositoryWriteStatus.ALREADY_EXISTS

        self._telemetry.metric(
            name="EpssSilverWriteFailure",
            value=1.0,
            unit="Count",
        )

        self._telemetry.exception(
            "Failed to persist EPSS Silver artifact",
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
        """Extract the HTTP status code from a Botocore client error."""
        response = cast(
            _S3ClientErrorResponse,
            error.response,
        )

        metadata = response.get(
            "ResponseMetadata",
            {},
        )

        status_code = metadata.get("HTTPStatusCode")

        return status_code if isinstance(status_code, int) else None
